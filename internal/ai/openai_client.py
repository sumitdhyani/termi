import json
import logging
import os

from openai import OpenAI
from pydantic import BaseModel, Field

from utils.utils import get_host_info, build_command_system_prompt

logger = logging.getLogger(__name__)


class CommandResponse(BaseModel):
    command: str = Field(description="The command to execute")


def generate(prompt: str, client: any) -> CommandResponse:
    """
    Call OpenAI API to generate a terminal command for the given prompt.

    Args:
        prompt: The user's natural language request.
        client: OPenAI client

    Returns:
        A CommandResponse containing the generated command.

    Raises:
        ValueError: If OPENAI_KEY is not set.
        Exception: If the API call fails.
    """
    
    host_info = get_host_info()
    logger.debug("Host info: os=%s, distro=%s, arch=%s", host_info.os, host_info.distro, host_info.arch)

    system_prompt = build_command_system_prompt(
        host_info.os, host_info.distro, host_info.arch
    )
    logger.debug("System prompt length: %d chars", len(system_prompt))

    # Build the schema for structured output (OpenAI requires additionalProperties: false)
    schema = CommandResponse.model_json_schema()
    schema["additionalProperties"] = False

    logger.info("Calling OpenAI API (model=gpt-5-nano-2025-08-07) with prompt: %s", prompt)

    response = client.responses.create(
        model="gpt-5-nano-2025-08-07",
        input=system_prompt + "\n\nUser Prompt:\n" + prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "command_response",
                "schema": schema,
            }
        },
        tools=[{"type": "web_search"}],
        include=["web_search_call.action.sources"],
    )

    # Parse the response text as JSON
    raw_text = response.output_text
    logger.debug("Raw API response: %s", raw_text)

    data = json.loads(raw_text)
    logger.info("Parsed command: %s", data.get("command", "<missing>"))
    return CommandResponse(**data)