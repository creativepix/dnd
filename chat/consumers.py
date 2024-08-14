import json
import asyncio
from asgiref.sync import sync_to_async
from datetime import timedelta
from channels.auth import login, logout
from channels.generic.websocket import AsyncWebsocketConsumer
from users.models import Character
from .models import Room, Waiting, Chat, Message, Scenario, ScenarioPart, ScenarioFightState, ScenarioState
from daphne.server import twisted_loop
from dungeon_master import characterDM
import itertools
from dungeon_master import create_scenario_parts, get_character_info, generate_answer, \
    classify_personal_prompt, sync_generate_answer, make_content_shorter, sync_make_content_shorter, \
    check_need_spells, check_need_equipment, classify_throws_skills, get_exact_throws, get_exact_skills, \
    change_equipment, what_equipment_changed, check_next_part, check_equipment, check_spells, generate_intro, \
    sync_check_next_part, need_change_scenario, change_scenario, start_fight, generate_fight_turn, is_starting_fight, \
    generate_failed_battle, sync_generate_failed_battle, sync_generate_image_scenario
import random

WAIT_SECONDS = 0.5

@sync_to_async
def get_monsert_info(chat):
    if chat.room.scenario.scenariostate.fight_state is None:
        return ""
    return chat.room.scenario.scenariostate.fight_state.monster_info

@sync_to_async
def sync_save_object(obj):
    obj.save()

@sync_to_async
def sync_print(*args, **kwargs):
    print(*args, **kwargs)

@sync_to_async
def get_character(character_id):
    return Character.objects.get(id=character_id)

@sync_to_async
def get_character_stats(character):
    return character.stats

@sync_to_async
def is_end(room):
    return room.scenario.scenariostate.current_part.is_final
    
@sync_to_async
def get_message(message_id):
    return Message.objects.get(id=message_id)
    
@sync_to_async
def get_chat(chat_id):
    return Chat.objects.get(id=chat_id)
    
@sync_to_async
def get_room(room_name):
    return Room.objects.get(name=room_name)

@sync_to_async
def get_room_characters(room):
    return list(room.characters.all())

@sync_to_async
def get_chat_characters(chat):
    return list(chat.characters.all())

def get_item(dictionary, key):
    if key in dictionary:
        return dictionary[key]
    return dictionary[str(key)]

