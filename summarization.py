from utils.gemini_api import call_gemini

def summarize_chat_history(messages):
    summarize_prompt = """
    Given a history of chat messages, summarize the conversation between user and AI into one paragraph of not more than 250 words.
    Summarize all user messages into one paragraph and all AI messages into another paragraph.
    User: 
    AI: 

    Message history:
    {conversation}

    Instructions:

    Summary:
    """
    # Combine all messages into a single string
    summary = " ".join([str(msg) for msg in messages])
    # Generate the prompt for summarization
    prompt = summarize_prompt.format(conversation=summary)
    # Call the Gemini model to generate the summary
    response = call_gemini(prompt, temperature=0.7)
    return response['content']