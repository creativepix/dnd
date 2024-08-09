# Generated by Django 4.0.5 on 2022-06-03 12:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_waiting'),
    ]

    operations = [
        migrations.CreateModel(
            name='Chat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room', models.ForeignKey(to='chat.room', on_delete=models.CASCADE)),
                ('characters', models.ManyToManyField(to='users.character')),
                ('is_general', models.BooleanField(default=False)),
                ('is_blocked', models.BooleanField(default=False))
            ],
        ),
    ]
