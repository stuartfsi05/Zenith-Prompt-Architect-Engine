import asyncio
import os
import sys

# Ensure src is in path
sys.path.append(os.getcwd())

from src.core.agent import ZenithAgent
from src.core.config import Config
from src.core.database import DatabaseManager

async def main():
    print("--- Zenith Database Persistence Verification ---")
    
    # Mock Config
    try:
        config = Config.load()
    except Exception as e:
        print(f"Failed to load config: {e}")
        return

    TEST_SESSION_ID = "test_verification_session"
    
    # 1. First Run: Create Session & Log Interaction
    print(f"\nPhase 1: Running Agent (Session: {TEST_SESSION_ID})...")
    agent = ZenithAgent(config, system_instruction="You are a test agent.")
    
    # Manually override session id for this test
    agent.current_session_id = TEST_SESSION_ID
    agent.db.create_session(TEST_SESSION_ID)
    
    user_input = "Remember this: The key code is 12345."
    print(f"User: {user_input}")
    
    response_text = ""
    async for chunk in agent.run_analysis_async(user_input):
        response_text += chunk
        
    print(f"Agent: {response_text[:50]}...")

    # 2. Verify Database Content directly
    print("\nPhase 2: Inspecting Database...")
    db = DatabaseManager(config)
    history = db.get_history(TEST_SESSION_ID)
    
    if len(history) >= 2: # At least User + Model
        print(f"✅ History found in DB: {len(history)} items.")
        print(f"Last Item Role: {history[-1]['role']}")
        # print metadata
        last_meta = history[-1]['metadata']
        print(f"Metadata (Score): {last_meta.get('score')}")
    else:
        print(f"❌ History NOT found or incomplete. Count: {len(history)}")
        return

    # 3. Second Run: Restore Session
    print("\nPhase 3: Restoring Session (New Agent Instance)...")
    agent_restored = ZenithAgent(config, system_instruction="You are a test agent.")
    agent_restored.start_chat(TEST_SESSION_ID)
    
    # Verify History in GenAI Session
    # Note: Accessing internal history for verification
    loaded_history = agent_restored.main_session.history
    if len(loaded_history) >= 2:
        print(f"✅ GenAI Session History Restored. Items: {len(loaded_history)}")
        print(f"First User Message: {loaded_history[0].parts[0].text}")
        if "12345" in loaded_history[0].parts[0].text:
             print("✅ Content Match Confirmed.")
    else:
        print("❌ GenAI Session History is empty.")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
