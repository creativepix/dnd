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
        
        self.stre = 2
        self.dex = 2
        self.cos = 2
        self.inte = 2
        self.wis = 2
        self.cha = 2
        
        self.stre_down = 15
        self.dex_down = 15
        self.cos_down = 15
        self.inte_down = 15
        self.wis_down = 15
        self.cha_down = 15
        
        self.proficiency_bonus = 1
        self.passive_perception = 5
        
        self.stre_saving = 2
        self.dex_saving = 2
        self.cos_saving = 2
        self.inte_saving = 2
        self.wis_saving = 2
        self.cha_saving = 2
        
        self.acrobatics = 3
        self.animals = 3
        self.arcana = 3
        self.athletics = 3
        self.deception = 3
        self.history = 3
        self.insight = 3
        self.intimidation = 3
        self.investigation = 3
        self.medicine = 3
        self.nature = 3
        self.perception = 3
        self.performance = 3
        self.persuasion = 3
        self.religion = 3
        self.sleightofhand = 3
        self.stealth = 3
        self.survival = 3
        
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
        self.armour = 50
        self.initiative = 3
        self.speed = 30


class CharacterCreateFormValues:
    def __init__(self):
        self.name = "Johnatan"
        self.image = ""
