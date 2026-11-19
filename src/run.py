import os
import sys

import uvicorn

# Ensure project root is in pythonpath
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("ZENITH_RELOAD", "false").lower() == "true"
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=port, reload=reload_enabled)
