# utils/openai_api.py

import openai
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

def generate_response(prompt):
    # response = openai.ChatCompletion.create(
    #     model="gpt-3.5-turbo",
    #     messages=[{"role": "user", "content": prompt}]
    # )
    response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            )
    return response.choices[0].message['content']