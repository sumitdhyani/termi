#!/usr/bin/env python3
"""
termi - AI-powered terminal command helper (Python version)
"""

import sys
import os
from openai import OpenAI

# Add project root to path so internal imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cmd.root import cli


def main():
    openai_key = os.environ.get("OPENAI_KEY", "")
    if not openai_key:
        raise ValueError("SET OPENAI_KEY in env")

    client = OpenAI(api_key=openai_key)
    cli(obj=client)


if __name__ == "__main__":
    main()
