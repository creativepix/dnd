from users.models import User, Character, Stats
from secret_data import DM_PARAMS
import django
from openai_api import generate_text, generate_text_by_msgs
import re
from asgiref.sync import sync_to_async

MAX_CONTENT_SIZE = 4096
MAX_PERSONAL_CONTENT_SIZE = 512
CHANGING_SCENARIO_PARTS_N = 3

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
"Я беру и бросаю в него камень" - [[1]]
"Я вытягиваю из его ножн нож и пронзаю его ногу" - [[1]]
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
        return int(re.findall(r'\[\[(\d+)\]\]', out)[0])
    except Exception:
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
    prompt = """Ты - Dungeon Master в игре Dungeon&Dragons. Твоя задача придумать сценарий так, чтобы каждая его часть представляла из себя какую-то единичную активность. Каждая часть/активность должна быть описана кратко, их должно быть много (около 10)

Оформляй сценарий в таком виде:
[1]
<Первая часть сценария>
[2]
<Вторая часть сценари>
И т. д.

Ты придумываешь сценарий для следующих героев:"""
    for i, character in enumerate(characters, start=1):
        prompt += f"{i}) " + character.info + "\n"
    prompt += "Попытайся сделать так, чтобы сценарий понравился всем. Помни, что последняя часть сценария должна быть завершающей, не подразумевающей продолжение!"
    txt = generate_text(prompt, model="gpt-3.5-turbo")
    print(txt)
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

