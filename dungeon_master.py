from users.models import User, Character, Stats
from chat.models import ScenarioFightState
from secret_data import DM_PARAMS
import django
from openai_api import generate_text, generate_text_by_msgs, generate_image_with_url
import re
from asgiref.sync import sync_to_async
import math
import random

MAX_CONTENT_SIZE = 4096
MAX_PERSONAL_CONTENT_SIZE = 512
CHANGING_SCENARIO_PARTS_N = 3
FIGHT_MESSAGES_LAST_INFO_N = 4
MEAN_FIGHT_ROUNDS_K = 4

def extract_parts(text):
    pattern = r'\[\d+\](.*?)(?=\[\d+\]|$)'
    parts = [part.replace("\n", " ") for part in re.findall(pattern, text, re.S)]
    return parts

newline = "\n"

try:
    userDM = User.objects.get(username=DM_PARAMS["username"])
    if Character.objects.filter(user=userDM).exists():
        characterDM = Character.objects.get(user=userDM)
        statsDM = characterDM.stats
    else:
        statsDM = Stats(custom_class="DungeonMaster", custom_race="Master", level=0, stre=0, dex=0, cos=0, inte=0, wis=0, cha=0, stre_down=0, dex_down=0, cos_down=0, inte_down=0, wis_down=0, cha_down=0, proficiency_bonus=0, passive_perception=0, stre_saving=0, dex_saving=0, cos_saving=0, inte_saving=0, wis_saving=0, cha_saving=0, acrobatics=0, animals=0, arcana=0, athletics=0, deception=0, history=0, insight=0, intimidation=0, investigation=0, medicine=0, nature=0, perception=0, performance=0, persuasion=0, religion=0, sleightofhand=0, stealth=0, survival=0, proficiencies=0, current_hit=0, attacks_spellcasting="", equipment="", personality_traits="", ideals="", bonds="", flaws="", features_traits="", success=0, failure=0, armour=0, initiative=0, speed=0)
        statsDM.save()
        characterDM = Character(stats=statsDM, image="character_pics/dm.jpg", name="DungeonMaster", user=userDM)
        characterDM.save()
        print("DM character created")
except Exception:
    userDM, characterDM, statsDM = None, None, None
    print("Cannot import DM")

def get_character_info(character):
    stats = character.stats
    system_prompt = "Твоя задача как можно сильнее сжать следующую информацию так, чтобы она отражала основные характеристики героя. Удаляй ту информацию, которая не сказывается (либо сказывается мало) на характере персонажа! В дальнейшем это будет использоваться как промпт для генерации изображения"
    constitution = "худое"            
    if 10 < stats.armour < 15:
        constitution = "среднее"
    elif 15 <= stats.armour < 25:
        constitution = "крепкое"
    elif 25 <= stats.armour < 40:
        constitution = "толстое"
    elif 40 <= stats.armour:
        constitution = "огромное"
    newline = "\n"
    prompt = f"""
Класс героя:
{stats.custom_class.replace(newline, " ")}

Раса героя:
{stats.custom_race.replace(newline, " ")}

Навыки:
{stats.proficiencies.replace(newline, " ")}

Оружие/инвентарь:
{stats.equipment.replace(newline, " ")}

Черты характера: 
{stats.personality_traits.replace(newline, " ")}

Идеалы:
{stats.ideals.replace(newline, " ")}

Привязанности:
{stats.bonds.replace(newline, " ")}

Слабости:
{stats.flaws.replace(newline, " ")}

Умения и способности:
{stats.features_traits.replace(newline, " ")}

Телосложение:
{constitution}
"""
    return generate_text(prompt, system_prompt, model="gpt-3.5-turbo").replace("\n", "")
    
def classify_personal_prompt(prompt):
    """1 - trash; 2 - general; 3 - ask; 4 - action"""
    system_prompt = """Ты - DungeonMaster в игре Dungeon&Dragons. Тебе поступил запрос одного из героев. Твоя задача классифицировать этот запрос в один из следующих классов:
1) пользователь просто что-то сказал, либо не туда обратился. Скорее всего он не заинтересован в помощи DM/ничего не хочет узнать. Это, так называемый, пустой промпт.
2) обращение пользователя направлено на сокомандников
3) пользователь пытается спросить, можно ли что-то ему сделать (возможно, и как)
4) пользователь совершает какое-то действие

Твой ответ должен быть в формате: [[число]]

Примеры классификации:
"freererh уа" - [[1]]
"баба" - [[1]]
"Эй, боб, привет)" - [[2]]
"Как думаете, я могу это сделать?" - [[2]]
"Я могу заброситься на спину этого дракона?" - [[3]]
"Я хочу взять камень" - [[4]]
"Я ухожу из трактира" - [[4]]
"Я отвечаю: не хочу-небуду" - [[4]]
"Да, я готов" - [[4]]
"Я настаиваю" - [[4]]

Помни, что ты не отвечаешь на запрос пользователя, а лишь классифицируешь его!
"""
    prompt = "Запрос пользователя:\n" + prompt
    out = generate_text(prompt, system_prompt, model="gpt-3.5-turbo")
    try:
        prompt_class = int(re.findall(r'\[\[(\d+)\]\]', out)[0])
        if prompt_class == 2:
            prompt_class = 4
        print('prompt_class', prompt_class, out)
        return prompt_class
    except Exception:
        print("prompt_class. ERROR: 1")
        return 1

