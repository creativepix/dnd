from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import Profile, Character, Stats


class UserRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']


class StatsCreateForm(forms.ModelForm):
    class Meta:
        model = Stats
        fields = ['strength']


class CharacterCreateForm(forms.ModelForm):
    class Meta:
        model = Character
        fields = ['image']
