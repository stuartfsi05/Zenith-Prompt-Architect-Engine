import asyncio
import io
import logging
import sys
import warnings
from typing import NoReturn

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

# Force UTF-8 encoding for stdout and stderr to handle emojis and special chars on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Suppress noisy warnings from third-party libraries
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

from src.api.dependencies import (
    get_analyzer,
    get_context_builder,
    get_db,
    get_judge,
    get_knowledge_base,
    get_llm,
    get_memory,
    get_validator,
)
from src.core.agent import ZenithAgent
from src.core.bootstrap import BootstrapService
from src.core.config import Config
from src.utils.loader import load_system_prompt
from src.utils.logger import setup_logger

# Initialize global UI and logging components
console = Console()
logger = setup_logger("ZenithMain")


def print_header() -> None:
    """
    Displays the application's visual header in the console.
    """
    console.print(
        Panel.fit(
            "[bold cyan]Zenith | Prompt Architect Engine[/bold cyan]\n"
            "[dim]Advanced Autonomous Agent Interface[/dim]",
            border_style="cyan",
        )
    )


async def main() -> None:
    """
    Orchestrates the application lifecycle: config loading, bootstrapping,
    agent initialization, and the interactive command-line loop.
    """
    print_header()

    # 1. Load Configuration (Pydantic Settings)
    try:
        config = Config()
    except Exception as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        sys.exit(1)

    # 2. Bootstrap System Environment
    # Verifies directories, knowledge base consistency, and essential resources.
    if not await BootstrapService.initialize(config):
        console.print("[bold red]System Initialization Failed. Exiting.[/bold red]")
        sys.exit(1)

    # 3. Load System Core Instructions
    try:
        system_instruction = load_system_prompt(config.SYSTEM_PROMPT_PATH)
    except FileNotFoundError as e:
        console.print(f"[bold red]Critical Error (Prompt Missing):[/bold red] {e}")
        sys.exit(1)

    # 4. Initialize Zenith Agent via Dependency Injection
    try:
        with console.status(
            f"[bold green]Initializing {config.MODEL_NAME}...", spinner="dots"
        ):
            # Resolve singleton dependencies
            db = get_db(config)
            llm = get_llm(config)
            knowledge_base = get_knowledge_base(config)
            context_builder = get_context_builder()
            analyzer = get_analyzer(config)
            judge = get_judge(config)
            memory = get_memory(config)
            validator = get_validator()

            agent = ZenithAgent(
                config=config,
                system_instruction=system_instruction,
                db=db,
                llm=llm,
                knowledge_base=knowledge_base,
                context_builder=context_builder,
                analyzer=analyzer,
                judge=judge,
                memory=memory,
                validator=validator,
            )

            # Initialize the default CLI chat session
            agent.start_chat(session_id="cli_session", user_id="cli_user")

    except Exception as e:
        console.print(f"[bold red]Agent Initialization Failed:[/bold red] {e}")
        logger.exception("Failed to initialize ZenithAgent")
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

            console.print()  # Spacer
            accumulated_text = ""

            # Use Live display for real-time markdown streaming
            with Live(
                Panel(
                    "",
                    title="[bold magenta]Zenith Agent (Thinking...)[/bold magenta]",
                    border_style="magenta",
                ),
                refresh_per_second=10,
                auto_refresh=True,
            ) as live:
                async for chunk in agent.run_analysis_async(
                    user_input=user_input,
                    session_id="cli_session",
                    user_id="cli_user",
                ):
                    accumulated_text += chunk
                    live.update(
                        Panel(
                            Markdown(accumulated_text),
                            title="[bold magenta]Zenith Agent[/bold magenta]",
                            border_style="magenta",
                        )
                    )
            console.print()  # Final spacer

        except KeyboardInterrupt:
            console.print("\n[yellow]Session interrupted by user.[/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Runtime Error:[/bold red] {e}")
            logger.exception("Runtime error encountered in chat loop")


if __name__ == "__main__":
    # Performance optimization for Windows event loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

