# # conversation_handler.py

# from utils.openai_api import generate_response
# from utils.gemini_api import call_gemini
# from utils.token_counter import count_tokens

# def handle_user_message(chat_manager, user_id, message_text):
#     # Fetch chat history
#     history = chat_manager.get_chat_history(user_id)

#     # Prepare the conversation history in the required format
#     conversation_history = ""
#     for item in history:
#         if 'content' in item:
#             if isinstance(item['content'], dict):
#                 role = item['content'].get('role', 'assistant')
#                 content = item['content'].get('content', '')
#             else:
#                 role = 'assistant'
#                 content = item['content']
#             conversation_history += f"{role}: {content}\n"

#     # Create prompt for OpenAI
#     prompt = f"Given the following conversation history, continue the conversation appropriately.\n\n{conversation_history}\nUser: {message_text}\nAssistant:"

#     # Count tokens
#     token_count = count_tokens(prompt)

#     # Generate response from OpenAI
#     response_text = call_gemini(prompt)['content']

#     # Store messages
#     user_message = {"role": "user", "content": message_text}
#     assistant_message = {"role": "assistant", "content": response_text}

#     chat_manager.handle_new_message(user_id, user_message)
#     chat_manager.handle_new_message(user_id, assistant_message)


#     print(f"Gemini Response: {response_text}")
#     return response_text, token_count


# conversation_handler.py

from utils.gemini_api import call_gemini
from utils.token_counter import count_tokens
import json

def handle_user_message(chat_manager, user_id, message_text):
    # Fetch chat history
    history = chat_manager.get_chat_history(user_id)

    # Prepare the conversation history
    conversation_history = ""
    for item in history:
        if 'content' in item:
            if isinstance(item['content'], dict):
                role = item['content'].get('role', 'assistant')
                content = item['content'].get('content', '')
            else:
                role = 'assistant'
                content = item['content']
            conversation_history += f"{role}: {content}\n"

    # Update the prompt
    prompt = f"Given the following conversation history, continue the conversation appropriately. Do not include any JSON formatting in your response.\n\n{conversation_history}\nUser: {message_text}\nAssistant:"

    # Count tokens
    token_count = count_tokens(prompt)

    # Generate response
    response = call_gemini(prompt)
    response_text_json = response['content']

    # Parse the nested JSON
    try:
        response_content = json.loads(response_text_json)
        response_text = response_content.get('content', response_text_json)
    except json.JSONDecodeError:
        response_text = response_text_json

    # Store messages
    user_message = {"role": "user", "content": message_text}
    assistant_message = {"role": "assistant", "content": response_text}

    chat_manager.handle_new_message(user_id, user_message)
    chat_manager.handle_new_message(user_id, assistant_message)

    print(response_text)
    return response_text, token_count