import logging, click, os, sys, time
from openai import OpenAI
from internal.ai.openai_client import generate
from internal.ui.spinner import start_spinner
from internal.ui.output import print_ai_response
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


@click.command()
@click.argument("prompt", required=False, default=None)
@click.option("--toggle", "-t", is_flag=True, help="Help message for toggle")
@click.option("--log", "-l", is_flag=True, hidden=True, help="Enable debug logging to ~/.termi/termi.log")
def cli(prompt: str | None, toggle: bool, log: bool) -> None:
    """AI-powered terminal command helper.

    Usage: termi [options...] [PROMPT]
    """

    openai_key = os.environ.get("OPENAI_KEY", "")
    if not openai_key:
        raise ValueError("SET OPENAI_KEY in env")

    client = OpenAI(api_key=openai_key)

    setup_logging(enable=log)

    if prompt is None:
        click.echo(click.get_current_context().get_help())
        return

    logger.info("Prompt received: %s", prompt)

    stop = start_spinner("thinking...")

    start = time.time()
    try:
        resp = generate(prompt, client)
    except Exception as e:
        stop()
        logger.error("Generation failed: %s", e, exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    elapsed = time.time() - start
    logger.info("Generated in %dms: %s", round(elapsed * 1000), resp.command)

    stop()
    print_ai_response(resp.command, elapsed)

def followUp(prompt: str | None, toggle: bool, log: bool) -> None:
    """AI-powered terminal command helper.

    Usage: termi [PROMPT]
    """
    setup_logging(enable=log)

    if prompt is None:
        click.echo(click.get_current_context().get_help())
        return

    logger.info("Prompt received: %s", prompt)

    stop = start_spinner("thinking...")

    start = time.time()
    try:
        resp = generate(prompt)
    except Exception as e:
        stop()
        logger.error("Generation failed: %s", e, exc_info=True)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    elapsed = time.time() - start
    logger.info("Generated in %dms: %s", round(elapsed * 1000), resp.command)

    if False:
        pass
    else:
        stop()
        print_ai_response(resp.command, elapsed)