def check_need_equipment(prompt):
    "0 - no; 1 - no; 2 - yes"
    system_prompt = """Ты - DungeonMaster в игре Dungeon&Dragons. Герой собирается что-то делать. Твоя задача классифицировать его действия в один из следующих классов:
0) данные действия игрок может совершить без предметов
1) для совершения данных действий игроку необходимы какие-то предметы, но в самом запросе пользователь их уже берет
2) для совершения данных действий игроку необходимы какие-то предметы

Твой ответ должен быть в формате: [[число]]

Примеры классификации:
"Я говорю сгинь!!!!!!" - [[0]]
"Я флиртую с барменом" - [[0]]
"Я взбираюсь на спину дракона" - [[0]]
"Я колдую ауру" - [[0]]
"Я бью его" - [[0]]
"Я беру и бросаю в него камень" - [[1]]
"Я вытягиваю из его ножн нож и пронзаю его ногу" - [[1]]
"Я бью его копьем" - [[2]]
"Я кидаю копье в бошку твари" - [[2]]
"Я стреляю в него" - [[2]]

Помни, что ты не отвечаешь на запрос пользователя, а лишь классифицируешь его!
"""
    prompt = "Действия игрока:\n" + prompt
    out = generate_text(prompt, system_prompt, model="gpt-3.5-turbo")
    try:
        out = int(re.findall(r'\[\[(\d+)\]\]', out)[0])
        print("Need equipment:", out)
        return out
    except Exception:
        print("ERROR. Need equipment: 0")
        return 0

def check_need_spells(prompt):
    "0 - no; 1 - yes"
    system_prompt = """Ты - DungeonMaster в игре Dungeon&Dragons. Тебе поступил запрос одного из героев на совершение действия. Твоя задача классифицировать этот запрос в один из следующих классов:
0) данное действие пользователь может совершить без знание заклятий
1) для совершения данного действия пользователю необходимы знания чар/магии/заклятий

Твой ответ должен быть в формате: [[число]]

Примеры классификации:
"Я говорю сгинь!!!!!!" - [[0]]
"Я флиртую с барменом" - [[0]]
"Я взбираюсь на спину дракона" - [[0]]
"Разговариваю с кроликом" - [[0]]
"Я колдую ауру" - [[1]]
"Бросаюсь огненными шарами" - [[1]]
"Читаю мысли старика" - [[1]]

Помни, что ты не отвечаешь на запрос пользователя, а лишь классифицируешь его!
"""
    prompt = "Запрос пользователя:\n" + prompt
    out = generate_text(prompt, system_prompt, model="gpt-3.5-turbo")
    try:
        out = int(re.findall(r'\[\[(\d+)\]\]', out)[0])
        print("need spells", out)
        return out
    except Exception:
        print("ERROR. need spells 0")
        return 0

def check_spells(prompt, spells):
    "0 - no; 1 - yes"
    prompt = f"""Ты - DungeonMaster в игре Dungeon&Dragons. Тебе поступил запрос одного из героев на совершение заклинания, чар или магии. Твоя задача понять, владеет ли игрок данными навыками.

Твой ответ должен быть в формате: [[число]]
0 - навыка нет; 1 - навык есть

Примеры классификации:

Навыки: владения огнем, владение силами природы, умение взлетать
Запрос: Поджигаю целый лес
Вывод: [[1]]

Навыки: разговор с животными
Запрос: Пытаюсь прочесть мысли у старика
Вывод: [[0]]

Навыки магии у игрока:
{spells}

Запрос игрока:
{prompt}

Помни, что ты не отвечаешь на запрос пользователя, а лишь классифицируешь его!
"""
    out = generate_text(prompt, model="gpt-3.5-turbo")
    try:
        return int(re.findall(r'\[\[(\d+)\]\]', out)[0])
    except Exception:
        return 0

def check_equipment(prompt, equipment):
    "0 - no; 1 - yes"
    prompt = f"""Ты - DungeonMaster в игре Dungeon&Dragons. Тебе поступил запрос одного из героев на совершение действия с использованием предметов. Твоя задача понять, есть ли у игрока в инвентаре необходимые предметы.

Твой ответ должен быть в формате: [[число]]
0 - предмета нет; 1 - предмет есть

Примеры классификации:

Инвентарь: Топор, секира, флейта
Запрос: пытаюсь отрубить секирой голову странника
Вывод: [[1]]

Инвентарь: веревка, камни
Запрос: я создаю рогатку
Вывод: [[1]]

Инвентарь: седло, подопытные мыши и кролики
Запрос: пытаюсь взлететь в воздух с помощью ковра-самолета
Вывод: [[0]]

Инвентарь у игрока:
{equipment}

Запрос игрока:
{prompt}

Помни, что ты не отвечаешь на запрос пользователя, а лишь классифицируешь его!
"""
    out = generate_text(prompt, model="gpt-3.5-turbo")
    try:
        return int(re.findall(r'\[\[(\d+)\]\]', out)[0])
    except Exception:
        return 0

def classify_throws_skills(prompt):
    "0 - nothing; 1 - throws; 2 - skills"
    system_prompt = """Ты - DungeonMaster в игре Dungeon&Dragons. Тебе поступил запрос одного из героев на совершение какого-либо действия. Твоя задача классифицировать этот запрос в один из следующих классов, принимая ввиду, какие навыки пользователю необходимы:
0) запрос не требует никаких навыков
1) запрос требует от пользователя каких-то базовых навыков (силы или ловкости, или телосложения, или мудрости, или харизмы, или восприятия)
2) запрос требует от пользователя каких особых навыков (Акробатика, Анализ, Атлетика, Восприятие, Выживание, Выступление, Запугивание, История, Ловкость рук, Магия, Медицина, Обман, Природа, Проницательность, Религия, Скрытность, Убеждение, Уход за животными)

Твой ответ должен быть в формате: [[число]]

Примеры классификации:
"Я отвечаю: а пошел-ка ты к черту!" - [[0]]
"Я иду и спотыкаюсь об валун" - [[0]]
"Мое животное кидает копье в мантикору" - [[1]] (связано с ловкостью)
"Я пытаюсь флиртовать с барменом" - [[1]] (связано с харизмой)
"Мои глаза вглядываются в темноту" - [[1]] (связано с восприятием)
"Он подманивает едой котенка" - [[2]] (связано с обращением с животными)
"Пытаюсь его вылечить, делая искусственное дыхание" - [[2]] (связано с медициной)
"Своими руками делаю шалаш" - [[2]] (связано с навыками выживания)

Помни, что ты не отвечаешь на запрос пользователя, а лишь классифицируешь его!
"""
    prompt = "Запрос пользователя:\n" + prompt
    out = generate_text(prompt, system_prompt, model="gpt-3.5-turbo")
    try:
        return int(re.findall(r'\[\[(\d+)\]\]', out)[0])
    except Exception:
        return 0

