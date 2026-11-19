import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.dependencies import get_config, initialize_global_agent
from src.api.routes import router
from src.core.bootstrap import BootstrapService
from src.utils.logger import setup_logger

# Setup Logger
logger = setup_logger("ZenithServer")


def _resolve_allowed_origins() -> list[str]:
    """Resolves allowed CORS origins from Config or environment safely."""
    try:
        return get_config().allowed_origins_list
    except Exception:
        raw = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://localhost:3000,"
            "https://zenith-interface-ten.vercel.app",
        )
        return [
            origin.strip().rstrip("/")
            for origin in raw.split(",")
            if origin.strip().rstrip("/")
        ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Zenith API Server...")
    config = get_config()

    # Bootstrap checks
    if not await BootstrapService.initialize(config):
        logger.critical("Bootstrap failed. Server functionality may be limited.")

    # Initialize Agent
    await initialize_global_agent()

    yield

    # Shutdown
    logger.info("Shutting down Zenith API Server...")


app = FastAPI(
    title="Zenith API",
    description="Headless API for Zenith Prompt Architect Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=_resolve_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "x-google-api-key"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)
