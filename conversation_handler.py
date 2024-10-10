from utils.gemini_api import call_gemini
from utils.token_counter import count_tokens

def handle_user_message(chat_manager, user_id, message_text):
    # Add the user's message to the context
    chat_manager.handle_new_message(user_id, {"role": "user", "content": message_text})

    # Get the current context
    context = chat_manager.get_context(user_id)

    # Prepare the prompt for Gemini
    prompt = f"Context: {context}\n\nUser: {message_text}\n\nAssistant:"

    # Call Gemini API
    response = call_gemini(prompt)

    # Add the assistant's response to the context
    chat_manager.handle_new_message(user_id, {"role": "assistant", "content": response['content']})

    # Count tokens
    token_count = count_tokens(prompt + response['content'])

    return response['content'], token_count