from django.db import models
from users.models import Character

class Room(models.Model):
    name = models.CharField(max_length=50, primary_key=True)
    characters = models.ManyToManyField(Character)
    is_waiting = models.BooleanField()

    def __str__(self):
        return str(self.name)

class Waiting(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    is_ready = models.BooleanField()

    class Meta:
        ordering = ('date_added', )

    def __str__(self):
        return f"{self.room.name}: {self.character.id} {self.character.name} {self.is_ready}"

class Chat(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    characters = models.ManyToManyField(Character)
    is_general = models.BooleanField(default=False)

class Message(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    content = models.CharField(max_length=512)

    class Meta:
        ordering = ('date_added', )

    def __str__(self):
        return f"{self.room.name}: {self.character.id} {self.character.name} {self.is_ready}"
