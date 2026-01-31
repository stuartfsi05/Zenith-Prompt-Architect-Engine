import sys
import os

sys.path.append(os.getcwd())

print("🔍 Debugging Imports...")

modules_to_test = [
    "src.core.config",
    "src.core.database",
    "src.core.services.auth",
    "src.core.services.usage",
    "src.core.services.history",
    "src.core.agent",
    "src.api.dependencies",
    "src.main"
]

failed = []

for module in modules_to_test:
    try:
        __import__(module)
        print(f"✅ Imported: {module}")
    except Exception as e:
        print(f"❌ Failed to import {module}: {e}")
        failed.append(module)

if failed:
    print(f"\n⚠️ Verification Failed for {len(failed)} modules.")
    sys.exit(1)
else:
    print("\n✨ All Core Modules Imported Successfully.")
    sys.exit(0)
