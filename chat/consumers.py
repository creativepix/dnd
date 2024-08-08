import json
import asyncio
from asgiref.sync import sync_to_async

from channels.auth import login, logout
from channels.generic.websocket import AsyncWebsocketConsumer
from users.models import Character
from .models import Room, Waiting
from daphne.server import twisted_loop
    
@sync_to_async
def get_character(character_id):
    return Character.objects.get(id=character_id)
    
@sync_to_async
def get_room(room_name):
    return Room.objects.get(name=room_name)

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
        print(text_data_json)
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
                #await self.channel_layer.group_send(
                #    self.room_group_name,
                #    {
                #        'type': 'generation_ended'
                #    }
                #)
                loop = asyncio.get_event_loop()
                loop.create_task(self.generate_scenario())

    async def generate_scenario(self):
        await asyncio.sleep(1) # to run generating on clients
        # scenarion generation
        #TODO
        

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
            
            