def get_exact_throws(prompt):
    "just indexes"
    system_prompt = """Ты - DungeonMaster в игре Dungeon&Dragons. Тебе поступил запрос одного из героев на совершение какого-либо действия. Твоя задача классифицировать этот запрос в один из следующих классов, принимая ввиду, какие навыки пользователю необходимы:
1) сила
2) ловкость
3) телосложение
4) интеллект
5) мудрость
6) харизма
7) восприятие реальности

Твой ответ должен быть в формате: [[число]]

Примеры классификации:
"Поднимаю это дерево" - [[1]]
"Запрыгиваю на спину огромной змее" - [[2]]
"Кричу всем: 'Посторонись!', - и бегу, снося все вокруг" - [[3]]
"Пытаюсь сопоставить реальность с квантовой вселенной" - [[4]]
"Пытаюсь понять, что эти математические иероглифы означают" - [[5]]
"Уговариваю стражника отдать ключи" - [[6]]
"Присматриваюсь в темноту" - [[7]]

Помни, что ты не отвечаешь на запрос пользователя, а лишь классифицируешь его!
"""
    prompt = "Запрос пользователя:\n" + prompt
    out = generate_text(prompt, system_prompt, model="gpt-3.5-turbo")
    try:
        return int(re.findall(r'\[\[(\d+)\]\]', out)[0])
    except Exception:
        return 7

def get_exact_skills(prompt):
    "just indexes"
    system_prompt = """Ты - DungeonMaster в игре Dungeon&Dragons. Тебе поступил запрос одного из героев на совершение какого-либо действия. Твоя задача классифицировать этот запрос в один из следующих классов, принимая ввиду, какие навыки пользователю необходимы:
1) - Акробатика
2) - Анализ
3) - Атлетика
4) - Восприятие
5) - Выживание
6) - Выступление
7) - Запугивание
8) - История
9) - Ловкость рук
10) - Магия
11) - Медицина
12) - Обман
13) - Природа
14) - Проницательность
15) - Религия
16) - Скрытность
17) - Убеждение
18) - Уход за животными

Твой ответ должен быть в формате: [[число]]

Примеры классификации:
Акробатика [[1]]: Перепрыгнуть через пропасть
Анализ [[2]]: Определить состав зелья
Атлетика [[3]]: Подняться на скалу
Восприятие [[4]]: Замечать скрытые двери
Выживание [[5]]: Найти путь в лесу
Выступление [[6]]: Спеть песню в таверне
Запугивание [[7]]: Заставить стражника отступить
История [[8]]: Узнать о древней руине
Ловкость рук  [[9]]: Украсть ключи незаметно
Магия [[10]]: Распознать заклинание.
Медицина [[11]]: Оказать первую помощь раненому.
Обман [[12]]: Убедить стражу, что ты купец.
Природа [[13]]: Определить опасное растение.
Проницательность [[14]]: Понять, что кто-то лжёт.
Религия [[15]]: Распознать символ бога.
Скрытность [[16]]: Подкрасться к врагу.
Убеждение [[17]]: Уговорить торговца снизить цену.
Уход за животными [[18]]: Успокоить раненую лошадь.

Помни, что ты не отвечаешь на запрос пользователя, а лишь классифицируешь его в формате:
[[число]]
"""
    prompt = "Запрос пользователя:\n" + prompt
    out = generate_text(prompt, system_prompt, model="gpt-3.5-turbo")
    try:
        return int(re.findall(r'\[\[(\d+)\]\]', out)[0])
    except Exception:
        return 5

def create_scenario_parts(characters):
    prompt = """Ты - Dungeon Master в игре Dungeon&Dragons. Твоя задача придумать сценарий так, чтобы каждая его часть представляла из себя какую-то единичную активность. Каждая часть/активность должна быть описана кратко, их должно быть  много (около 10)

Оформляй сценарий в таком виде:
[1]
<Первая часть сценария>
[2]
<Вторая часть сценари>
И т. д.

Ты придумываешь сценарий для следующих героев:"""
    for i, character in enumerate(characters, start=1):
        prompt += f"{i}) " + character.info + "\n"
    prompt += "Попытайся сделать так, чтобы сценарий понравился всем. Помни, что последняя часть сценария должна быть завершающей, не подразумевающей продолжение (но оформляй её также, как и остальные, то есть [число], а НЕ [завершающая])!"
    txt = generate_text(prompt, model="gpt-3.5-turbo")
    parts = extract_parts(txt)
    return parts

def make_content_shorter(content):
    prompt = f"""Ты - Dungeon Master в игре Dungeon&Dragons.Твоя задача как можно сильнее сжать следующую информацию так, чтобы она отражала основные произошедшие события. Удаляй ту информацию, которая не сказывается (либо сказывается мало) на будущем!
Информация:
{content}
"""
    return generate_text(prompt)

@sync_to_async
def sync_make_content_shorter(*args, **kwargs):
    return make_content_shorter(*args, **kwargs)
    

def get_characters_info_prompt(characters):
    prompt = "В твой сценарий играют следующие персонажи:\n"
    charid2id = {}
    for i, character in enumerate(characters, start=1):
        prompt += f"Персонаж {i}: " + character.info + "\n"
        charid2id[character.id] = i + 1
    return prompt

