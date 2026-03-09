from enum import Enum

from rich.console import Console

console = Console()


class MenuOption(Enum):
    ELABORATE = "e"
    EXECUTE = "ex"
    CONTINUE = "c"
    EXIT = "x"
    INVALID = "invalid"


def show_menu() -> MenuOption:
    """Display the interactive menu and return the user's choice."""
    console.print()
    console.print("[cyan]What would you like to do?[/cyan]")
    console.print("[green]  E  → Elaborate (more details about command)[/green]")
    console.print("[green]  Ex → Execute the command[/green]")
    console.print("[green]  C  → Continue (ask follow-up question)[/green]")
    console.print("[green]  X  → Exit[/green]")

    user_input = input("> ").strip().lower()

    match user_input:
        case "e":
            return MenuOption.ELABORATE
        case "ex":
            return MenuOption.EXECUTE
        case "c":
            return MenuOption.CONTINUE
        case "x":
            return MenuOption.EXIT
        case _:
            console.print("Invalid option. Please try again.")
            return MenuOption.INVALID


def get_user_input(prompt: str) -> str:
    """Get free-form text input from the user."""
    return input(f"{prompt} ").strip()
