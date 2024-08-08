from openai import OpenAI
from io import BytesIO
import base64
from PIL import Image
from keys import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_text(txt, system_txt=None, model="gpt-4o-mini"):
    messages = []
    if system_txt:
        messages.append({"role": "system", "content": system_txt})
    messages.append({"role": "user", "content": txt})
    completion = client.chat.completions.create(
        model=model,
        messages=messages
    )
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
