# Generated by Django 4.0.5 on 2022-06-03 12:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_chat'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chat', models.ForeignKey(to='chat.chat', on_delete=models.CASCADE)),
                ('character', models.ForeignKey(to='users.character', on_delete=models.CASCADE)),
                ('date_added', models.DateTimeField(auto_now_add=True)),
                ('content', models.CharField(max_length=2048)),
                ('short_content', models.CharField(max_length=512, default="")),
                ('is_fighting', models.BooleanField(default=False)),
                ('image', models.ImageField(default='', upload_to='message_images')),
            ],
            options={
                'ordering': ('date_added',),
            },
        ),
    ]
