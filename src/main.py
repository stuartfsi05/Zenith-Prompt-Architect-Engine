import asyncio
import io
import sys
import warnings

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

from src.api.dependencies import (  # noqa: E402
    create_cli_llm,
    get_analyzer,
    get_context_builder,
    get_db,
    get_judge,
    get_knowledge_base,
    get_memory,
    get_validator,
)
from src.core.agent import ZenithAgent  # noqa: E402
from src.core.bootstrap import BootstrapService  # noqa: E402
from src.core.config import Config  # noqa: E402
from src.utils.loader import load_system_prompt  # noqa: E402
from src.utils.logger import setup_logger  # noqa: E402

console = Console()
logger = setup_logger("ZenithMain")


def print_header() -> None:
    """Displays the application's visual header in the console."""
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

    try:
        config = Config()
    except Exception as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        sys.exit(1)

    if not await BootstrapService.initialize(config):
        console.print("[bold red]System Initialization Failed. Exiting.[/bold red]")
        sys.exit(1)

    try:
        system_instruction = load_system_prompt(str(config.SYSTEM_PROMPT_PATH))
    except FileNotFoundError as e:
        console.print(f"[bold red]Critical Error (Prompt Missing):[/bold red] {e}")
        sys.exit(1)

    try:
        with console.status(
            f"[bold green]Initializing {config.MODEL_NAME} (aux: {config.AUX_MODEL_NAME})...",
            spinner="dots",
        ):
            db = get_db(config)
            llm = create_cli_llm(config)
            knowledge_base = get_knowledge_base(config)
            context_builder = get_context_builder()
            analyzer = get_analyzer(config)
            judge = get_judge(config)
            memory = get_memory(config, db)
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
                active_model_name=config.MODEL_NAME,
                mode="byok",
            )

            agent.start_chat(session_id="cli_session", user_id="cli_user")

    except Exception as e:
        console.print(f"[bold red]Agent Initialization Failed:[/bold red] {e}")
        logger.exception("Failed to initialize ZenithAgent")
        sys.exit(1)

    console.print("[bold green][OK] System Online. Ready for input.[/bold green]\n")
    console.print("[dim]Type 'exit' or 'quit' to terminate session.[/dim]\n")

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
                Panel(
                    "",
                    title="[bold magenta]Zenith Agent (Thinking...)[/bold magenta]",
                    border_style="magenta",
                ),
                refresh_per_second=10,
                auto_refresh=True,
            ) as live:
                async for event in agent.run_analysis_async(
                    user_input=user_input,
                    session_id="cli_session",
                    user_id="cli_user",
                ):
                    event_type = event.get("type")
                    if event_type == "chunk":
                        accumulated_text += event.get("content", "")
                    elif event_type == "quality":
                        meta = event.get("metadata") or {}
                        accumulated_text += (
                            f"\n\n### Painel de Qualidade\n"
                            f"- **Pontuação**: {meta.get('score', 0)}/100\n"
                            f"- **Análise**: {meta.get('feedback', '')}\n"
                        )
                    elif event_type == "error":
                        accumulated_text += f"\n\n⚠️ {event.get('content', '')}"

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
            logger.exception("Runtime error encountered in chat loop")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
