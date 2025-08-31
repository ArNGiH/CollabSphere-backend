from openai import OpenAI
import os

# Initialize once at import
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def get_ai_reply(user_message: str, history: list[dict] = None) -> str:
    """
    Generate an AI reply using OpenAI with optional conversation history.

    :param user_message: The latest user input (string)
    :param history: A list of dicts like [{"role": "user"|"assistant", "content": "..."}]
    :return: AI's reply as string
    """

    # System instruction (defines AI’s behavior)
    system_prompt = {
        "role": "system",
        "content": (
            "You are an AI work assistant. "
            "Only answer questions related to work, "
            "such as company tasks, coding, or productivity. "
            "If asked about non-work topics, politely refuse."
        )
    }

    
    messages = [system_prompt]
    if history:
        messages.extend(history) 
    messages.append({"role": "user", "content": user_message})

    
    completion = client.chat.completions.create(
        model="gpt-4o-mini",  
        messages=messages,
    )

    return completion.choices[0].message.content
