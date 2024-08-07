from django.db import models
from django.contrib.auth.models import User
from PIL import Image

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.username} profile"

class Stats(models.Model):
    strength = models.IntegerField(default=0)


class Character(models.Model):
    image = models.ImageField(default="default.jpg", upload_to='character_pics')
    name = models.CharField(max_length=50)
    stats = models.OneToOneField(Stats, on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    profile = models.ForeignKey(Profile, on_delete=models.DO_NOTHING)

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
