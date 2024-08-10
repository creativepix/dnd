from django.db import models
from django.contrib.auth.models import User
from PIL import Image

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} profile"

class Stats(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    custom_class = models.CharField(max_length=200)
    custom_race = models.CharField(max_length=200)
    level = models.IntegerField()
    stre = models.IntegerField()
    dex = models.IntegerField()
    cos = models.IntegerField()
    inte = models.IntegerField()
    wis = models.IntegerField()
    cha = models.IntegerField()
    stre_down = models.IntegerField()
    dex_down = models.IntegerField()
    cos_down = models.IntegerField()
    inte_down = models.IntegerField()
    wis_down = models.IntegerField()
    cha_down = models.IntegerField()
    proficiency_bonus = models.IntegerField()
    passive_perception = models.IntegerField()
    stre_saving = models.IntegerField()
    dex_saving = models.IntegerField()
    cos_saving = models.IntegerField()
    inte_saving = models.IntegerField()
    wis_saving = models.IntegerField()
    cha_saving = models.IntegerField()
    acrobatics = models.IntegerField()
    animals = models.IntegerField()
    arcana = models.IntegerField()
    athletics = models.IntegerField()
    deception = models.IntegerField()
    history = models.IntegerField()
    insight = models.IntegerField()
    intimidation = models.IntegerField()
    investigation = models.IntegerField()
    medicine = models.IntegerField()
    nature = models.IntegerField()
    perception = models.IntegerField()
    performance = models.IntegerField()
    persuasion = models.IntegerField()
    religion = models.IntegerField()
    sleightofhand = models.IntegerField()
    stealth = models.IntegerField()
    survival = models.IntegerField()
    proficiencies = models.CharField(max_length=200)
    current_hit = models.IntegerField()
    attacks_spellcasting = models.CharField(max_length=200)
    equipment = models.CharField(max_length=200)
    personality_traits = models.CharField(max_length=200)
    ideals = models.CharField(max_length=200)
    bonds = models.CharField(max_length=200)
    flaws = models.CharField(max_length=200)
    features_traits = models.CharField(max_length=200)
    success = models.IntegerField()
    failure = models.IntegerField()
    armour = models.IntegerField()
    initiative = models.IntegerField()
    speed = models.IntegerField()


class Character(models.Model):
    id = models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')
    image = models.ImageField(default="default.jpg", upload_to='character_pics')
    name = models.CharField(max_length=50)
    stats = models.OneToOneField(Stats, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    info = models.CharField(max_length=512, default="")

    class Meta:
        ordering = ('date_added', )
    
    # save method if the image is too big, Pillow for resizing

    # Alternatively, you can also resize the image before committing the form
    # Lots of ways to do it
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        img = Image.open(self.image.path)

        if img.height > 300 or img.width > 300:
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)
