from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

import json
from .forms import RoomForm
from .models import Room, Waiting
from users.models import Character
from dungeon_master import characterDM

@login_required()
def chat_home(request):
    form = RoomForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        character = Character.objects.get(id=request.POST["char_id"])
        request.character = character
        room_name = form.cleaned_data['room_name']
        
        room = Room.objects.filter(name=room_name)[:]
        if len(room) == 0:
            room = Room(name=room_name, is_waiting=True)
            room.save()
        else:
            room = room[0]
        if room.characters.filter(user=request.user).exists() and character.id != room.characters.filter(user=request.user)[0].id:
            messages.warning(request, "One of your characters is already in room")
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
            messages.warning(request, "Room name is used")

    return render(request, 'chat/index.html', 
                  {'form': form, 'characters': request.user.character_set.all()})


@login_required
def dnd_room(request, room_name):
    #general chat is always first, in characters DM is first
    room = Room.objects.get(name=room_name)
    character = room.characters.filter(user=request.user)[0]
    chats_data = list(zip(room.chat_set.all(), 
                          [chat.characters.all() for chat in room.chat_set.all()], 
                          [chat.message_set.all() for chat in room.chat_set.all()]))
    chats_data = [{"chat": elem[0], "characters": elem[1], "messages": elem[2]} for elem in chats_data]
    return render(request, 'chat/chatroom.html', {
        'room': room,
        'chats_data': chats_data,
        'character': character,
        'characterDM': characterDM,
        'title': room_name,
    })
