# Generated by Django 5.0.8 on 2024-08-10 08:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0009_scenariostate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scenariostate',
            name='scenario',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='chat.scenario'),
        ),
    ]
