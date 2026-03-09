import json
import os

from openai import OpenAI
from pydantic import BaseModel, Field

from utils.utils import get_host_info, build_command_system_prompt


class CommandResponse(BaseModel):
    command: str = Field(description="The command to execute")


def generate(prompt: str) -> CommandResponse:
    """
    Call OpenAI API to generate a terminal command for the given prompt.

    Args:
        prompt: The user's natural language request.

    Returns:
        A CommandResponse containing the generated command.

    Raises:
        ValueError: If OPENAI_KEY is not set.
        Exception: If the API call fails.
    """
    openai_key = os.environ.get("OPENAI_KEY", "")
    if not openai_key:
        raise ValueError("SET OPENAI_KEY in env")

    client = OpenAI(api_key=openai_key)

    host_info = get_host_info()
    system_prompt = build_command_system_prompt(
        host_info.os, host_info.distro, host_info.arch
    )

    # Build the schema for structured output (OpenAI requires additionalProperties: false)
    schema = CommandResponse.model_json_schema()
    schema["additionalProperties"] = False

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
    data = json.loads(raw_text)
    return CommandResponse(**data)
