# Generated by Django 5.0.8 on 2024-08-11 13:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0010_alter_scenariostate_scenario'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scenariostate',
            name='scenario',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='chat.scenario'),
        ),
    ]
