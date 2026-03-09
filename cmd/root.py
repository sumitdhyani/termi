import logging, click, os, sys, time
from openai import OpenAI
from internal.ai.openai_client import generate, generate_follow_up
from internal.ui.spinner import start_spinner
from internal.ui.output import print_ai_response, print_ai_clarification
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.argument("prompt", required=True)
@click.option("--toggle", "-t", is_flag=True, help="Help message for toggle")
@click.option("--log", "-l", is_flag=True, hidden=True, help="Enable debug logging to ~/.termi/termi.log")
@click.pass_context
def cli(ctx, prompt: str | None, toggle: bool, log: bool) -> None:
    """AI-powered terminal command helper.

    Usage: termi [options...] [PROMPT]
    """
    client = ctx.obj
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
        return

    elapsed = time.time() - start
    logger.info("Generated in %dms: %s", round(elapsed * 1000), resp.command)
    stop()

    command = resp.command
    while command.find("pardon:") != -1 or (hasattr(resp, "pardon") and getattr(resp, "pardon") != ""):
        pardon = resp.pardon if hasattr(resp, "pardon") else ""
        #print_ai_clarification(pardon if pardon != "" else command, elapsed)
        logger.info("Prompting for clarification")
        displayString = pardon if pardon != "" else command
        promptString = click.prompt(displayString + "\n", type=str).strip()
        resp = followUp(promptString, client)
        command = resp.command

    print_ai_response(resp.command, elapsed)

def followUp(prompt: str, client) -> None:
    """AI-powered terminal command helper.

    Usage: termi [PROMPT]
    """
    stop = start_spinner("thinking...")
    resp = generate_follow_up(prompt, client)
    stop()
    return resp