def get_messages_history_prompt(chat, maxn=None, max_content_size=MAX_CONTENT_SIZE, characters=None, use_is_fighting=False):
    if characters is None:
        characters = chat.room.characters.all()
    charid2id = {}
    for i, character in enumerate(characters, start=1):
        charid2id[character.id] = i
    
    messages = []
    full_content = ""
    for i, message in enumerate(reversed(chat.message_set.all())):
        if message.is_fighting and not use_is_fighting:
            continue
        if maxn is not None and i >= maxn:
            break
        if any(message.short_content):
            content = message.short_content
        else:
            content = message.content
        if message.character == characterDM:
            role = "assistant"
        else:
            role = "user"
            content = f"Персонаж {charid2id[message.character.id]}:\n" + content
        if len(full_content + content) > MAX_CONTENT_SIZE:
            content = content[:MAX_CONTENT_SIZE - len(full_content) + 2]
        full_content += content
        messages.insert(0, {"role": role, "content": content})
        if len(full_content) > MAX_CONTENT_SIZE:
            break
    return messages
    
def generate_intro(room):
    characters = room.characters.all()
    current_part = room.scenario.scenariostate.current_part
    prompt = f"""Ты - Dungeon Master в игре Dungeon&Dragons. Тебе будет доступна первая часть сюжета. Тебе необходимо сгенерировать начало.
{get_characters_info_prompt(characters)}

Вот та часть сюжета, которую необходимо сгенерировать:
{current_part.content}

НЕ ПИШИ много текста. НЕ ДЕЛАЙ очень много действий. Помни, что ты в следующий раз также продолжишь сюжет и "подведение к другой части"! Твое сообщение не должно быть большим!
Если тебе требуется говорить за какого-то стороннего персонажа, то говори и сочиняй его речь. Описывай всё окружение"""
    txt = generate_text(prompt)
    return txt

#prompt_class: 3 - ask; 4 - action
def generate_answer(characters, general_chat, chat, prompt_class=4, cannot_make_prompt="", throws_skills_prompt_adding="",
                    is_fighting=False, is_fighting_end=False, fighting_hit=0, dead_monster_info=""):
    scenario_parts = list(general_chat.room.scenario.scenariopart_set.all())
    current_part = general_chat.room.scenario.scenariostate.current_part
    
    if any(cannot_make_prompt):
        insertion = 'контекст, в котором говорится, что игрок не может совершить данное действие по причине: ' + cannot_make_prompt
    elif is_fighting_end:
        insertion = f"конец битвы (герои одержали победу, а их соперник '{dead_monster_info}' погиб. Эту смерть очень важно учесть)"
    elif is_fighting:
        insertion = "продолжение битвы, в которой игрок наносит повреждения сопернику"
    elif prompt_class == 4:
        insertion = 'продолжение сюжета'
    else:
        insertion = 'ответ на вопрос пользователя, но без генерации продолжения сценария' 
    
    prompt0 = f"""Ты - Dungeon Master в игре Dungeon&Dragons. Тебе будут доступны все действия героев до этого момента. Тебе необходимо сгенерировать {insertion}.
{get_characters_info_prompt(characters)}"""
    if not any(cannot_make_prompt) and prompt_class == 4 and not current_part.is_final:
        next_part = scenario_parts[scenario_parts.index(current_part) + 1]
        prompt0 += f"""Помни, что ты - Dungeon Master в игре Dungeon&Dragons. Тебе необходимо сгенерировать {insertion}.
Сейчас игроки находятся в этой части сюжета:
{current_part.content}
"""
    messages = [{"role": "system", "content": prompt0}]
    messages += get_messages_history_prompt(general_chat, characters=characters)
    
    prompt_last = ""
    if is_fighting_end:
        prompt_last += f"""Помни, что ты - Dungeon Master в игре Dungeon&Dragons. Тебе необходимо сгенерировать {insertion}.
Помни, что ты генерируешь продолжение сюжета, поэтому учитывай предыдущую историю.
Ты не должен ими выполнять какие-либо действия. Также ты не должен сразу прекращать сюжет в данном месте.
Если тебе требуется говорить за какого-то стороннего персонажа, то говори и сочиняй его речь. Описывай всё окружение.
НЕ ДЕЛАЙ очень много действий. Твое сообщение не должно быть по размеру средним.
"""
    elif is_fighting:
        prompt_last += f"""Помни, что ты - Dungeon Master в игре Dungeon&Dragons. Тебе необходимо сгенерировать {insertion}.
Ты не должен сразу прекращать сюжет в данном месте.
Если тебе требуется говорить за какого-то стороннего персонажа, то говори и сочиняй его речь. Описывай всё окружение.
НЕ ДЕЛАЙ очень много действий. Твое сообщение не должно быть по размеру средним.

Помни, что герой наносит повреждения! Все поврежддения, которые игрок наносит существу, описывай в формате: [[повреждения]].
Сейчас у игрока базовое количество повреждений "{fighting_hit}", но ты должен добавить к этому значению дополнительные хиты в размере до {fighting_hit} за "креативность" подхода игрока, до {int(fighting_hit * 0.2)} за применение оружия и до {int(fighting_hit * 0.2)} за применение магии
Пример добавления хитов при базовых {fighting_hit}:
1) Промпт: я ударяю его кулаком
Добавление за креативность: 0
Добавление за оружие: 0
Добавление за магию: 0
2) Промпт: я, размахиваясь мечом и стреляя из лука, пронзаю этого монстра, затем создаю огненный шар и пуляюсь им
Добавление за креативность: {int(fighting_hit * 0.5)}
Добавление за оружие: 0
Добавление за магию: {int(fighting_hit * 0.1)}
3) Промпт: я взбираюсь на спину монстра и вонзаю меч между его крыльев так, чтобы тот засвирипел. И призывая силы земли, чтобы они сцепили его
Добавление за креативность: {int(fighting_hit * 0.85)}
Добавление за оружие: {int(fighting_hit * 0.05)}
Добавление за магию: {int(fighting_hit * 0.13)}

Помни, что за какие-то простые запросы (например, "я ударил его мечом") дополнительное количество повреждений должно быть как можно меньше. Также не пиши никаких примеров в [[...]], единственный верный формат: [[число]], причем это число - СУММА повреждений
"""
    elif not any(cannot_make_prompt):
        if prompt_class == 4:
            if current_part.is_final:
                prompt_last += """\nНа данный момент герои находятся на финальной части сценария. Тебе необходимо закончить сюжет. Ты не обязан ими выполнять какие-либо действия
Если тебе требуется говорить за какого-то стороннего персонажа, то говори и сочиняй его речь. Описывай всё окружение
"""
            else:
                next_part = scenario_parts[scenario_parts.index(current_part) + 1]
                prompt_last += f"""
Ты должен учитывать, что игроки двигаются по сюжету в эту сторону:
{next_part.content}

Помни, что ты - Dungeon Master в игре Dungeon&Dragons. Тебе необходимо сгенерировать {insertion}.
Помни, что ты генерируешь продолжение сюжета, поэтому учитывай предыдущую историю.
Ты не должен ими выполнять какие-либо действия. Также ты не должен сразу прекращать сюжет в данном месте.
Если тебе требуется говорить за какого-то стороннего персонажа, то говори и сочиняй его речь. Описывай всё окружение.
НЕ ДЕЛАЙ очень много действий. Твое сообщение не должно быть по размеру средним.
""" 
        else:
            messages += get_messages_history_prompt(chat, characters=characters, max_content_size=MAX_PERSONAL_CONTENT_SIZE)
            prompt_last += "Помни, что ты лишь отвечаешь на вопрос пользователя, а не генерируешь сценарий! Если требуется, то дай рекомендации/советы игроку"
    else:
        prompt_last += "Помни, что ты лишь генерируешь контекст для отказа игроку в действии, а не генерируешь сценарий! Если требуется, то дай рекомендации/советы игроку"
    if any(throws_skills_prompt_adding):
        messages += [{"role": "system", "content": throws_skills_prompt_adding}]
        prompt_last += "\n\nНЕ ЗАБЫВАЙ УЧЕСТЬ РЕЗУЛЬТАТ ПОСЛЕДНЕГО БРОСКА КУБИКА ИГРОКОМ"
    messages += [{"role": "system", "content": prompt_last}]
    txt = generate_text_by_msgs(messages=messages)
    if is_fighting:
        try:
            hit = max([int(i) for nums in re.findall(r'\[\[(.*?)\]\]', txt) + re.findall(r'\*\*(.*?)\*\*', txt) for i in re.findall(r'\d+', nums)])
        except Exception as ex:
            print("ERROR: ", ex)
            hit = fighting_hit
        current_part.scenario.scenariostate.refresh_from_db()
        current_part.scenario.scenariostate.fight_state.refresh_from_db()
        fight_state = current_part.scenario.scenariostate.fight_state
        fight_state.health = max(0, fight_state.health - hit)
        fight_state.save()
        txt += f"\n\nИтого ты наносишь {hit} урона. Осталось: {fight_state.health}"
    return txt

