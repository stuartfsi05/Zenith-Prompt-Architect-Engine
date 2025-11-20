import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.layout import Layout
from rich.live import Live

from src.core.config import Config
from src.core.agent import ZenithAgent
from src.utils.loader import load_system_prompt
from src.utils.logger import setup_logger

# Initialize Console and Logger
console = Console()
logger = setup_logger("ZenithMain")

def print_header():
    """Prints the application header."""
    console.print(Panel.fit(
        "[bold cyan]Zenith | Prompt Architect Engine[/bold cyan]\n"
        "[dim]Advanced Autonomous Agent Interface[/dim]",
        border_style="cyan"
    ))

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

    # 2. Load System Prompt
    try:
        with console.status("[bold green]Loading system protocols...", spinner="dots"):
            system_instruction = load_system_prompt(config.SYSTEM_PROMPT_PATH)
    except FileNotFoundError as e:
        console.print(f"[bold red]Critical Error:[/bold red] {e}")
        sys.exit(1)

    # 3. Initialize Agent
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

    # 4. Interactive Chat Loop
    while True:
        try:
            user_input = Prompt.ask("[bold cyan]User[/bold cyan]")
            
            if user_input.lower() in ('exit', 'quit'):
                console.print("[yellow]Shutting down Zenith Engine...[/yellow]")
                break
            
            if not user_input.strip():
                continue

            with console.status("[bold cyan]Analyzing...[/bold cyan]", spinner="aesthetic"):
                response = agent.run_analysis(user_input)

            console.print(Panel(
                Markdown(response),
                title="[bold magenta]Zenith Agent[/bold magenta]",
                border_style="magenta",
                expand=False
            ))
            console.print() # Empty line for spacing

        except KeyboardInterrupt:
            console.print("\n[yellow]Session interrupted by user.[/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Runtime Error:[/bold red] {e}")
            logger.exception("Runtime error in chat loop")

if __name__ == "__main__":
    main()
