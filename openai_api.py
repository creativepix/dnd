from openai import OpenAI
from io import BytesIO
import base64
from PIL import Image
from secret_data import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
tokens_used = int(open("tokens_used").read())

def generate_text(txt, system_txt=None, model="gpt-4o-mini"):
    global tokens_used
    messages = []
    if system_txt:
        messages.append({"role": "system", "content": system_txt})
    messages.append({"role": "user", "content": txt})
    completion = client.chat.completions.create(
        model=model,
        messages=messages
    )
    tokens_used += completion.usage.total_tokens
    with open("tokens_used", "w") as f:
        f.write(str(tokens_used))
    message = completion.choices[0].message.content
    return message

def generate_text_by_msgs(messages, model="gpt-4o-mini"):
    global tokens_used
    completion = client.chat.completions.create(
        model=model,
        messages=messages
    )
    tokens_used += completion.usage.total_tokens
    with open("tokens_used", "w") as f:
        f.write(str(tokens_used))
    message = completion.choices[0].message.content
    return message

def generate_image(txt, model="dall-e-2", res="256x256", outformat="b64"):
    """format: b64/img (img=PIL.Image)"""
    engcount = sum([el in "qwertyuiopoasdfghjklzxcvbnm" for el in txt])
    ruscount = sum([el in "йцукенгшщзхъфывапролджэячсмитьбю" for el in txt])
    if ruscount > engcount and model == "dall-e-2":
        prompt = "Переведи следующий текст на английский:\n" + txt
        txt = generate_text(prompt)
    response = client.images.generate(
        model=model,
        prompt=txt,
        quality="standard",
        size=res,
        n=1,
        response_format="b64_json"
    )
    if outformat == "b64":
        return response.data[0].b64_json
    img = Image.open(BytesIO(base64.b64decode(response.data[0].b64_json)))
    return img


"""
main_prompt = f""
Ты - Dungeon Master в игре Dungeon&Dragons. Твоя задача придумать сценарий так, чтобы каждая его часть представляла из себя какую-то единичную активность. Каждая часть/активность должна быть описана кратко. Активностей должно быть много (около 15 штук)

Оформляй сценарий в таком виде:
[1]
<Первая часть сценария>
[2]
<Вторая часть сценария>
И т. д.

Ты придумываешь сценарий для следующих героев:""
for i, character_info zip(range(1, len(character_info) + 1), character_info):
    main_prompt += "1) " + character_info + "\n\n"
main_prompt += "Попытайся сделать так, чтобы сценарий понравился всем. Помни, что ты не обязан говорить, как кто поступит, так как действия выбирают сами герои! - ты лишь придумываешь сценарий и концепцию"
main_scenario = generate_text(main_prompt)
main_parts = extract_parts(main_scenario)
"""