def check_next_part(general_chat):
    """0 - no; 1 - yes"""
    scenario_parts = list(general_chat.room.scenario.scenariopart_set.all())
    current_part = general_chat.room.scenario.scenariostate.current_part
    current_part_ind = scenario_parts.index(current_part)
    if not current_part.is_final:
        next_part = scenario_parts[current_part_ind + 1]
    
    prompt0 = f"""Ты - Dungeon Master в игре Dungeon&Dragons. Тебе будут доступны все действия героев до этого момента. Тебе необходимо понять, перешел ли сюжет к следующей части."""
    messages = [{"role": "system", "content": prompt0}]
    messages += get_messages_history_prompt(general_chat)
    prompt_last = f"""Твой вывод должен быть в формате:
[[0]] - герои НЕ достигли {'следующей части сценария' if not current_part.is_final else 'финала, и сюжет заканчивается'}
[[1]] - герои достигли {'следующей части сценария' if not current_part.is_final else 'финала, и сюжет заканчивается'}

Нынешняя часть сценария:
{current_part.content}
"""
    if not current_part.is_final:
        prompt_last += f"""Следующая часть сценария:
{next_part.content}"""
    prompt_last += """
Помни, что тебе необходимо понять, перешел ли сюжет к следующей части (или вообще уже её прошел/достиг)."""
    messages += [{"role": "system", "content": prompt_last}]
    out = generate_text_by_msgs(messages=messages)
    try:
        out = int(re.findall(r'\[\[(\d+)\]\]', out)[0])
        print(f'current part: {current_part_ind}, next part?', out)
        return out
    except Exception:
        print(f'ERROR. current part: {current_part_ind}, next part, out:', out)
        return 1

@sync_to_async
def sync_check_next_part(*args, **kwargs):
    return check_next_part(*args, **kwargs)

@sync_to_async
def sync_generate_answer(*args, **kwargs):
    return generate_answer(*args, **kwargs)

