from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.api.routes import router
from src.api.dependencies import initialize_global_agent, get_config
from src.core.bootstrap import BootstrapService
from src.utils.logger import setup_logger
import logging

# Setup Logger
logger = setup_logger("ZenithServer")

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
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now (dev mode)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=True)
