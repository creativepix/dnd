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

class StatsCreateFormValues:
    def __init__(self):
        self.custom_class = "Бард"
        self.custom_race = "Человек"
        self.level = 1
        self.stre = -5
        self.dex = -5
        self.cos = -5
        self.inte = -5
        self.wis = -5
        self.cha = -5
        self.stre_down = 1
        self.dex_down = 1
        self.cos_down = 1
        self.inte_down = 1
        self.wis_down = 1
        self.cha_down = 1
        self.proficiency_bonus = 1
        self.passive_perception = 5
        self.stre_saving = 0
        self.dex_saving = 0
        self.cos_saving = 0
        self.inte_saving = 0
        self.wis_saving = 0
        self.cha_saving = 0
        self.acrobatics = 0
        self.animals = -4
        self.arcana = -4
        self.athletics = -4
        self.deception = -4
        self.history = -4
        self.insight = -4
        self.intimidation = -4
        self.investigation = -4
        self.medicine = -4
        self.nature = -4
        self.perception = -4
        self.performance = -4
        self.persuasion = -4
        self.religion = -4
        self.sleightofhand = -4
        self.stealth = -4
        self.survival = -4
        self.proficiencies = ""
        self.current_hit = 10
        self.attacks_spellcasting = ""
        self.equipment = ""
        self.personality_traits = ""
        self.ideals = ""
        self.bonds = ""
        self.flaws = ""
        self.features_traits = ""
        self.success = 0
        self.failure = 0
        self.armour = 5
        self.initiative = -4
        self.speed = 30


class CharacterCreateFormValues:
    def __init__(self):
        self.name = "Johnatan"
        self.image = ""
