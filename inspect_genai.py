
import asyncio
import os
from google import genai

try:
    from src.core.config import Config
    config = Config.load()
    api_key = config.GOOGLE_API_KEY
except Exception as e:
    print(f"Failed to load config: {e}")
    # Fallback
    api_key = os.environ.get("GOOGLE_API_KEY", "DUMMY")

async def inspect():
    print("Initializing client...")
    # Initialize with a dummy key if needed, or real one if available.
    # We just want to inspect the object structure.
    client = genai.Client(api_key=api_key) 
    
    print("Creating async chat...")
    chat = client.aio.chats.create(model="gemini-2.0-flash-exp") # Use a valid model name from recent history or config
    


    with open("results.txt", "w") as f:
        f.write(f"Chat object type: {type(chat)}\n")
        attributes = dir(chat)
        history_attrs = [a for a in attributes if 'history' in a.lower()]
        f.write(f"History related attributes: {history_attrs}\n")

        if hasattr(chat, '_history'):
            f.write(f"Has _history attribute. Type: {type(chat._history)}\n")
            f.write(f"_history content: {chat._history}\n")
        
        if hasattr(chat, 'get_history'):
            f.write("Has get_history method\n")
            try:
                 hist = chat.get_history()
                 f.write(f"get_history returns: {type(hist)}\n")
            except Exception as e:
                 f.write(f"get_history call failed: {e}\n")

if __name__ == "__main__":
    asyncio.run(inspect())
