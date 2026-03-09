import time

from rich.console import Console

try:
    import pyperclip
except ImportError:
    pyperclip = None

console = Console()


def print_ai_response(command: str, elapsed: float) -> None:
    """
    Print the AI-generated command with styling and copy to clipboard.

    Args:
        command: The command string to display.
        elapsed: Time taken in seconds.
    """
    # Copy to clipboard (best effort)
    if pyperclip:
        try:
            pyperclip.copy(command)
        except Exception:
            pass

    elapsed_ms = round(elapsed * 1000)

    console.print()
    console.print(f"[color(229)]{command}[/color(229)]")
    console.print()
    console.print(f"[color(241)]⏱  {elapsed_ms}ms   📋 copied[/color(241)]")
