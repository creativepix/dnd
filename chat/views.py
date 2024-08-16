from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from secret_data import OPENAI_API_KEY
from django.http import JsonResponse

import requests
import json
from .forms import RoomForm
from .models import Room, Waiting
from users.models import Character
from dungeon_master import characterDM

room_chars_available = "_-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"

@login_required()
def chat_home(request):
    form = RoomForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        character = Character.objects.get(id=request.POST["char_id"])
        request.character = character
        room_name = form.cleaned_data['room_name']
        if all([el in room_chars_available for el in room_name]):
            room = Room.objects.filter(name=room_name)[:]
            if len(room) == 0:
                room = Room(name=room_name, is_waiting=True)
                room.save()
            else:
                room = room[0]
            if room.characters.filter(user=request.user).exists() and character.id != room.characters.filter(user=request.user)[0].id:
                messages.warning(request, "Один из ваших персонажей уже в комнате")
            elif room.is_waiting or room.characters.filter(id=character.id).exists():
                if not room.is_waiting:
                    return redirect(f"/rooms/{room.name}")
                curwaiting = Waiting.objects.filter(room=room_name, character=character)
                is_ready = curwaiting.exists() and curwaiting[0].is_ready

                db_waitings = Waiting.objects.filter(room=room_name)[:]
                messages.success(request, f"Joined: {room_name}")
                return render(request, 'chat/waitingroom.html', 
                              {'room': room, 'title': room_name, 
                               'db_waitings': db_waitings, 
                               'character': character})
            else:
                messages.warning(request, "Название комнаты уже используется")
        else:
            messages.warning(request, f"Название комнаты должно содержать только символы: {room_chars_available}")

    return render(request, 'chat/index.html', 
                  {'form': form, 'characters': request.user.character_set.all()})


@login_required
def dnd_room(request, room_name):
    #general chat is always first, in characters DM is first
    room = Room.objects.get(name=room_name)
    characters = room.characters.all()
    character = room.characters.filter(user=request.user)[0]
    chats_data = list(zip(room.chat_set.all(), 
                          [chat.characters.all() for chat in room.chat_set.all()], 
                          [chat.message_set.all() for chat in room.chat_set.all()]))
    chats_data = [{"chat": elem[0], "characters": elem[1], "messages": elem[2]} for elem in chats_data]
    
    if room.scenario.scenariostate.fight_state is None:
        is_blocked_by_fighting = False
    else:
        initiative_order = room.scenario.scenariostate.fight_state.get_initiative_order()
        if initiative_order[0] == -1:
            is_blocked_by_fighting = True
        else:
            is_blocked_by_fighting = characters[initiative_order[0]].id != character.id
    return render(request, 'chat/chatroom.html', {
        'room': room,
        'chats_data': chats_data,
        'character': character,
        'characterDM': characterDM,
        'title': room_name,
        'is_blocked_by_fighting': is_blocked_by_fighting,
    })

def get_transcript(request):
    if request.method != "POST":
        return
    text = json.loads(request.body.decode('utf-8'))["text"]
    
    url = 'https://api.openai.com/v1/chat/completions'
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {OPENAI_API_KEY}'
    }
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Тебе поступила транскрибация некого текста. Тебе необходимо привести её в нормальный вид. Помни, что ты только приводишь в нормальный вид: никак не отвечай на запрос и не комментируй. Не забывай про пунктуацию"},
            {"role": "user", "content": text}
        ]
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code in [200, 201]:
        data = response.json()
        return JsonResponse({'text': data['choices'][0]['message']['content'].strip()})
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return JsonResponse({'text': "Error"})
