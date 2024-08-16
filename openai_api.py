from openai import OpenAI
from io import BytesIO
import base64
from PIL import Image
from secret_data import OPENAI_API_KEY
import json
import uuid
import openai
import os

client = OpenAI(api_key=OPENAI_API_KEY)
if os.path.exists("tokens_used"):
    tokens_used = json.load(open("tokens_used"))
else:
    tokens_used = {}

def generate_text(txt, system_txt=None, model="gpt-4o-mini", max_tokens=None):
    global tokens_used
    messages = []
    if system_txt:
        messages.append({"role": "system", "content": system_txt})
    messages.append({"role": "user", "content": txt})
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens
    )
    
    if model not in tokens_used:
        tokens_used[model] = 0
    tokens_used[model] += completion.usage.total_tokens
    with open("tokens_used", "w") as f:
        json.dump(tokens_used, f)

    message = completion.choices[0].message.content
    return message

def generate_text_by_msgs(messages, model="gpt-4o-mini", max_tokens=None):
    global tokens_used
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens
    )
    
    if model not in tokens_used:
        tokens_used[model] = 0
    tokens_used[model] += completion.usage.total_tokens
    with open("tokens_used", "w") as f:
        json.dump(tokens_used, f)

    message = completion.choices[0].message.content
    return message

def generate_image(txt, model="dall-e-3", res="256x256", outformat="b64"):
    """format: b64/img (img=PIL.Image)"""
    engcount = sum([el in "qwertyuiopoasdfghjklzxcvbnm" for el in txt])
    ruscount = sum([el in "йцукенгшщзхъфывапролджэячсмитьбю" for el in txt])
    if ruscount > engcount and model == "dall-e-2":
        prompt = "Переведи следующий текст на английский:\n" + txt
        txt = generate_text(prompt)
    sz = "1024x1024" if model != "dall-e-2" else "256x256"
    try:
        response = client.images.generate(
            model=model,
            prompt=txt,
            quality="standard",
            size=sz,
            n=1,
            response_format="b64_json"
        )
        b64 = response.data[0].b64_json
    except openai.BadRequestError:
        img = Image.open("media/safety.png")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        b64 = base64.b64encode(buffered.getvalue()).decode('ascii')
    
    if model not in tokens_used:
        tokens_used[model] = 0
    tokens_used[model] += 1
    with open("tokens_used", "w") as f:
        json.dump(tokens_used, f)

    if sz != res:
        img = Image.open(BytesIO(base64.b64decode(b64)))
        img.thumbnail(tuple(map(int, res.split("x"))), Image.ANTIALIAS)
        if outformat == "b64":
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('ascii')
            return img_str
        return img

    if outformat == "b64":
        return b64
    img = Image.open(BytesIO(base64.b64decode(b64)))
    return img

def generate_image_with_url(*args, prefolder="", outsize=None, **kwargs):
    img_name = f"{uuid.uuid4()}.png"
    img = generate_image(*args, outformat="img", **kwargs)
    if outsize is not None:
        img.thumbnail(outsize, Image.ANTIALIAS)
    
    img.save(f"media/{prefolder}/{img_name}")
    return f"{prefolder}/" + img_name
