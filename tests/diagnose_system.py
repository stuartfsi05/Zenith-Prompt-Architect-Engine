import asyncio
import os
import sys
import logging

sys.path.append(os.getcwd())

from src.core.config import Config
from src.core.database import SupabaseRepository
from src.core.llm.google_genai import GoogleGenAIProvider

# Setup simple logger
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("Diagnosis")

async def diagnose():
    print("🩺 Starting System Diagnosis...")
    errors = []

    # 1. Config Check
    try:
        config = Config.load()
        print("✅ Configuration Loaded.")
    except Exception as e:
        print(f"❌ Config Load Failed: {e}")
        return

    # 2. Database Connectivity
    try:
        db = SupabaseRepository(config)
        # Try a simple read
        db.get_analytics_summary()
        print("✅ Supabase Connection: OK")
    except Exception as e:
        logger.error(f"Supabase Connection Failed: {e}")
        errors.append(f"Supabase Error: {e}")

    # 3. LLM Connectivity
    try:
        llm = GoogleGenAIProvider(
            model_name=config.MODEL_NAME,
            temperature=0.1
        )
        llm.configure(config.GOOGLE_API_KEY)
        
        print(f"Testing Gemini Model: {config.MODEL_NAME}...")
        # Simple generation
        response = await llm.generate_content_async("Ping. Reply with 'Pong'.")
        if "pong" in response.lower():
            print(f"✅ Gemini API: OK (Response: {response})")
        else:
             print(f"⚠️ Gemini API: Connected but unexpected response: {response}")
        
    except Exception as e:
        logger.error(f"Gemini API Failed: {e}")
        errors.append(f"Gemini API Error: {e}")

    if errors:
        print(f"\n❌ Diagnosis Found {len(errors)} Issues.")
        sys.exit(1)
    else:
        print("\n✨ System Healthy. Ready to Start.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(diagnose())