class WaitingConsumer(AsyncWebsocketConsumer):
    """
    A consumer does three things:
    1. Accepts connections.
    2. Receives messages from client.
    3. Disconnects when the job is done.
    """

    async def connect(self):
        """
        Connect to a room
        """
        # Connect only if the user is authenticated
        user = self.scope['user']

        if user.is_authenticated:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f"chat_{self.room_name}"
            
            self.character = await get_character(self.scope['url_route']['kwargs']['character_id'])
            self.room = await get_room(self.room_name)

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            if await self.is_creating_waiting_necessary():
                await self.create_waiting()
                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'character_connected',
                        'character_id': self.character.id,
                    }
                )
        else:
            await self.send({"close": True})

    async def disconnect(self, close_code):
        """
        Disconnect from channel

        :param close_code: optional
        """
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Receive messages from WebSocket

        :param text_data: message
        """

        text_data_json = json.loads(text_data)
        if text_data_json["type"] == "check":
            await self.set_my_ready_state(text_data_json["state"])
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'set_ready_state',
                    'character_id': self.character.id,
                    'state': text_data_json["state"],
                }
            )
            if await self.is_everyone_ready():
                await self.set_room_waiting_state(False)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'everyone_ready'
                    }
                )
                loop = asyncio.get_event_loop()
                loop.create_task(self.generate_scenario())

    async def generate_scenario(self):
        await asyncio.sleep(WAIT_SECONDS) # to run generating "loading" on clients
        await self.generate_scenario_sync()
        await self.create_character_chats()
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'generation_ended'
            }
        )

    async def generation_ended(self, event):
        await self.send(text_data=json.dumps({
            'type': 'generation_ended',
        }))

    async def everyone_ready(self, event):
        await self.send(text_data=json.dumps({
            'type': 'everyone_ready',
        }))

    async def character_connected(self, event):
        """
        Receive messages from room group

        :param event: Events to pick up
        """
        connected_character = await get_character(event["character_id"])
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'character_image': connected_character.image.url,
            'character_name': connected_character.name,
            'character_id': connected_character.id,
        }))

    async def set_ready_state(self, event):
        await self.send(text_data=json.dumps({
            'type': 'check',
            'character_id': event['character_id'],
            'state': event['state'],
        }))
        
    @sync_to_async
    def generate_scenario_sync(self):
        scenario = Scenario(room=self.room)
        for character in self.room.characters.all():
            info = get_character_info(character)
            
            character.info = info
            character.save()
        scenario_parts_txt = create_scenario_parts(self.room.characters.all())
        scenario_parts = [ScenarioPart(scenario=scenario, content=content) for content in scenario_parts_txt]
        scenario_parts[-1].is_final = True
        scenario_state = ScenarioState(scenario=scenario, current_part=scenario_parts[0])
        
        scenario.save()
        for scenario_part in scenario_parts:
            scenario_part.save()
        scenario_state.save()

    @sync_to_async
    def create_character_chats(self):
        characters = [characterDM] + list(self.room.characters.all())
        
        # general chat
        general_chat = Chat(room=self.room, is_general=True)
        general_chat.save()
        info = {}
        for char in characters:
            info[char.id] = {}
            info[char.id]["new_messages_count"] = 0
            general_chat.characters.add(char)
        general_chat.save()
        
        # friends chat
        friends_chat = Chat(room=self.room, is_friends=True)
        friends_chat.save()
        info = {}
        for char in characters:
            info[char.id] = {}
            info[char.id]["new_messages_count"] = 0
            friends_chat.characters.add(char)
        friends_chat.save()
        
        
        #one2one chats
        for char1, char2 in itertools.combinations(characters, 2):
            chat = Chat(room=self.room)
            chat.save()
            info = {char1.id: {"new_messages_count": 0},
                    char2.id: {"new_messages_count": 0},}
            chat.characters.add(char1)
            chat.characters.add(char2)
            chat.save()
        
        first_msg = generate_intro(self.room)
        first_short_msg = make_content_shorter(first_msg)
        Message.objects.create(chat=general_chat, character=characterDM, content=first_msg, short_content=first_short_msg)

    @sync_to_async
    def set_room_waiting_state(self, state):
        self.room.is_waiting = state
        self.room.save()
        
    @sync_to_async
    def is_creating_waiting_necessary(self):
        return not self.room.characters.filter(id=self.character.id).exists()
        
    @sync_to_async
    def set_my_ready_state(self, state):
        waiting = Waiting.objects.filter(room=self.room, character=self.character)[0]
        waiting.is_ready = state
        waiting.save()
    
    @sync_to_async
    def is_everyone_ready(self):
        return all([waiting.is_ready for waiting in Waiting.objects.filter(room=self.room)])
        
    @sync_to_async
    def create_waiting(self):
        self.room.characters.add(self.character)
        self.room.save()
        Waiting.objects.create(room=self.room, character=self.character, is_ready=False)
            
            

class RoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Connect only if the user is authenticated
        user = self.scope['user']

        if user.is_authenticated:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f"chat_{self.room_name}"
            
            self.character = await get_character(self.scope['url_route']['kwargs']['character_id'])
            self.room = await get_room(self.room_name)
            
            await self.init_general_chat()

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.send({"close": True})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        if text_data_json["type"] == "send_message":
            if not any(text_data_json["message"]):
                return
            chat = await get_chat(text_data_json["chat_id"])
            chat_characters = await get_chat_characters(chat)
            need_answer = not chat.is_friends and characterDM in chat_characters
            
            if need_answer:
                await self.set_chat_block_status(chat, True)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'change_chat_block_status',
                        'status': True,
                        'chat_id': chat.id
                    }
                )
            
            message_text_data = await self.createMessage(chat, text_data_json["message"])
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_data',
                    'data': message_text_data,
                }
            )
            if need_answer:
                loop = asyncio.get_event_loop()
                loop.create_task(self.generate_answer(text_data_json["message"], chat))
        elif text_data_json["type"] == "change_chat_block_status":
            chat = await get_chat(text_data_json["chat_id"])
            await self.set_chat_block_status(chat, text_data_json["status"])
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'change_chat_block_status',
                    'status': text_data_json["status"],
                    'chat_id': text_data_json["chat_id"]
                }
            )
        else:
            print(text_data_json)
    
    async def send_data(self, event):
        await self.send(text_data=event["data"])
    
    async def change_chat_block_status(self, event):
        await self.send(text_data=json.dumps({"type": "update_chat_block_status",
                        "blocked_chat_ids": await self.get_blocked_chat_ids()}))
    
    async def generate_answer(self, message, chat):
        if chat.is_friends:
            return
        is_fighting_end = False
        is_fighting_start = False
        is_fighting = await self.get_is_fighting()
        
        if is_fighting:
            await self.send(text_data=json.dumps({
                'type': 'update_is_blocked_by_fighting_status',
                'status':  True
            }))
        
        if chat.is_general:
            self.general_chat = chat
        characters = await get_room_characters(self.room)
        
        message_text_data, message_img_data, message_text_data2, imgurl = None, "", None, ""
        if not chat.is_general:
            #TODO
            msg = await sync_generate_answer(characters, self.general_chat, chat, prompt_class=3)
        else:
            msg = await self.generate_action_answer(characters, message, chat, is_fighting=is_fighting, fighting_hit=await self.get_current_hit())
        short_msg = await sync_make_content_shorter(msg)
        
        if chat.is_general:
            message_text_data = await self.createMessage(self.general_chat, msg, short_content=short_msg, character=characterDM)
            
            if await is_end(chat.room):
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'send_data',
                        'data': message_text_data,
                    }
                )
                await self.end_game_save()
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'send_data',
                        'data': json.dumps({'type': "end_game"})
                    }
                )
                return
        
            monster_info = await get_monsert_info(chat)
            if is_fighting and await self.is_end_fight(chat):
                is_fighting_end = True
                is_fighting = False
                is_fighting_start = False
                msg2 = await self.generate_action_answer(characters, message, chat, is_fighting=is_fighting, fighting_hit=await self.get_current_hit(),
                                                         is_fighting_end=is_fighting_end, dead_monster_info=monster_info)
                short_msg2 = await sync_make_content_shorter(msg2)
                message_text_data2 = await self.createMessage(self.general_chat, msg2, short_content=short_msg2, character=characterDM)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'send_data',
                        'data': json.dumps({
                            'type': 'update_is_blocked_by_fighting_status',
                            'status':  False
                        }),
                    }
                )
        
            is_fighting_start = (not is_fighting and chat.room.scenario.scenariostate.fight_state is not None) and not is_fighting_end
            is_fighting = (is_fighting or is_fighting_start) and not is_fighting_end
            if is_fighting:
                # печальный конец
                if await self.is_everyone_dead(characters):
                    msg = await sync_generate_failed_battle(self.general_chat)
                    message_text_data = await self.createMessage(self.general_chat, msg, character=characterDM)
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'send_data',
                            'data': message_text_data,
                        }
                    )
                    await self.end_game_save()
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'send_data',
                            'data': json.dumps({'type': "end_game"})
                        }
                    )
                    return
            if is_fighting_start:
                imgurl = await sync_generate_image_scenario(self.general_chat, prefolder="message_images")
                message_text_data = await self.set_message_image(message_text_data, imgurl)
                
                initiative_order = chat.room.scenario.scenariostate.fight_state.get_initiative_order()
                if initiative_order[0] == -1:
                    msg = await self.generate_fight_monster_turn(chat)
                    short_msg = await sync_make_content_shorter(msg)
                    await self.channel_layer.group_send(self.room_group_name, {'type': 'check_update_is_dead'})
                    message_text_data2 = await self.createMessage(self.general_chat, msg, short_content=short_msg, character=characterDM)
            elif await sync_check_next_part(self.general_chat):
                await self.go_next_part()
                imgurl = await sync_generate_image_scenario(self.general_chat, prefolder="message_images")
                message_text_data = await self.set_message_image(message_text_data, imgurl)
        else:
            message_text_data = await self.createMessage(chat, msg, short_content=short_msg, character=characterDM)
            
            
        #if not chat.is_general:
        await self.set_chat_block_status(chat, False)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'change_chat_block_status',
                'status': False,
                'chat_id': chat.id
            }
        )

        for txt_data in [message_text_data, message_text_data2]:
            if txt_data is not None:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'send_data',
                        'data': txt_data,
                    }
                )
        
        if is_fighting_start:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_data',
                    'data': json.dumps({
                        'type': 'update_is_blocked_by_fighting_status',
                        'status':  True
                    }),
                }
            )
        if is_fighting:
            initiative_order = await self.get_initiative_order(chat)
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'next_fight_turn',
                        'character_id_turn': characters[initiative_order[0]].id,
                        'go_next_turn': not is_fighting_start
                    }
                )
    
    async def next_fight_turn(self, event):
        if self.character.id != event["character_id_turn"]:
            return
        await self.refresh_character()
        await self.refresh_general_chat()
        stats = await get_character_stats(self.character)
        characters = await get_room_characters(self.room)
        is_stabilized_now = False
        # печальный конец
        if await self.is_everyone_dead(characters):
            msg = await sync_generate_failed_battle(self.general_chat)
            message_text_data = await self.createMessage(self.general_chat, msg, character=characterDM)
            
            imgurl = await sync_generate_image_scenario(self.general_chat, prefolder="message_images")
            message_text_data = await self.set_message_image(message_text_data, imgurl)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_data',
                    'data': message_text_data,
                }
            )
            return
        #await sync_print(self.character.id, event["character_id_turn"])
        msg = None
        if stats.failure >= 3:
            msg = f"К сожалению, персонаж {self.character.name} уже покинул наш мир и пропускает ход"
        else:
            is_dying = stats.armour <= 0
            await sync_print('armour', stats.armour, is_dying)
            if is_dying:
                r = random.randint(1, 20)
                msg = f"""Персонаж {self.character.name} помирает, поэтому бросает спасбросок 1к20 от смерти.
