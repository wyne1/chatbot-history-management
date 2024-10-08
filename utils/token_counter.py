import tiktoken

def count_tokens(text, model_name='gpt-3.5-turbo'):
    encoding = tiktoken.encoding_for_model(model_name)
    num_tokens = len(encoding.encode(text))
    return num_tokens