def what_equipment_changed(message):
    "[0] - no; [1, cmd, items] - yes"
    system_prompt = """Ты - DungeonMaster в игре Dungeon&Dragons. Ты уже создал часть событий, в которых участвует игрок. Твоя задача узнать, изменится ли инвентарь игрока в течение данной части сценария. Если изменится, то понять, как и что именно измениться в инвентаре.

Твой вывод может быть представлен в следующих видах:
[[0]] - инвентарь не изменится
[[1]] [[действие (например, добавить, удалить)]] [[над какими предметами происходит действие]] - инвентарь изменится так: к нему необходимо применить какие-то указанные действия к указанным предметам

Примеры ответов:

1)
Запрос игрока:
На ярмарке царила атмосфера веселья: вокруг слышались смех и звуки толпы, яркие костюмы и шалости уличных артистов привлекали внимание. Бард, настроившись на выступление, заметил, как внимание зрителей постепенно переключается на него.
Он берет в руки лютню и начинает играть живую мелодию, вызывая восторг у зрителей.
Вывод:
[[0]]

2)
Запрос игрока:
Ты пытаешься ударить стражника, но безуспешно. Тогда ты колдуешь магию: создаешь огненный шар, которым сжигаешь все его тело.
Ты снимаешь с него доспехи, но решаешь их выбросить. Присматриваясь к оружие, ты решаешь забрать копье и щит.
Вывод:
[[1]] [[добавить]] [[копье и щит]]

3)
Запрос игрока:
Во время представления Бард ощущает, что этот незнакомец может знать что-то важное о пропавшем артефакте. Попробовать Разговорить его — не сработает ли удача? Ты решаешь подарить ему лютню.
Вывод:
[[1]] [[удалить]] [[лютня]]

Помни, что ситуации, когда необходимо что-то сделать с инвентарем, не частые - проводи изменения только в явных случаях.
"""
    prompt = "Запрос игрока:\n" + message
    out = generate_text(prompt, system_prompt, model="gpt-3.5-turbo")
    try:
        out = re.findall(r'\[\[(.*?)\]\]', out)[:3]
        if out[0] not in [0, 1]:
            out[0] = 0
        out[0] = int(out[0])
        return out
    except Exception:
        return [0]



def change_equipment(equipment, cmd, character_info):
    system_prompt = f"""Ты - DungeonMaster в игре Dungeon&Dragons. Игрок совершил какое-то действие, после которого его инвентарь должен измениться. Тебе необходимо изменить его инвентарь согласно приведенной команде.

Твой ответ должен практически полностью совпадать с инвентарем игрока - тебе необходимо лишь внести некоторые изменения. 

Примеры изменений инвентаря:

1) Инвентарь игрока:
У меня есть щипцы (не знаю, зачем они), кожа щуки, голова тролля
Комманда:
добавить камень
Вывод:
У меня есть щипцы (не знаю, зачем они), кожа щуки, голова тролля. А также камень.

2) Инвентарь игрока:
Недавно я прихватил щит охранника и его доспехи
Не забываем, что ещё и есть чья-то рука
Комманда:
удалить щит и копье
Вывод:
Недавно я прихватил доспехи охранника
Не забываем, что ещё и есть чья-то рука

3) Инвентарь игрока:

Комманда:
добавить голова тролля
Вывод:
Голова тролля

Тебе необходимо произвести изменения над следующим инвентарем:
Инвентарь игрока:
{equipment}

Команда:
{cmd}

Также тебе известна информация о героя:
{character_info}

Помни, что твой ответ должен практически полностью совпадать с инвенарем игрока. 
"""
    out = generate_text(prompt, model="gpt-3.5-turbo")
    return out

def need_change_scenario(general_chat):
    return 1

def combine_scenarios(content_scenario1, content_scenario2):
    prompt = f"""Ты - Dungeon Master в игре Dungeon&Dragons. Тебе необходимо объединить две части сюжета в одну. Ты также можешь ужалять ненужную информацию, которая никак на сюжет не влияет
Первая часть сюжета:
{content_scenario1}

Вторая часть сюжета:
{content_scenario2}

Ответ дай в виде объединенной части сюжета (без каких-либо личных комментариев). Преимущество сюжета оставляй за первой частью. Не объединяй части типами "но", "а", только как объединение, а не замещение
"""
    return generate_text(prompt)


def change_scenario(general_chat, throws_skills_prompt_adding=""):
    "0 - no; 1 - yes"
    characters = general_chat.room.characters.all()
    prompt0 = f"""Ты - Dungeon Master в игре Dungeon&Dragons. Тебе будут доступны все действия героев до этого момента. Действия героев привели к какому-то (возможно, небольшому) изменению сценария. Твооей задачей будет немного изменить сюжет так, чтобы он подстроился под действия героев.
Герои:
{get_characters_info_prompt(characters)}
"""
    messages = [{"role": "system", "content": prompt0}]
    messages += get_messages_history_prompt(general_chat)
    
    scenario_parts = list(general_chat.room.scenario.scenariopart_set.all())
    current_part = general_chat.room.scenario.scenariostate.current_part
    if current_part.is_final:
        return
    current_part_ind = scenario_parts.index(current_part)
    if any(throws_skills_prompt_adding):
        messages += [{"role": "system", "content": throws_skills_prompt_adding}]
    last_prompt = f"""Тебе необходимо изменить сценарий так, чтобы он подстраивался под последние события. Все части должны быть описаны ОЧЕНЬ кратко.
Часть сюжета на которой остановились:
{current_part.content}

Тебе необходимо изменить следующую часть сюжета (но помни, что основная идея этой части сценария должна остаться, анпример, какие-то предметы/существа/действия в нем):
{scenario_parts[current_part_ind + 1].content}
"""
    messages += [{"role": "system", "content": last_prompt}]
    txt = generate_text_by_msgs(messages=messages, model="gpt-4o")
    txt = make_content_shorter(combine_scenarios(scenario_parts[current_part_ind+1].content, txt))
    print("New scenario before:", scenario_parts[current_part_ind+1].content)
    scenario_parts[current_part_ind+1].content = txt
    scenario_parts[current_part_ind+1].save()
    print("Current part:", current_part.content)
    print("New scenario parts:", scenario_parts[current_part_ind+1].content)

