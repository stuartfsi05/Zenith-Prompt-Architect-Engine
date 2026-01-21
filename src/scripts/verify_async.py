import asyncio
import os
import sys

# Ensure src is in path
sys.path.append(os.getcwd())

from src.core.agent import ZenithAgent
from src.core.config import Config

async def main():
    print("--- Zenith Async Verification ---")
    
    # Mock Config or Load
    try:
        config = Config.load()
    except Exception as e:
        print(f"Failed to load config: {e}")
        return

    # Mock System Prompt
    system_instruction = "You are Zenith, a test agent."

    print("Initializing Agent...")
    agent = ZenithAgent(config, system_instruction)
    
    print("Sending Async Request: 'Hello Zenith'")
    
    chunk_count = 0
    full_response = ""
    
    try:
        async for chunk in agent.run_analysis_async("Hello Zenith"):
            print(f"[Stream Chunk]: {chunk}", end="", flush=True)
            full_response += chunk
            chunk_count += 1
            
        print("\n\n--- Verification Results ---")
        print(f"Total Chunks: {chunk_count}")
        print(f"Full Response Length: {len(full_response)}")
        
        if chunk_count > 0:
            print("✅ Streaming Verified")
        else:
            print("❌ No chunks received")
            
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
