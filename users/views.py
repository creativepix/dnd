from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
import json
from .forms import UserRegisterForm, UserUpdateForm, CharacterCreateFormValues, \
    StatsCreateFormValues
from .models import Stats, Character
from openai_api import generate_image, generate_text
from PIL import Image
from io import BytesIO
import base64
import uuid

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f"{username} has been created!")
            return redirect('login')
    else:
        form = UserRegisterForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    u_form = UserUpdateForm(instance=request.user)
    if request.method == 'POST':
        if "update-profile" in request.POST:
            u_form = UserUpdateForm(request.POST, instance=request.user)
            if u_form.is_valid():
                u_form.save()
                messages.success(request, "Your account has been updated")
        elif "add-character" in request.POST:
            character = CharacterCreateFormValues().__dict__
            stats = StatsCreateFormValues().__dict__
            data = {}
            for key, val in stats.items():
                data[key] = val if isinstance(val, int) else f'"{val}"'
            for key, val in character.items():
                data[key] = val if isinstance(val, int) else f'"{val}"'
            data["mode"] = "'create'"
            data["char_id"] = "''"
            return render(request, 'users/character.html', data)
        elif "generate" in request.POST:
            all_data = json.loads(request.POST["all_data"])
            system_prompt = "Твоя задача сжать следующую информацию так, чтобы она отражала основные характеристики героя. Твой ответ должен быть таким, чтобы его можно было использовать как промпт для генерации изображения к этому персонажу. Удаляй ту информацию, которая не сказывается (либо сказывается мало) на внешности персонажа!"
            constitution = "худое"
            try:
                all_data["armour"] = int(all_data["armour"])
            except Exception:
                all_data["armour"] = 20
            if 10 < all_data["armour"] < 15:
                constitution = "среднее"
            elif 15 <= all_data["armour"] < 25:
                constitution = "крепкое"
            elif 25 <= all_data["armour"] < 40:
                constitution = "толстое"
            elif 40 <= all_data["armour"]:
                constitution = "огромное"
            newline = "\n"
            prompt = f"""
Класс героя:
{all_data["custom_class"].replace(newline, " ")}

Раса героя:
{all_data["custom_race"].replace(newline, " ")}

Навыки:
{all_data["proficiencies"].replace(newline, " ")}

Оружие/инвентарь:
{all_data["equipment"].replace(newline, " ")}

Черты характера: 
{all_data["personality_traits"].replace(newline, " ")}

Идеалы:
{all_data["ideals"].replace(newline, " ")}

Привязанности:
{all_data["bonds"].replace(newline, " ")}

Слабости:
{all_data["flaws"].replace(newline, " ")}

Умения и способности:
{all_data["features_traits"].replace(newline, " ")}

Телосложение:
{constitution}
"""
            imgprompt = generate_text(prompt, system_prompt)
            img_b64 = generate_image(imgprompt)
            return HttpResponse(json.dumps({"img_b64": img_b64}), content_type="application/json")
        elif "create" in request.POST:
            all_data = json.loads(request.POST["all_data"])
            stats = Stats(custom_class=all_data["custom_class"], custom_race=all_data["custom_race"], level=all_data["level"], stre=all_data["stre"], dex=all_data["dex"], cos=all_data["cos"], inte=all_data["inte"], wis=all_data["wis"], cha=all_data["cha"], stre_down=all_data["stre_down"], dex_down=all_data["dex_down"], cos_down=all_data["cos_down"], inte_down=all_data["inte_down"], wis_down=all_data["wis_down"], cha_down=all_data["cha_down"], proficiency_bonus=all_data["proficiency_bonus"], passive_perception=all_data["passive_perception"], stre_saving=all_data["stre_saving"], dex_saving=all_data["dex_saving"], cos_saving=all_data["cos_saving"], inte_saving=all_data["inte_saving"], wis_saving=all_data["wis_saving"], cha_saving=all_data["cha_saving"], acrobatics=all_data["acrobatics"], animals=all_data["animals"], arcana=all_data["arcana"], athletics=all_data["athletics"], deception=all_data["deception"], history=all_data["history"], insight=all_data["insight"], intimidation=all_data["intimidation"], investigation=all_data["investigation"], medicine=all_data["medicine"], nature=all_data["nature"], perception=all_data["perception"], performance=all_data["performance"], persuasion=all_data["persuasion"], religion=all_data["religion"], sleightofhand=all_data["sleightofhand"], stealth=all_data["stealth"], survival=all_data["survival"], proficiencies=all_data["proficiencies"], current_hit=all_data["current_hit"], attacks_spellcasting=all_data["attacks_spellcasting"], equipment=all_data["equipment"], personality_traits=all_data["personality_traits"], ideals=all_data["ideals"], bonds=all_data["bonds"], flaws=all_data["flaws"], features_traits=all_data["features_traits"], success=all_data["success"], failure=all_data["failure"], armour=all_data["armour"], initiative=all_data["initiative"], speed=all_data["speed"])
            img_name = "default.jpg"
            if all_data["image"]:
                img = Image.open(BytesIO(base64.b64decode(all_data["image"])))
                img_name = f"{uuid.uuid4()}.png"
                img.save(f"media/character_pics/{img_name}")
            stats.save()
            if all_data["mode"] == "edit":
                character = Character.objects.get(id=all_data["char_id"])
                character.image = "character_pics/" + img_name
                character.name = all_data["name"]
                character.stats = stats
            else:
                character = Character(image="character_pics/" + img_name, name=all_data["name"], stats=stats, user=request.user)
            character.save()
        elif "edit" in request.POST:
            character = Character.objects.get(id=request.POST["char_id"])
            stats = character.stats
            data = {}
            for key in ["custom_class", "custom_race", "level", "stre", "dex", "cos", "inte", "wis", "cha", "stre_down", "dex_down", "cos_down", "inte_down", "wis_down", "cha_down", "proficiency_bonus", "passive_perception", "stre_saving", "dex_saving", "cos_saving", "inte_saving", "wis_saving", "cha_saving", "acrobatics", "animals", "arcana", "athletics", "deception", "history", "insight", "intimidation", "investigation", "medicine", "nature", "perception", "performance", "persuasion", "religion", "sleightofhand", "stealth", "survival", "proficiencies", "current_hit", "attacks_spellcasting", "equipment", "personality_traits", "ideals", "bonds", "flaws", "features_traits", "success", "failure", "armour", "initiative", "speed"]:
                val = getattr(stats, key)
                data[key] = val if isinstance(val, int) else f'"{val}"'
            data["name"] = f'"{character.name}"'
            
            img = Image.open(character.image.url[1:] if character.image.url.startswith("/") else character.image.url)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode("ascii")
            data["image"] = f'"{img_str}"'
            
            data["char_id"] = character.id
            data["mode"] = '"edit"'
            return render(request, 'users/character.html', data)
        elif "delete" in request.POST:
            character = Character.objects.get(id=request.POST["char_id"])
            character.delete()
        else:
            print(request.POST)
    characters = []
    for character in request.user.character_set.all():
        characters.append({'id': character.id, 'name': character.name, 'image': character.image})
    context = {
        'u_form': u_form,
        'characters': characters
    }
    return render(request, 'users/profile.html', context)