def is_starting_fight(general_chat):
    """0 - no; 1 - yes"""
    characters = general_chat.characters.all()
    prompt0 = f"Ты - Dungeon Master в игре Dungeon&Dragons. Тебе будут доступны все действия героев до этого момента. Тебе необходимо понять, последние действия игроков начнут какую-то драку/битву или нет."
    messages = [{"role": "system", "content": prompt0}]
    messages += get_messages_history_prompt(general_chat, maxn=FIGHT_MESSAGES_LAST_INFO_N, characters=characters)
    
    prompt_last = f"""
Помни, что ты - Dungeon Master в игре Dungeon&Dragons. Тебе необходимо понять, последние действия игроков начнут какую-то драку/битву или нет.
Выведи ответ в формате:
[[0]] - битва не начнется
[[1]] - битва начнется

Примеры классификаций:
Сюжет: На отдых вы решили взремнуть, но к вам подкрадывается группа грабителей
Вывод: [[0]]
Пояснение: они лишь подкрадываются, но не нападают

Сюжет: после прогулки и захода в таверну ты решаешь присмотреться к посетителям. "Я ударяю его в голову"
Вывод: [[1]]
Пояснение: здесь явное начало драки

Помни, что герои не могут бороться между собой. Герои:
{get_characters_info_prompt(characters)}
"""
    messages += [{"role": "system", "content": prompt_last}]
    out = generate_text_by_msgs(messages=messages, model="gpt-3.5-turbo")
    try:
        out = int(re.findall(r'\[\[(\d+)\]\]', out)[0])
        print(f"is starting fight: {out}")
        return out
    except Exception:
        print(f'ERROR. is fighting start: 0 ', out)
        return 0

def get_mean_rand_stat(stat_vals):
    return int(max(0, sum(stat_vals) + random.randint(0, int(sum(stat_vals) / 3))) / len(stat_vals))

def start_fight(general_chat):
    characters = general_chat.room.characters.all()
    
    characters_hits = [char.stats.current_hit for char in characters]
    mean_hit = get_mean_rand_stat(characters_hits)
    health = mean_hit * len(characters) * MEAN_FIGHT_ROUNDS_K
    
    characters_levels = [char.stats.level for char in characters]
    mean_level = get_mean_rand_stat(characters_levels)
    monster_class = mean_level + 1
    
    characters_initiatives = [max(0, char.stats.initiative) for char in characters]
    mean_initiative = get_mean_rand_stat(characters_initiatives)
    monster_initiative = mean_initiative
    
    inititatives = []
    while any([inititatives.count(elem) > 1 for elem in inititatives]) or len(inititatives) == 0:
        inititatives = [char.stats.initiative + random.randint(1, 20) for char in characters] + [monster_initiative + random.randint(1, 20)]
    inititatives = [(initiative, i) for i, initiative in enumerate(inititatives)]
    inititatives.sort(reverse=True)
    
    initiative_order = [(pair[1] if pair[1] != len (characters) else -1, pair[0]) for pair in inititatives] # if it is monster than -1
    
    cube_class = random.choices([4, 6, 8, 10, 12, 16, 20], weights=[5, 10, 45, 60, 45, 20, 10])[0]
    
    
    prompt0 = f"""Ты - Dungeon Master в игре Dungeon&Dragons. Тебе будут доступны все действия героев до этого момента. Герои приняли бой с кем-то. Тебе необходимо будет выяснить, с кем именно они борются
Примеры:
Сюжет: Два героя решили передохнуть в таверне. Один из них решил не скучать и ударил бармена по голове
Вывод: [[бармен]]

Сюжет: на отчаянных героев в пещере напал дракон. Он дышит огнем, готов всех испепелить
Вывод: [[дракон]]"""
    messages = [{"role": "system", "content": prompt0}]
    messages += get_messages_history_prompt(general_chat, maxn=FIGHT_MESSAGES_LAST_INFO_N, characters=characters, use_is_fighting=True)
    prompt_last = f"""
Ты - Dungeon Master в игре Dungeon&Dragons. Тебе необходимо будет выяснить, с кем именно игроки борются (помни, что герои не могут бороться между собой)
Выведи ответ в формате:
[[имя/название существ, с которыми начинается битва]]

Помни, что игроки не могут бороться между собойю Их персонажи:
{get_characters_info_prompt(characters)}
"""
    messages += [{"role": "system", "content": prompt_last}]
    monster_info = generate_text_by_msgs(messages=messages)
    print("monster_info", monster_info)
    try:
        monster_info = re.findall(r'\[\[(.*?)\]\]', monster_info)[0]
    except Exception as ex:
        print("monster_info error: ", ex)
        monster_info = "неопределенный"
    
    out = f"""Ваши действия приводят к битве с "{monster_info}".
Его здоровье: {health}
Его уровень: {monster_class}
Его кубики хитов: {monster_class}к{cube_class}

Инициатива распределена в следующем порядке (определяется как [личная инициатива + 1к20]):"""
    for chari, initiative in initiative_order:
        if chari == -1:
            out += f"\n{monster_info} (инициатива: {monster_initiative}+{initiative-monster_initiative}={initiative})"
        else:
            out += f"\n{characters[chari].name} (инициатива: {characters[chari].stats.initiative}+{initiative-characters[chari].stats.initiative}={initiative})"
    
    fight_state = ScenarioFightState(monster_info=monster_info, health=health, monster_class=monster_class, cube_class=cube_class, initiative_order=" ".join(map(lambda x: str(x[0]), initiative_order)))
    fight_state.save()
    general_chat.room.scenario.scenariostate.fight_state = fight_state
    general_chat.room.scenario.scenariostate.save()
    print(general_chat.room.scenario)
    return out

