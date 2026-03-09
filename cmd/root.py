import sys
import time

import click

from internal.ai.openai_client import generate
from internal.ui.spinner import start_spinner
from internal.ui.output import print_ai_response


@click.command()
@click.argument("prompt", required=False, default=None)
@click.option("--toggle", "-t", is_flag=True, help="Help message for toggle")
def cli(prompt: str | None, toggle: bool) -> None:
    """AI-powered terminal command helper.

    Usage: termi [PROMPT]
    """
    if prompt is None:
        click.echo(click.get_current_context().get_help())
        return

    stop = start_spinner("thinking...")

    start = time.time()
    try:
        resp = generate(prompt)
    except Exception as e:
        stop()
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    stop()

    elapsed = time.time() - start
    print_ai_response(resp.command, elapsed)
