import logging
import subprocess
import sys

from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


def execute_command(command: str) -> int:
    """
    Execute a shell command, streaming stdout/stderr to the terminal.
    Returns the exit code.
    """
    console.print()
    console.print(f"Executing: {command}")
    console.print()

    logger.info("Executing command: %s", command)
    try:
        result = subprocess.run(
            command,
            shell=True,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        logger.info("Command exit code: %d", result.returncode)
        return result.returncode
    except Exception as e:
        logger.error("Command execution failed: %s", e, exc_info=True)
        console.print(f"[red]Error executing command: {e}[/red]")
        return 1


def print_elaboration_prompt() -> None:
    """Print a styled elaboration prompt."""
    console.print()
    console.print("[yellow]Generating elaboration...[/yellow]")