def generate_fight_turn(general_chat):
    """0 - no; 1 - yes"""
    characters = general_chat.room.characters.all()
    fight_state = general_chat.room.scenario.scenariostate.fight_state
    
    character_fight = None
    while character_fight is None or character_fight == characterDM or character_fight.stats.failure >= 3:
        character_fight = random.choice(characters)
    is_character_dying = character_fight.stats.success or character_fight.stats.failure or character_fight.stats.armour <= 0
    hits = []
    for _ in range(fight_state.monster_class):
        hits.append(random.randint(1, fight_state.cube_class))
    hit = sum(hits)    
    
    fight_state = general_chat.room.scenario.scenariostate.fight_state
    prompt0 = f"""Ты - один из существ в игре Dungeon&Dragons. С тобой в битву вступили герои. Тебе будут доступны все действия героев до этого момента. Тебе необходимо описать свои действия с учетом своих статистик
{get_characters_info_prompt(characters)}\n

Статистики существа/существ/соперников:
Название: {fight_state.monster_info}
Уровень соперника: {fight_state.monster_class}
Какого персонажа соперник атакует: {character_fight.info}
"""
    messages = [{"role": "system", "content": prompt0}]
    messages += get_messages_history_prompt(general_chat, characters=characters, use_is_fighting=True)
    
    prompt_last = f"""
Помни, что ты - {fight_state.monster_info} в игре Dungeon&Dragons. Тебе необходимо свой ход в битве, а именно описать его. Ты не должен кидать никаких кубиков и писать, сколько урона ты нанес - только генерировать описание своих действий"""
    messages += [{"role": "system", "content": prompt_last}]
    txt = generate_text_by_msgs(messages=messages)
    
    adding = f"""Ход соперника.
Его здоровье: {fight_state.health}
Его уровень: {fight_state.monster_class}
Его кубики атаки: {fight_state.monster_class}к{fight_state.cube_class}
Его значение атаки: {'+'.join(map(str, hits))}={hit}
Он наносит {hit} урона персонажу {character_fight.name}, у которого остается {max(0, character_fight.stats.armour - hit)} здоровья
{"" if character_fight.stats.armour > 0 else "Так как у персонажа уже было 0 здоровья, то он получает проваленный спасбросок"}
"""
    last_adding = "\n\n"
    if is_character_dying:
        last_adding += "Помираемому персонажу нанесли урон - этот персонаж получает проваленный спасбросок от смерти\n\n"
        character_fight.stats.failure += 1
    else:
        character_fight.stats.armour = max(0, character_fight.stats.armour - hit)
        if character_fight.stats.armour <= 0:
            last_adding += "Персонажу нанесли критический для здоровья урон - теперь он находится на гране смерти и стабилизируется\n\n"
            character_fight.stats.armour = 0
    if character_fight.stats.failure >= 3:
        last_adding += "Персонаж помирает: у него 3 проваленных спасброска от смерти\n\n"
    character_fight.stats.save()
    return adding + txt + last_adding

def generate_failed_battle(general_chat):
    characters = general_chat.room.characters.all()
    fight_state = general_chat.room.scenario.scenariostate.fight_state
    prompt0 = f"""Ты - Dungeon Master в игре Dungeon&Dragons. Тебе будут доступны все действия героев до этого момента. Герои приняли бой с кем-то. Во время этого боя все игроки погибли и партия закончилась. Тебе необходимо будет сгенерировать конец сюжета.
{get_characters_info_prompt(characters)}\n

Название существа/существ/соперников: {fight_state.monster_info}
"""
    messages = [{"role": "system", "content": prompt0}]
    messages += get_messages_history_prompt(general_chat, characters=characters, use_is_fighting=True)

    prompt_last = f"""
Ты - Dungeon Master в игре Dungeon&Dragons. Герои приняли бой с {fight_state.monster_info}. Во время этого боя все игроки погибли и партия закончилась. Тебе необходимо будет сгенерировать конец сюжета."""
    messages += [{"role": "system", "content": prompt_last}]
    txt = generate_text_by_msgs(messages=messages)
    return txt

@sync_to_async
def sync_generate_failed_battle(*args, **kwargs):
    return generate_failed_battle(*args, **kwargs)

def generate_image_scenario(general_chat, prefolder="", outsize=None):
    characters = general_chat.room.characters.all()
    prompt0 = f"""Ты - Dungeon Master в игре Dungeon&Dragons. Тебе будут доступны все действия героев до этого момента. Действия героев следующей завязке сюжета. Твооей задачей будет сгенерировать промпт, описывающий последние действия. Этот промпт в дальнейшем будет использоваться для генерации изображений, поэтому ты имеешь право удалять ту информацию, которая не сказывается на картине сюжета.
Герои:
{get_characters_info_prompt(characters)}
"""
    messages = [{"role": "system", "content": prompt0}]
    messages += get_messages_history_prompt(general_chat)
    
    scenario_parts = list(general_chat.room.scenario.scenariopart_set.all())
    current_part = general_chat.room.scenario.scenariostate.current_part
    current_part_ind = scenario_parts.index(current_part)
    last_prompt = f"""Действия героев следующей завязке сюжета. Твооей задачей является генерация промпта, описывающего последние действия. Этот промпт в дальнейшем будет использоваться для генерации изображений, поэтому ты имеешь право удалять ту информацию, которая не сказывается на картине сюжета.
Часть сюжета, к которой герои перешли:
{current_part.content}

Герои:
{get_characters_info_prompt(characters)}

Помни, что ты лишь генерируешь промпт для генерации изображения - ты не должен как-то его комментировать или отвечать на вопросы игроков. Также он должен быть кратким.
"""
    messages += [{"role": "system", "content": last_prompt}]
    
    txt = generate_text_by_msgs(messages=messages)
    print("image prompt:", txt)
    return generate_image_with_url(txt, prefolder=prefolder, outsize=outsize)

@sync_to_async
def sync_generate_image_scenario(*args, **kwargs):
    return generate_image_scenario(*args, **kwargs)