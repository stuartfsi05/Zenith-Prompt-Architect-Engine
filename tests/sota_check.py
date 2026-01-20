import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))
sys.path.append(os.getcwd())

from src.core.agent import ZenithAgent
from src.core.config import Config


def verify_sota():
    print("🚀 Verifying SOTA Architecture...")

    try:
        # 1. Load Config
        print("1. Loading Config...")
        config = Config.load()
        if not config.GOOGLE_API_KEY:
            raise ValueError("Missing GOOGLE_API_KEY")
        print("✅ Config Loaded.")

        # 2. Instantiate Agent (Triggers Validator, Analyzer, Judge, Knowledge)
        print("2. Instantiating ZenithAgent (SOTA)...")
        # Use a dummy system instruction
        agent = ZenithAgent(config, "You are Zenith.")
        print("✅ ZenithAgent Instantiated.")

        # 3. Check Sub-modules
        if not agent.analyzer:
            raise ValueError("Analyzer missing")
        if not agent.validator:
            raise ValueError("Validator missing")
        if not agent.judge:
            raise ValueError("Judge missing")
        if not agent.knowledge_base:
            raise ValueError("KnowledgeBase missing")
        if not agent.main_session:
            raise ValueError("Main Session missing")
        print("✅ All SOTA Sub-modules initialized.")

        print("🎉 SOTA Verification Passed: Architecture is sound.")
        return True

    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        return False


if __name__ == "__main__":
    verify_sota()
