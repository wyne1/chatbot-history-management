import google.generativeai as genai
from config import GEMINI_API_KEY

def call_gemini(prompt_text, temperature=0.7):
    genai.configure(api_key=GEMINI_API_KEY)
    model_name = "gemini-pro"
    # Start a chat session with the Gemini model
    model = genai.GenerativeModel(model_name)
    chat_session = model.start_chat()
    # Send the message to the model
    response = chat_session.send_message(prompt_text)
    # Parse the response
    result_text = response.text
    return {'role': 'assistant', 'content': result_text}