from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from .forms import RoomForm
from .models import Room, Waiting
from users.models import Character

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
        if room.is_waiting or room.characters.filter(id=character.id).exists():
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
def chat_room(request, room_name):
    db_messages = []
    #db_messages = Message.objects.filter(room=room_name)[:]

    messages.success(request, f"Joined: {room_name}")
    return render(request, 'chat/chatroom.html', {
        'room_name': room_name,
        'title': room_name,
        'db_messages': db_messages,
    })
