import asyncio
import io
import os
import sys
import warnings

# Force UTF-8 encoding for stdout and stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# --- [SOTA FIX: ChromaDB & Asyncio Compatibility] ---
try:
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass

# Suppress Warnings
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality.*")

from rich.console import Console  # noqa: E402
from rich.markdown import Markdown  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.prompt import Prompt  # noqa: E402
from rich.live import Live  # noqa: E402

from src.core.agent import ZenithAgent  # noqa: E402
from src.core.config import Config  # noqa: E402
from src.scripts.ingest import run_ingestion  # noqa: E402
from src.utils.bootstrapper import (  # noqa: E402
    check_knowledge_updates,
    save_knowledge_hash,
)
from src.utils.loader import load_system_prompt  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402

# Initialize Console and Logger
console = Console()
logger = setup_logger("ZenithMain")


def print_header():
    """Prints the application header."""
    console.print(
        Panel.fit(
            "[bold cyan]Zenith | Prompt Architect Engine[/bold cyan]\n"
            "[dim]Advanced Autonomous Agent Interface (Async SOTA)[/dim]",
            border_style="cyan",
        )
    )


async def main():
    """Main entry point for the application (Async)."""
    print_header()

    # 1. Load Configuration
    try:
        with console.status("[bold green]Loading configuration...", spinner="dots"):
            config = Config.load()
    except ValueError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        logger.exception("Failed to load configuration")
        sys.exit(1)

    # 1.1. Memory Bootstrapping (Automatic Ingestion)
    # Note: Ingestion is still sync for now as it's a startup task.
    knowledge_dir = "knowledge_base"  # Relative path valid for check
    console.print(
        "[bold blue]🔄 Verificando integridade da Base de Conhecimento...[/bold blue]"
    )

    loop = asyncio.get_running_loop()

    # Offload blocking IO to executor
    try:
        should_update = await loop.run_in_executor(None, check_knowledge_updates, knowledge_dir)
        
        if should_update:
            console.print(
                "[bold yellow]📂 Novos documentos detectados. Atualizando cérebro do Zenith...[/bold yellow]"
            )

            # SOTA Optimization: Event-Driven Cache Invalidation
            bm25_cache = "data/bm25_index.pkl"
            if os.path.exists(bm25_cache):
                try:
                    os.remove(bm25_cache)
                    console.print("[dim]🗑️ Cache BM25 invalidado para reconstrução...[/dim]")
                except Exception as e:
                    logger.warning(f"Failed to clear cache: {e}")
            
            # Run ingestion in executor
            ingestion_success = await loop.run_in_executor(None, run_ingestion)

            if ingestion_success:
                await loop.run_in_executor(None, save_knowledge_hash, knowledge_dir)
                console.print("[bold green]✅ Memória atualizada com sucesso.[/bold green]")
            else:
                console.print(
                    "[bold red]❌ Falha na atualização da memória. Verifique os logs.[/bold red]"
                )
        else:
            console.print("[dim]⚡ Base de conhecimento (RAG) sincronizada.[/dim]")
    except Exception as e:
         logger.error(f"Startup error: {e}")
         console.print(f"[bold red]Startup Verification Failed:[/bold red] {e}")
         # Continue anyway

    # 2. Load System Prompt
    try:
        with console.status("[bold green]Loading system protocols...", spinner="dots"):
            system_instruction = load_system_prompt(config.SYSTEM_PROMPT_PATH)
    except FileNotFoundError as e:
        console.print(f"[bold red]Critical Error:[/bold red] {e}")
        sys.exit(1)

    # 3. Initialize Agent
    try:
        with console.status(
            f"[bold green]Initializing {config.MODEL_NAME}...", spinner="dots"
        ):
            agent = ZenithAgent(config, system_instruction)
            agent.start_chat()
    except Exception as e:
        console.print(f"[bold red]Agent Initialization Failed:[/bold red] {e}")
        logger.exception("Failed to initialize agent")
        sys.exit(1)

    console.print("[bold green][OK] System Online. Ready for input.[/bold green]\n")
    console.print("[dim]Type 'exit' or 'quit' to terminate session.[/dim]\n")

    # 4. Interactive Chat Loop
    while True:
        try:
            # Note: Prompt.ask is synchronous (blocking), but fine for CLI input loop
            user_input = Prompt.ask("[bold cyan]User[/bold cyan]")

            if user_input.lower() in ("exit", "quit"):
                console.print("[yellow]Shutting down Zenith Engine...[/yellow]")
                break

            if not user_input.strip():
                continue

            console.print() # Spacing
            
            # Prepare UI for Streaming
            accumulated_text = ""
            
            with Live(
                Panel("", title="[bold magenta]Zenith Agent (Thinking...)[/bold magenta]", border_style="magenta"),
                refresh_per_second=10,
                auto_refresh=True
            ) as live:
                
                async for chunk in agent.run_analysis_async(user_input):
                    accumulated_text += chunk
                    live.update(
                        Panel(
                            Markdown(accumulated_text),
                            title="[bold magenta]Zenith Agent[/bold magenta]",
                            border_style="magenta",
                        )
                    )

            console.print()  # Empty line for spacing

        except KeyboardInterrupt:
            console.print("\n[yellow]Session interrupted by user.[/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Runtime Error:[/bold red] {e}")
            logger.exception("Runtime error in chat loop")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())
