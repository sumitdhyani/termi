#!/usr/bin/env python3
"""
termi - AI-powered terminal command helper (Python version)
"""

import sys
import os

# Add project root to path so internal imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cmd.root import cli


def main():
    cli()


if __name__ == "__main__":
    main()
