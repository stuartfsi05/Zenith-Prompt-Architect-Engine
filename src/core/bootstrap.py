import asyncio
import os
import sys
from rich.console import Console

from src.core.config import Config
from src.scripts.ingest import run_ingestion
from src.utils.bootstrapper import check_knowledge_updates, save_knowledge_hash
from src.utils.logger import setup_logger

logger = setup_logger("Bootstrap")
console = Console()


class BootstrapService:
    """
    Service responsible for system initialization, consistency checks,
    and ensuring the environment is ready for the agent.
    """

    @staticmethod
    async def initialize(config: Config) -> bool:
        """
        Runs all initialization steps.
        Returns True if successful, False otherwise.
        """
        try:
            # 1. Verify Directories
            BootstrapService._verify_paths(config)

            # 2. Check Knowledge Base
            await BootstrapService._ensure_knowledge_consistency(config)

            return True

        except Exception as e:
            logger.critical(f"Initialization Failed: {e}")
            console.print(f"[bold red]Critical Startup Error:[/bold red] {e}")
            return False

    @staticmethod
    def _verify_paths(config: Config):
        """Ensures essential directories exist."""
        required_paths = [
            config.DATA_DIR,
            config.KNOWLEDGE_DIR,
            os.path.dirname(config.SYSTEM_PROMPT_PATH)
        ]

        for path in required_paths:
            if not os.path.exists(path):
                logger.info(f"Creating missing directory: {path}")
                os.makedirs(path, exist_ok=True)

        if not os.path.exists(config.SYSTEM_PROMPT_PATH):
            logger.warning(f"System prompt not found at {config.SYSTEM_PROMPT_PATH}")
            # We don't raise here to allow later graceful failure or default fallback

    @staticmethod
    async def _ensure_knowledge_consistency(config: Config):
        """
        Checks if knowledge ingestion is required and runs it.
        """
        console.print("[bold blue]🔄 Verifying Knowledge Base Integrity...[/bold blue]")

        loop = asyncio.get_running_loop()
        should_update = await loop.run_in_executor(
            None, check_knowledge_updates, config.KNOWLEDGE_DIR
        )

        if should_update:
            console.print("[bold yellow]📂 New documents detected. Updating Zenith Brain...[/bold yellow]")

            # Invalidate Cache
            if os.path.exists(config.BM25_CACHE_PATH):
                try:
                    os.remove(config.BM25_CACHE_PATH)
                    logger.info("BM25 cache invalidated.")
                except Exception as e:
                    logger.warning(f"Failed to clear cache: {e}")

            # Run Ingestion (Sync function run in executor)
            ingestion_success = await loop.run_in_executor(None, run_ingestion)

            if ingestion_success:
                await loop.run_in_executor(
                    None, save_knowledge_hash, config.KNOWLEDGE_DIR
                )
                console.print("[bold green]✅ Memory updated successfully.[/bold green]")
            else:
                console.print("[bold red]❌ Update failed. Check logs.[/bold red]")
                raise RuntimeError("Knowledge Ingestion Failed")
        else:
            console.print("[dim]⚡ Knowledge Base synchronized.[/dim]")
