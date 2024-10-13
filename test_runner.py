import importlib.util
import sys
from chat_manager import ChatManager
from utils.token_counter import count_tokens
import logging

logger = logging.getLogger(__name__)

def load_conversation(file_path):
    logger.info(f"Loading conversation from file: {file_path}")
    spec = importlib.util.spec_from_file_location("sample_conversation", file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sample_conversation"] = module
    spec.loader.exec_module(module)
    logger.info(f"Loaded conversation with {len(module.conversation)} messages")
    return module.conversation

# def run_test(file_path):
#     conversation = load_conversation(file_path)
#     chat_manager = ChatManager()
#     approaches = chat_manager.approaches.keys()
#     results = {approach: [] for approach in approaches}

#     for approach in approaches:
#         logger.info(f"Running test for approach: {approach}")
#         chat_manager.set_approach(approach)
#         cumulative_tokens = 0
#         try:
#             for i, message in enumerate(conversation):
#                 user_id = f"user_{approach}"
#                 if message['role'] == 'user':
#                     context = chat_manager.get_context(user_id)
#                     prompt = f"Context: {context}\n\nUser: {message['content']}\n\nAssistant:"
#                     tokens = count_tokens(prompt)
#                     cumulative_tokens += tokens
#                     results[approach].append((i + 1, cumulative_tokens))
#                     logger.info(f"Approach: {approach}, Message: {i+1}, Cumulative Tokens: {cumulative_tokens}")
#                 chat_manager.handle_new_message(user_id, message)
#         except Exception as e:
#             logger.error(f"Error in approach {approach}: {str(e)}")
#             results[approach] = [(-1, -1)]  # Indicate error for this approach

#     logger.info("Test completed for all approaches")
#     return results



def run_test(file_path):
    conversation = load_conversation(file_path)
    chat_manager = ChatManager()
    approaches = chat_manager.approaches.keys()
    results = {approach: [] for approach in approaches}

    for approach in approaches:
        logger.info(f"Running test for approach: {approach}")
        chat_manager.set_approach(approach)
        cumulative_tokens = 0
        try:
            for i, message in enumerate(conversation):
                user_id = f"user_{approach}"
                if message['role'] == 'user':
                    context = chat_manager.get_context(user_id)
                    
                    # All approaches now return a string context
                    context_str = str(context)
                    
                    prompt = f"Context: {context_str}\n\nUser: {message['content']}\n\nAssistant:"
                    print(f"{i}: {prompt}")
                    tokens = count_tokens(prompt)
                    # cumulative_tokens += tokens
                    cumulative_tokens = tokens
                    results[approach].append((i + 1, cumulative_tokens))
                    logger.info(f"Approach: {approach}, Message: {i+1}, Cumulative Tokens: {cumulative_tokens}")
                chat_manager.handle_new_message(user_id, message)
        except Exception as e:
            logger.error(f"Error in approach {approach}: {str(e)}")
            results[approach] = [(-1, -1)]  # Indicate error for this approach

    logger.info("Test completed for all approaches")
    return results

