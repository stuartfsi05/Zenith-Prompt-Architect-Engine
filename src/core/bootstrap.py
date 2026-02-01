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
            os.path.dirname(config.SYSTEM_PROMPT_PATH),
        ]

        for path in required_paths:
            if not os.path.exists(path):
                logger.info(f"Creating missing directory: {path}")
                os.makedirs(path, exist_ok=True)

        if not os.path.exists(config.SYSTEM_PROMPT_PATH):
            logger.info(f"System prompt not found. Attempting to create from sample...")
            
            if os.path.exists(config.SAMPLE_SYSTEM_PROMPT_PATH):
                import shutil
                try:
                     shutil.copy(config.SAMPLE_SYSTEM_PROMPT_PATH, config.SYSTEM_PROMPT_PATH)
                     console.print(f"[bold green]✅ System Prompt created from sample: {config.SYSTEM_PROMPT_PATH}[/bold green]")
                except Exception as e:
                     logger.error(f"Failed to copy sample prompt: {e}")
                     console.print(f"[bold red]❌ Failed to create system prompt: {e}[/bold red]")
            else:
                logger.warning(f"Sample prompt not found at {config.SAMPLE_SYSTEM_PROMPT_PATH}")
                console.print(f"[bold yellow]⚠️ System Prompt and Sample missing. Agent requires instructions.[/bold yellow]")

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
            console.print(
                "[bold yellow]📂 New documents detected. Updating Zenith Brain...[/bold yellow]"
            )

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
                console.print(
                    "[bold green]✅ Memory updated successfully.[/bold green]"
                )
            else:
                console.print("[bold yellow]⚠️ Atenção: Zenith operando sem memória atualizada devido a erro na API.[/bold yellow]")
                logger.warning("Graceful Degradation: Knowledge Ingestion failed. System starting with stale/empty memory.")
                # We do NOT raise RuntimeError here. We allow the system to start.
                return
        else:
            console.print("[dim]⚡ Knowledge Base synchronized.[/dim]")