Выпадает: {r}, что {'>=' if r >= 10 else '<'} 10, поэтому этот бросок оказался {'успешным' if r >= 10 else 'провальным'}"""
                if r < 10:
                    stats.failure += 1
                else:
                    stats.success += 1
                if stats.success >= 3:
                    msg += "\nК счастью, персонаж стабилизируется. Теперь у него одно здоровье"
                    await self.stabilize_character()
                    is_stabilized_now = True
                if stats.failure >= 3:
                    msg += "\nК несчастью, персонаж погибает"
                    await self.send(text_data=json.dumps({"type": "update_is_dead_status", "status": True}))
                # сохранить новые предсмертные значения
                await sync_save_object(stats)
        await sync_print('msg', msg, event)
        if msg is not None:
            message_text_data = await self.createMessage(self.general_chat, msg, character=characterDM)
            #TODO: await asyncio.sleep(WAIT_SECONDS)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_data',
                    'data': message_text_data,
                }
            )
        
        if (msg is not None or event['go_next_turn']) and not is_stabilized_now:
            await self.go_next_fight_round()
            initiative_order = await self.get_initiative_order(self.general_chat)
            await sync_print('current initiative', initiative_order)
            if initiative_order[0] == -1:
                msg = await self.generate_fight_monster_turn(self.general_chat)
                short_msg = await sync_make_content_shorter(msg)
                message_text_data = await self.createMessage(self.general_chat, msg, short_content=short_msg, character=characterDM)
                await self.channel_layer.group_send(self.room_group_name, {'type': 'check_update_is_dead'})
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'send_data',
                        'data': message_text_data,
                    }
                )
                # обновление порядка инициатив, так как походил монстр
                initiative_order = await self.get_initiative_order(self.general_chat)
            await sync_print('current2 initiative', initiative_order)
            await self.send(text_data=json.dumps({
                'type': 'update_is_blocked_by_fighting_status',
                'status':  True
            }))
            await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'next_fight_turn',
                        'character_id_turn': characters[initiative_order[0]].id,
                        'go_next_turn': False
                    }
                )
        else:
            await self.send(text_data=json.dumps({
                'type': 'update_is_blocked_by_fighting_status',
                'status':  False
            }))
            
    
    async def check_update_is_dead(self, event):
        stats = await get_character_stats(self.character)
        if stats.failure >= 3:
            await self.send(text_data=json.dumps({"type": "update_is_dead_status", "status": True}))
        else:
            await self.send(text_data=json.dumps({"type": "update_is_dead_status", "status": False}))
    
    @sync_to_async
    def set_message_image(self, message_text_data, imgurl):
        message_text_data = json.loads(message_text_data)
        msg = Message.objects.get(id=message_text_data["id"])
        msg.image = imgurl
        msg.save()
        message_text_data['content_image'] = msg.image.url
        message_text_data = json.dumps(message_text_data)
        return message_text_data
            
    @sync_to_async
    def is_end_fight(self, chat):
        fight_state = chat.room.scenario.scenariostate.fight_state
        if fight_state.health <= 0:
            chat.room.scenario.scenariostate.fight_state = None
            chat.room.scenario.scenariostate.save()
            return True
        return False
    
    @sync_to_async
    def get_initiative_order(self, chat):
        return chat.room.scenario.scenariostate.fight_state.get_initiative_order()
            
    @sync_to_async
    def get_current_hit(self):
        return self.character.stats.current_hit
    
    @sync_to_async
    def get_is_fighting(self):
        return self.general_chat.room.scenario.scenariostate.fight_state is not None
            
    @sync_to_async
    def is_everyone_dead(self, characters):
        return all([char == characterDM or (char.stats.armour == 0 and char.stats.failure >= 3) for char in characters])
    
    @sync_to_async
    def stabilize_character(self):
        self.character.stats.success = 0
        self.character.stats.failure = 0
        self.character.stats.armour = 1
        self.character.stats.save()
    
    @sync_to_async
    def go_next_fight_round(self):
        self.general_chat.room.scenario.scenariostate.refresh_from_db()
        fight_state = self.general_chat.room.scenario.scenariostate.fight_state
        initiative_order = fight_state.get_initiative_order()
        initiative_order = initiative_order[1:] + [initiative_order[0]]
        fight_state.initiative_order = " ".join(map(str, initiative_order))
        fight_state.save()

    @sync_to_async
    def go_next_part(self):
        current_part = self.room.scenario.scenariostate.current_part
        #if current_part.is_final:
        #    #TODO: end game
        #    print("GAME ENDED")
        #    return
        scenario_parts = list(self.general_chat.room.scenario.scenariopart_set.all())
        next_part = scenario_parts[scenario_parts.index(current_part) + 1]
        self.room.scenario.scenariostate.current_part = next_part
        self.room.scenario.scenariostate.save()
    
    @sync_to_async
    def refresh_general_chat(self):
        self.general_chat.refresh_from_db()
    
    @sync_to_async
    def refresh_character(self):
        self.character.refresh_from_db()
    
    @sync_to_async
    def generate_fight_monster_turn(self, chat):
        fight_state = chat.room.scenario.scenariostate.fight_state
        out = generate_fight_turn(chat)
        initiative_order = fight_state.get_initiative_order()
        initiative_order = initiative_order[1:] + [initiative_order[0]]
        fight_state.initiative_order = " ".join(map(str, initiative_order))
        fight_state.save()
        self.character.refresh_from_db()
        return out

    @sync_to_async
    def generate_action_answer(self, characters, message, chat, is_fighting=False, fighting_hit=0, is_fighting_end=False, dead_monster_info=""):
        prompt_class = 4
        out_adding = ""
        spells = self.character.stats.attacks_spellcasting
        equipment = self.character.stats.equipment
        
        cannot_make_prompt = ""
        throws_skills_prompt_adding = ""
        need_spells = check_need_spells(message)
        if need_spells:
            if not check_spells(message, spells):
                cannot_make_prompt = "У игрока не хватает необходимых навыков владения магией"
        else:
            need_equipment = check_need_equipment(message)
            if need_equipment:
                if not check_equipment(message, equipment):
                    cannot_make_prompt = "У игрока не хватает необходимых предметов (их нет в 'инвентаре' - но слово 'инвентарь' использовать при генерации не надо)"
            else:
                throws_skills_class = classify_throws_skills(message)
                r = random.randint(1, 20)
                prof = self.character.stats.proficiency_bonus
                if throws_skills_class == 1:
                    throws_ind = get_exact_throws(message)
                    throws_ind -= 1
                    throws = ['Сила', 'Ловкость', 'Телосложение', 'Интеллект', 'Мудрость', 'Харизма', 'Восприятие']
                    if throws_ind == 0:
                        adding = self.character.stats.stre_saving
                    elif throws_ind == 1:
                        adding = self.character.stats.dex_saving
                    elif throws_ind == 2:
                        adding = self.character.stats.cos_saving
                    elif throws_ind == 3:
                        adding = self.character.stats.inte_saving
                    elif throws_ind == 4:
                        adding = self.character.stats.wis_saving
                    elif throws_ind == 5:
                        adding = self.character.stats.cha_saving
                    else:
                        adding = self.character.stats.passive_perception
                    s = r + adding + prof
                    out_adding += f'Тебе потребовался спасбросок "{throws[throws_ind]}" (вычисляется как 1к20 + модификатор характеристики + бонус мастерства). Его получившееся значение: {r}+{adding}+{prof}={s}\n\n'
                    throws_skills_prompt_adding += f'Игрок также совершил проверку навыка "{throws[throws_ind]}". У него получилось: "{s}". '
                elif throws_skills_class == 2:
                    skills_ind = get_exact_skills(message)
                    skills_ind -= 1
                    skills = ['Акробатика', 'Анализ', 'Атлетика', 'Восприятие', 'Выживание', 'Выступление', 'Запугивание', 'История', 'Ловкость рук', 'Магия', 'Медицина', 'Обман', 'Природа', 'Проницательность', 'Религия', 'Скрытность', 'Убеждение', 'Уход за животными']
                    if skills_ind == 0:
                        adding = self.character.stats.acrobatics
                    elif skills_ind == 1:
                        adding = self.character.stats.animals
                    elif skills_ind == 2:
                        adding = self.character.stats.arcana
                    elif skills_ind == 3:
                        adding = self.character.stats.athletics
                    elif skills_ind == 4:
                        adding = self.character.stats.deception
                    elif skills_ind == 5:
                        adding = self.character.stats.history
                    elif skills_ind == 6:
                        adding = self.character.stats.insight
                    elif skills_ind == 7:
                        adding = self.character.stats.intimidation
                    elif skills_ind == 8:
                        adding = self.character.stats.investigation
                    elif skills_ind == 9:
                        adding = self.character.stats.medicine
                    elif skills_ind == 10:
                        adding = self.character.stats.nature
                    elif skills_ind == 11:
                        adding = self.character.stats.perception
                    elif skills_ind == 12:
                        adding = self.character.stats.performance
                    elif skills_ind == 13:
                        adding = self.character.stats.persuasion
                    elif skills_ind == 14:
                        adding = self.character.stats.religion
                    elif skills_ind == 15:
                        adding = self.character.stats.sleightofhand
                    elif skills_ind == 16:
                        adding = self.character.stats.stealth
                    else:
                        adding = self.character.stats.survival
                    s = r + adding + prof
                    out_adding += f'Тебе потребовался навык "{skills[skills_ind]}" (вычисляется как 1к20 + модификатор характеристики + бонус мастерства). Его получившееся значение: {r}+{adding}+{prof}={s}\n\n'
                    throws_skills_prompt_adding += f'Игрок также совершил проверку навыка "{skills[skills_ind]}". У него получилось: "{s}". '
        
        if any(throws_skills_prompt_adding):
            throws_skills_prompt_adding += '''Оценить результат можно по следующей таблице:
Очень ужасно: 0-5 (что-то идет не так, всё проходит неудачно)
Плохо: 6-10 (есть вероятность на проявление какого-то нехорошего события)
Средне: 11-15 (ничего необычного не может произойти, ход событий не особо меняется)
Хорошо: 16-20 (что-то может получиться, но не то, чего можно не ждать, ход событий может немного изменится)
Очень хорошо: 21-25 (игроку удается совершить нечто, выходящее за рамки обычного)
Невероятно, сделал невозможное: 26-30 (игроку удается совершить невозможное, ход событий меняется колоссально)'''

        if not any(cannot_make_prompt) and not is_fighting and not is_fighting_end:
            if is_starting_fight(chat):
                out = start_fight(chat)
                print(chat.room.scenario.scenariostate.fight_state)
                return out
            if need_change_scenario(self.general_chat):
                change_scenario(self.general_chat, throws_skills_prompt_adding=throws_skills_prompt_adding)

        msg = generate_answer(characters, self.general_chat, chat,
                              prompt_class=prompt_class,
                              cannot_make_prompt=cannot_make_prompt,
                              throws_skills_prompt_adding=throws_skills_prompt_adding,
                              is_fighting=is_fighting, fighting_hit=fighting_hit,
                              is_fighting_end=is_fighting_end, dead_monster_info=dead_monster_info)


        if any(out_adding):
            msg = out_adding + msg
        #equipment_changing = what_equipment_changed(msg)
        #if equipment_changing[0] == 1:
        #    cmd = " ".join(equipment_changing[1:])
        #    equipment = change_equipment(equipment, cmd, self.character.info)
        #    self.character.stats.equipment = equipment
        #    self.character.stats.save()

        return msg
    
    @sync_to_async
    def end_game_save(self):
        self.room.is_end = True
        self.room.save()
    
    @sync_to_async
    def get_blocked_chat_ids(self):
        chat_ids = []
        for chat in self.room.chat_set.all():
            if chat.is_blocked:
                chat_ids.append(chat.id)
        return chat_ids
    
    @sync_to_async
    def set_chat_block_status(self, chat, status):
        chat.is_blocked = status
        chat.save()
    
    @sync_to_async
    def createMessage(self, chat, content, short_content="", character=None, image=""):
        if character is None:
            character = self.character
        message = Message(chat=chat, character=character, content=content, short_content=short_content, image=image)
        message.save()
        message.date_added += timedelta(hours=3)
        message.save()
        text_data = json.dumps({
            'type': 'message_received',
            'id': message.id,
            'content': message.content,
            'character_id': message.character.id,
            'character_name': message.character.name,
            'image': message.character.image.url,
            'content_image': message.image.url if message.image else "",
            'date': message.date_added.strftime("%H:%M:%S"),
            'chat_id': message.chat.id,
        })
        return text_data
    
    @sync_to_async
    def init_general_chat(self):
        self.general_chat = self.room.chat_set.filter(is_general=True)[0]
