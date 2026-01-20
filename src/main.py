import sys
import io
import os

import warnings

# Force UTF-8 encoding for stdout and stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Suppress Pydantic V1/Python 3.14 compatibility warnings
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality.*")

from rich.console import Console  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.markdown import Markdown  # noqa: E402
from rich.prompt import Prompt  # noqa: E402

from src.core.config import Config  # noqa: E402
from src.core.agent import ZenithAgent  # noqa: E402
from src.utils.loader import load_system_prompt  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402
from src.scripts.ingest import run_ingestion  # noqa: E402
from src.utils.bootstrapper import (  # noqa: E402
    check_knowledge_updates,
    save_knowledge_hash,
)

# Initialize Console and Logger
console = Console()
logger = setup_logger("ZenithMain")


def print_header():
    """Prints the application header."""
    console.print(
        Panel.fit(
            "[bold cyan]Zenith | Prompt Architect Engine[/bold cyan]\n"
            "[dim]Advanced Autonomous Agent Interface[/dim]",
            border_style="cyan",
        )
    )


def main():
    """Main entry point for the application."""
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
    knowledge_dir = "knowledge_base"  # Relative path valid for check
    console.print(
        "[bold blue]🔄 Verificando integridade da Base de Conhecimento...[/bold blue]"
    )

    if check_knowledge_updates(knowledge_dir):
        console.print(
            "[bold yellow]📂 Novos documentos detectados. Atualizando cérebro do Zenith...[/bold yellow]"
        )

        # SOTA Optimization: Event-Driven Cache Invalidation
        # Force cache deletion to prevent "Zero Blindness"
        bm25_cache = "data/bm25_index.pkl"
        if os.path.exists(bm25_cache):
            try:
                os.remove(bm25_cache)
                console.print("[dim]🗑️ Cache BM25 invalidado para reconstrução...[/dim]")
            except Exception as e:
                logger.warning(f"Failed to clear cache: {e}")

        if run_ingestion():
            save_knowledge_hash(knowledge_dir)
            console.print("[bold green]✅ Memória atualizada com sucesso.[/bold green]")
        else:
            console.print(
                "[bold red]❌ Falha na atualização da memória. Verifique os logs.[/bold red]"
            )
    else:
        console.print("[dim]⚡ Base de conhecimento (RAG) sincronizada.[/dim]")

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
            user_input = Prompt.ask("[bold cyan]User[/bold cyan]")

            if user_input.lower() in ("exit", "quit"):
                console.print("[yellow]Shutting down Zenith Engine...[/yellow]")
                break

            if not user_input.strip():
                continue

            with console.status(
                "[bold cyan]Analyzing...[/bold cyan]", spinner="aesthetic"
            ):
                response = agent.run_analysis(user_input)

            console.print(
                Panel(
                    Markdown(response),
                    title="[bold magenta]Zenith Agent[/bold magenta]",
                    border_style="magenta",
                    expand=False,
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
    main()
