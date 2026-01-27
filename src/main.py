import asyncio
import io
import sys
import warnings

# Force UTF-8 encoding for stdout and stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Suppress Warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")
warnings.filterwarnings("ignore", message=".*Core Pydantic V1 functionality.*")

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from src.core.agent import ZenithAgent
from src.core.bootstrap import BootstrapService
from src.core.config import Config
from src.utils.loader import load_system_prompt
from src.utils.logger import setup_logger

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


async def main():
    """Main entry point."""
    print_header()

    # 1. Load Configuration
    try:
        config = Config.load()
    except Exception as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        sys.exit(1)

    # 2. Bootstrap System
    if not await BootstrapService.initialize(config):
        console.print("[bold red]System Initialization Failed. Exiting.[/bold red]")
        sys.exit(1)

    # 3. Load System Prompt
    try:
        system_instruction = load_system_prompt(config.SYSTEM_PROMPT_PATH)
    except FileNotFoundError as e:
        console.print(f"[bold red]Critical Error:[/bold red] {e}")
        sys.exit(1)

    # 4. Initialize Agent
    try:
        with console.status(f"[bold green]Initializing {config.MODEL_NAME}...", spinner="dots"):
            agent = ZenithAgent(config, system_instruction)
            agent.start_chat()
    except Exception as e:
        console.print(f"[bold red]Agent Initialization Failed:[/bold red] {e}")
        logger.exception("Failed to initialize agent")
        sys.exit(1)

    console.print("[bold green][OK] System Online. Ready for input.[/bold green]\n")
    console.print("[dim]Type 'exit' or 'quit' to terminate session.[/dim]\n")

    # 5. Interactive Chat Loop
    while True:
        try:
            user_input = Prompt.ask("[bold cyan]User[/bold cyan]")

            if user_input.lower() in ("exit", "quit"):
                console.print("[yellow]Shutting down Zenith Engine...[/yellow]")
                break

            if not user_input.strip():
                continue

            console.print()
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
            console.print()

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
