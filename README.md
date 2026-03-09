# termi (Python)

AI-powered terminal command helper — Python rewrite.

## Setup

```bash
cd termi-python
pip install -r requirements.txt
```

## Usage

```bash
# Set your OpenAI API key
export OPENAI_KEY="sk-..."

# Run termi
python main.py "list all docker containers"

# Or install as a CLI tool
pip install -e .
termi "find large files over 100MB"
```

## Project Structure

```
termi-python/
├── main.py                      # Entry point
├── cmd/
│   └── root.py                  # CLI definition (click)
├── internal/
│   ├── ai/
│   │   └── openai_client.py     # OpenAI API integration
│   └── ui/
│       ├── executor.py          # Command execution
│       ├── menu.py              # Interactive menu
│       ├── output.py            # Styled output + clipboard
│       └── spinner.py           # Terminal spinner
├── utils/
│   └── utils.py                 # Host info & system prompt
├── requirements.txt
└── setup.py
```