def get_messages_history_prompt(chat, max_content_size=MAX_CONTENT_SIZE, characters=None):
    if characters is None:
        characters = chat.room.characters.all()
    charid2id = {}
    for i, character in enumerate(characters, start=1):
        charid2id[character.id] = i
    
    messages = []
    full_content = ""
    for message in reversed(chat.message_set.all()):
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
def generate_answer(characters, general_chat, chat, prompt_class=4, cannot_make_prompt="", throws_skills_prompt_adding=""):
    scenario_parts = list(general_chat.room.scenario.scenariopart_set.all())
    current_part = general_chat.room.scenario.scenariostate.current_part
    
    if any(cannot_make_prompt):
        insertion = 'контекст, в котором говорится, что игрок не может совершить данное действие по причине: ' + cannot_make_prompt
    elif prompt_class == 4:
        insertion = 'продолжение сюжета'
    else:
        #if prompt_class == 3:
        insertion = 'ответ на вопрос пользователя, но без генерации продолжения сценария' 
    
    prompt0 = f"""Ты - Dungeon Master в игре Dungeon&Dragons. Тебе будут доступны все действия героев до этого момента. Тебе необходимо сгенерировать {insertion}.
{get_characters_info_prompt(characters)}"""
    if not any(cannot_make_prompt) and prompt_class == 4 and not current_part.is_final:
        
        next_part = scenario_parts[scenario_parts.index(current_part) + 1]
        prompt0 += f"""Помни, что ты - Dungeon Master в игре Dungeon&Dragons. Тебе необходимо сгенерировать {insertion}.
Сейчас игроки находятся в этой части сюжета:
{current_part.content}

Ты должен учитывать, что игроки двигаются по сюжету в эту сторону:
{next_part.content}
"""

    messages = [{"role": "system", "content": prompt0}]
    messages += get_messages_history_prompt(general_chat, characters=characters)
    
    next_part = scenario_parts[scenario_parts.index(current_part) + 1]
    prompt_last = ""
    if not any(cannot_make_prompt):
        if prompt_class == 4:
            if current_part.is_final:
                prompt_last += """\nНа данный момент герои находятся на финальной части сценария. Тебе необходимо подвести их к финалу/заключению, но помни, что ты их лишь подводишь! Ты не обязан ими выполнять какие-либо действия. Также не обязан сразу прекращать сюжет в данном месте - сюжет нужно прекращать, только если герои сами подошли к заключинию (а не ты их резко за ручку привел)
Если тебе требуется говорить за какого-то стороннего персонажа, то говори и сочиняй его речь. Описывай всё окружение
"""
            else:
                prompt_last += f"""
Ты должен учитывать, что игроки двигаются по сюжету в эту сторону:
{next_part.content}

Помни, что ты - Dungeon Master в игре Dungeon&Dragons. Тебе необходимо сгенерировать {insertion}.
Помни, что ты генерируешь продолжение сюжета, поэтому учитывай предыдущую историю.
Ты не должен ими выполнять какие-либо действия. Также ты не должен сразу прекращать сюжет в данном месте.
Если тебе требуется говорить за какого-то стороннего персонажа, то говори и сочиняй его речь. Описывай всё окружение.
НЕ ДЕЛАЙ очень много действий. Твое сообщение не должно быть по размеру средним.
"""
#                prompt_last += f"""\nТебе необходимо подводить игроков к следующей части сюжета:
#{next_part.content}
#
#Помни, что тебе необходимо ПОДВЕСТИ их к следующему этапу, но помни, что ты их лишь подводишь! Ты не обязан ими выполнять какие-либо действия. Также ты не должен сразу прекращать сюжет в данном месте.
#Если тебе требуется говорить за какого-то стороннего персонажа, то говори и сочиняй его речь. Описывай всё окружение
#НЕ ПИШИ много текста. НЕ ДЕЛАЙ очень много действий. Помни, что ты в следующий раз также продолжишь сюжет и "подведение к другой части"! Твое сообщение не должно быть большим!
#"""
                
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
    #print(messages)
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
    print(messages)
    out = generate_text_by_msgs(messages=messages)
    #print(messages)
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
#    "0 - no; 1 - yes"
#    prompt0 = f"""Ты - Dungeon Master в игре Dungeon&Dragons. Тебе будут доступны все действия героев до этого момента. Тебе необходимо будет понять, приведут ли последние действия героев к изменению сюжета."""
#    messages = [{"role": "system", "content": prompt0}]
#    messages += get_messages_history_prompt(general_chat)
#    
#    scenario_parts = list(general_chat.room.scenario.scenariopart_set.all())
#    current_part = general_chat.room.scenario.scenariostate.current_part
#    current_part_ind = scenario_parts.index(current_part)
#    scenario_prompt = """Тебе даны следующие части сюжета (каждое начало части в формате [часть] ):
#"""
#    for i, scenario_part in enumerate(scenario_parts[current_part_ind:min(len(scenario_parts), current_part_ind+CHANGING_SCENARIO_PARTS_N)], start=current_part_ind+1):
#        scenario_prompt += f"[{i}]\n{scenario_part.content}\n"
#    messages += [{"role": "system", "content": scenario_prompt}]
#    last_prompt = """Тебе необходимо понять, изменится ли сюжет после действий героев или нет. Ответь в формате:
#[[0]] - сценарий не изменится (например, идет какой-то разговор, игроки куда-то свернули/пришли)
#[[1]] - сценарий изменится (например, игроки нарушают порядок действий, решают идти иным путем)
#
#Пример вывода:
#[[0]]
#"""
#    messages += [{"role": "system", "content": last_prompt}]
#    out = generate_text_by_msgs(messages)
#    try:
#        out = int(re.findall(r'\[\[(\d+)\]\]', out)[0])
#        print(f'scenario change:', out)
#        return out
#    except Exception:
#        print(f'ERROR. scenario change: {current_part_ind}, out:', out)
#        return 0
#    txt = generate_text_by_msgs(messages=messages)
#    print(messages)

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
    current_part_ind = scenario_parts.index(current_part)
    if any(throws_skills_prompt_adding):
        messages += [{"role": "system", "content": throws_skills_prompt_adding}]
    #messages += [{"role": "system", "content": scenario_prompt}]
    last_prompt = f"""Тебе необходимо изменить сценарий так, чтобы он подстраивался под последние события. Все части должны быть описаны ОЧЕНЬ кратко.
Часть сюжета на которой остановились:
{current_part.content}

Тебе необходимо изменить следующую часть сюжета (но помни, что основная идея этой части сценария должна остаться, анпример, какие-то предметы/существа/действия в нем):
{scenario_parts[current_part_ind + 1].content}
"""
    messages += [{"role": "system", "content": last_prompt}]
    print(messages)
    #for i, scenario_part in enumerate(scenario_parts[current_part_ind:min(len(scenario_parts), current_part_ind+CHANGING_SCENARIO_PARTS_N+1)], start=current_part_ind+1):
    #    messages += [{"role": "user", "content": f"[{i}]\n{scenario_part.content}\n"}]
    #print(messages)
    txt = generate_text_by_msgs(messages=messages, model="gpt-4o")
    txt = make_content_shorter(combine_scenarios(scenario_parts[current_part_ind+1].content, txt))
    print("New scenario before:", scenario_parts[current_part_ind+1].content)
    scenario_parts[current_part_ind+1].content = txt
    scenario_parts[current_part_ind+1].save()
    print("Current part:", current_part.content)
    print("New scenario parts:", scenario_parts[current_part_ind+1].content)
    #new_parts_content = extract_parts(txt)[1:]
    #for i in range(len(new_parts_content)):
    #    new_parts_content[i] = make_content_shorter(new_parts_content[i])
    #print("Current part:", current_part.content)
    ##shorted_new_parts_content = []
    #print("New scenario parts:", txt)
    #for new_scenario_part_content, scenario_part in zip(new_parts_content, scenario_parts[current_part_ind+1:min(len(scenario_parts), current_part_ind+CHANGING_SCENARIO_PARTS_N+1)]):
    #    #scenario_part.content = make_content_shorter(new_scenario_part_content)
    #    scenario_part.content = new_scenario_part_content.replace("...", "")
    #    scenario_part.save()
    #    #shorted_new_parts_content.append(scenario_part.content)
    #print("New short scenario parts:", shorted_new_parts_content)
