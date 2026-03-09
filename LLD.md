# Low-Level Design — termi-python

## 1. Project Structure & Layer Responsibilities

```
termi-python/
├── main.py                          # Bootstrap: sys.path, call cli()
├── cmd/
│   └── root.py                      # Orchestrator: Click CLI, main control loop
├── internal/
│   ├── ai/
│   │   └── openai_client.py         # Data layer: API call, schema, response parsing
│   └── ui/
│       ├── spinner.py               # Presentation: threaded loading animation
│       ├── output.py                # Presentation: styled command display + clipboard
│       ├── menu.py                  # Input: interactive option selector
│       └── executor.py              # Action: shell command execution
└── utils/
    └── utils.py                     # Infrastructure: host detection, prompt construction
```

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ENTRY LAYER                                │
│  main.py                                                            │
│  ─────────                                                          │
│  sys.path setup → imports cmd.root.cli → calls cli()                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        COMMAND LAYER — cmd/                         │
│  root.py                                                            │
│  ─────────                                                          │
│  @click.command                                                     │
│  cli(prompt, toggle)                                                │
│  Orchestrates: spinner → generate → display → menu loop             │
└───────┬──────────┬──────────┬──────────┬───────────────────────────┘
        │          │          │          │
        ▼          ▼          ▼          ▼
┌────────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
│ AI LAYER   │ │SPINNER │ │ OUTPUT │ │   MENU     │
│ openai_    │ │spinner │ │output  │ │  menu.py   │
│ client.py  │ │  .py   │ │  .py   │ │executor.py │
│            │ │        │ │        │ │            │
│ generate() │ │start   │ │print   │ │show_menu() │
│ elaborate()│ │_spinner │ │_ai_    │ │get_user    │
│            │ │        │ │response│ │_input()    │
│            │ │        │ │        │ │execute_    │
│            │ │        │ │        │ │command()   │
└─────┬──────┘ └────────┘ └───┬────┘ └─────┬──────┘
      │                       │             │
      ▼                       ▼             ▼
┌────────────┐          ┌──────────┐  ┌──────────┐
│ UTILS      │          │pyperclip │  │  bash    │
│ utils.py   │          │clipboard │  │subprocess│
│            │          └──────────┘  └──────────┘
│get_host    │
│_info()     │
│build_cmd   │
│_sys_prompt │
└─────┬──────┘
      │
      ▼
┌────────────┐     ┌─────────────────┐
│ platform   │     │  OpenAI API     │
│  stdlib    │     │ gpt-5-nano      │
└────────────┘     │ Responses API   │
                   └─────────────────┘
```

---

## 3. Module-by-Module Breakdown

### 3.1 — `main.py` (Entry Point)

| Aspect | Detail |
|--------|--------|
| **Role** | Bootstrap the application |
| **Mechanism** | Injects project root into `sys.path` so `cmd/`, `internal/`, `utils/` resolve as top-level packages. Imports `cli` from `cmd.root` and invokes it. |
| **Why sys.path hack?** | The project uses implicit namespace packages (no top-level package), so `sys.path.insert(0, ...)` ensures Python can find `cmd`, `internal`, `utils` as importable modules without requiring `pip install`. |

```python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cmd.root import cli
cli()  # Click takes over from here
```

---

### 3.2 — `cmd/root.py` (Orchestrator)

| Aspect | Detail |
|--------|--------|
| **Role** | Central control flow — the "brain" of the app |
| **Framework** | `click` (Python equivalent of Go's `cobra`) |
| **Signature** | `cli(prompt: str \| None, toggle: bool)` |

**Control flow within `cli()`:**

```
1. prompt is None? → show help, return
2. start_spinner("thinking...")
3. resp = generate(prompt)     ← blocks until API returns
4. stop()                      ← kill spinner
5. print_ai_response(resp.command, elapsed)
6. [menu loop — modules exist for E/Ex/C/X interaction]
```

**Key design decisions:**
- `@click.argument("prompt", required=False, default=None)` — makes prompt optional; no prompt = help text
- `time.time()` wraps the `generate()` call to measure latency
- Error handling: catches all exceptions from `generate()`, prints to stderr, exits with code 1
- The spinner `stop` function is called in both success and error paths (via try/except) to avoid leaving the terminal in a broken state

---

### 3.3 — `internal/ai/openai_client.py` (API Client)

This is the most critical module — it transforms a human prompt into a structured command.

| Aspect | Detail |
|--------|--------|
| **Role** | Build API request, send it, parse response into typed data |
| **API** | OpenAI Responses API (not Chat Completions) |
| **Model** | `gpt-5-nano-2025-08-07` |

**Data structures:**

```python
class CommandResponse(BaseModel):
    command: str = Field(description="The command to execute")
```

Pydantic serves double duty:
1. **Schema generation** — `CommandResponse.model_json_schema()` produces the JSON Schema sent to OpenAI's `text.format.json_schema` parameter, which forces the model to return structurally valid JSON.
2. **Response validation** — `CommandResponse(**data)` validates the parsed dict against the schema at runtime.

**`generate()` data flow, step by step:**

```
Step 1: Read OPENAI_KEY from env
        └── ValueError if missing

Step 2: OpenAI(api_key=...) — instantiate client

Step 3: get_host_info() → HostInfo(os="linux", distro="...", arch="amd64")

Step 4: build_command_system_prompt(os, distro, arch) → multi-paragraph string
        └── Injects OS/distro/arch into template at TWO places:
            a) Guidelines section (for context)
            b) System Variables block (for the model to use)

Step 5: Concatenate: system_prompt + "\n\nUser Prompt:\n" + prompt
        └── This becomes a SINGLE string input (not chat messages)

Step 6: Build JSON Schema from Pydantic:
        schema = CommandResponse.model_json_schema()
        schema["additionalProperties"] = False   ← OpenAI requirement

Step 7: API call:
        client.responses.create(
            model="gpt-5-nano-2025-08-07",
            input=combined_prompt,           ← flat string, not messages
            text={format: {type: "json_schema", name: "command_response", schema: ...}},
            tools=[{type: "web_search"}],    ← model CAN web search if needed
            include=["web_search_call.action.sources"]
        )

Step 8: Parse response:
        raw_text = response.output_text      ← string like '{"command": "..."}'
        data = json.loads(raw_text)          ← dict
        return CommandResponse(**data)       ← validated Pydantic model
```

**Why Responses API instead of Chat Completions?**
- Supports structured output via `text.format.json_schema` natively
- Built-in tool support (`web_search`) without manual function-calling plumbing
- `include` parameter lets you get web search sources in the response

---

### 3.4 — `utils/utils.py` (Host Context & Prompt Engineering)

| Aspect | Detail |
|--------|--------|
| **Role** | Detect runtime environment; build the system prompt |

**`get_host_info()`:**

```python
HostInfo(
    os     = platform.system().lower(),    # "linux", "darwin", "windows"
    distro = platform.platform(),          # "Linux-6.1.0-amd64-x86_64"
    arch   = platform.machine(),           # "x86_64", "aarch64"
)
```

Uses stdlib `platform` — no external dependency needed (Go version uses `gopsutil`).

**`build_command_system_prompt()`:**

Constructs a ~2KB prompt string that:
1. Defines the model's role: command generator
2. Feeds in the host's OS/distro/arch as system variables
3. Sets strict output format rules (no explanations, just the command)
4. Provides a worked example
5. Injects the actual host values at the bottom for the model to reference

The prompt uses Python f-string with doubled braces `{{{{os}}}}` to produce literal `{{os}}` in the output (template placeholders for the AI to understand).

---

### 3.5 — `internal/ui/spinner.py` (Loading Animation)

| Aspect | Detail |
|--------|--------|
| **Mechanism** | `threading.Thread` + `threading.Event` |
| **Frame rate** | 80ms per frame (12.5 FPS) |
| **Frames** | Braille dot spinner: `⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏` |

```
start_spinner("thinking...")
   │
   ├── Creates threading.Event (stop signal)
   ├── Spawns daemon thread running spin()
   │      └── Loop: write "\r⠋ thinking..." to stdout every 80ms
   │          └── Checks stop_event between frames
   │
   └── Returns stop() closure
          └── Sets event → joins thread → overwrites line with spaces
```

**Why threading, not asyncio?** The rest of the app is synchronous (Click is sync, OpenAI SDK `responses.create` is sync). A daemon thread is the simplest approach — it dies automatically if the main process crashes.

**Cleanup:** `stop()` writes `\r` + spaces + `\r` to hard-clear the line. This is Windows-safe (no ANSI escape codes needed).

---

### 3.6 — `internal/ui/output.py` (Display & Clipboard)

| Aspect | Detail |
|--------|--------|
| **Styling** | `rich.Console` with Rich markup tags |
| **Clipboard** | `pyperclip` (optional — gracefully degraded) |

```python
def print_ai_response(command: str, elapsed: float):
    pyperclip.copy(command)                           # best-effort clipboard
    console.print(f"[color(229)]{command}[/]")        # gold/yellow command
    console.print(f"[color(241)]⏱ {elapsed_ms}ms 📋 copied[/]")  # gray metadata
```

**Color mapping:**
- `color(229)` = ANSI 256-color gold — the command itself
- `color(241)` = ANSI 256-color dim gray — metadata line

**Clipboard strategy:** `pyperclip` is imported inside a try/except at module level. If unavailable (headless server, etc.), the clipboard step is silently skipped. The "📋 copied" text still shows — a minor UX inaccuracy that could be improved.

---

### 3.7 — `internal/ui/menu.py` (Interactive Menu)

| Aspect | Detail |
|--------|--------|
| **Options** | `MenuOption` Enum: ELABORATE, EXECUTE, CONTINUE, EXIT, INVALID |
| **Input** | Raw `input()` call — blocking, line-buffered |
| **Matching** | Python 3.10+ `match/case` statement |

```
show_menu() flow:
   Print styled options via Rich
   └── Read input → .strip().lower()
       └── match "e"  → ELABORATE
           match "ex" → EXECUTE
           match "c"  → CONTINUE
           match "x"  → EXIT
           _          → INVALID (prints error, caller retries)
```

`get_user_input(prompt)` is a thin wrapper around `input()` for the Continue flow — prompts the user for a follow-up question.

---

### 3.8 — `internal/ui/executor.py` (Shell Execution)

| Aspect | Detail |
|--------|--------|
| **Mechanism** | `subprocess.run(command, shell=True)` |
| **I/O** | stdin/stdout/stderr all connected to the parent terminal |

```python
def execute_command(command: str) -> int:
    result = subprocess.run(command, shell=True,
                            stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)
    return result.returncode
```

**`shell=True`** is critical — the generated commands may contain pipes, redirects, glob patterns, etc. that require a shell interpreter. The command string is passed directly to `/bin/sh -c`.

**Security consideration:** This executes arbitrary AI-generated commands. The menu flow (requiring explicit `Ex` confirmation) is the safety gate.

---

## 4. Full Data Flow Sequence

```
User                    main.py    root.py    spinner    openai_client    utils       OpenAI API    output     menu       executor    bash
 │                        │          │          │            │              │              │           │          │           │          │
 │ $ termi "find files"   │          │          │            │              │              │           │          │           │          │
 │───────────────────────>│          │          │            │              │              │           │          │           │          │
 │                        │ cli()    │          │            │              │              │           │          │           │          │
 │                        │─────────>│          │            │              │              │           │          │           │          │
 │                        │          │ extract  │            │              │              │           │          │           │          │
 │                        │          │ args[0]  │            │              │              │           │          │           │          │
 │                        │          │          │            │              │              │           │          │           │          │
 │                        │          │ start_   │            │              │              │           │          │           │          │
 │                        │          │ spinner()│            │              │              │           │          │           │          │
 │                        │          │─────────>│            │              │              │           │          │           │          │
 │                        │          │          │ thread     │              │              │           │          │           │          │
 │ ⠋ thinking...          │          │          │ animates   │              │              │           │          │           │          │
 │                        │          │          │            │              │              │           │          │           │          │
 │                        │          │ generate(prompt)      │              │              │           │          │           │          │
 │                        │          │─────────────────────->│              │              │           │          │           │          │
 │                        │          │          │            │ get_host_info│              │           │          │           │          │
 │                        │          │          │            │─────────────>│              │           │          │           │          │
 │                        │          │          │            │  HostInfo    │              │           │          │           │          │
 │                        │          │          │            │<─────────────│              │           │          │           │          │
 │                        │          │          │            │ build_prompt │              │           │          │           │          │
 │                        │          │          │            │─────────────>│              │           │          │           │          │
 │                        │          │          │            │  sys_prompt  │              │           │          │           │          │
 │                        │          │          │            │<─────────────│              │           │          │           │          │
 │                        │          │          │            │              │              │           │          │           │          │
 │                        │          │          │            │ responses.create(...)       │           │          │           │          │
 │                        │          │          │            │────────────────────────────>│           │          │           │          │
 │                        │          │          │            │   {"command":"find ..."}    │           │          │           │          │
 │                        │          │          │            │<────────────────────────────│           │          │           │          │
 │                        │          │          │            │              │              │           │          │           │          │
 │                        │          │          │            │ json.loads + │              │           │          │           │          │
 │                        │          │          │            │ Pydantic     │              │           │          │           │          │
 │                        │          │ CommandResponse       │              │              │           │          │           │          │
 │                        │          │<─────────────────────-│              │              │           │          │           │          │
 │                        │          │          │            │              │              │           │          │           │          │
 │                        │          │ stop()   │            │              │              │           │          │           │          │
 │                        │          │─────────>│ thread     │              │              │           │          │           │          │
 │                        │          │          │ joins      │              │              │           │          │           │          │
 │                        │          │          │            │              │              │           │          │           │          │
 │                        │          │ print_ai_response()   │              │              │           │          │           │          │
 │                        │          │──────────────────────────────────────────────────────────────->│          │           │          │
 │ find / -size +100M     │          │          │            │              │              │           │ clipboard│           │          │
 │ ⏱ 235ms 📋 copied     │          │          │            │              │              │           │          │           │          │
 │                        │          │          │            │              │              │           │          │           │          │
 │                        │          │ show_menu()           │              │              │           │          │           │          │
 │                        │          │───────────────────────────────────────────────────────────────────────────>│           │          │
 │ E/Ex/C/X?              │          │          │            │              │              │           │          │           │          │
 │ > ex                   │          │          │            │              │              │           │          │           │          │
 │                        │          │          │            │              │              │           │          │  EXECUTE  │          │
 │                        │          │ execute_command()     │              │              │           │          │           │          │
 │                        │          │─────────────────────────────────────────────────────────────────────────────────────->│          │
 │                        │          │          │            │              │              │           │          │           │ bash -c  │
 │                        │          │          │            │              │              │           │          │           │─────────>│
 │ (command output)       │          │          │            │              │              │           │          │           │          │
 │<────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────│
```

---

## 5. Data Transformation Pipeline

This table tracks how data morphs as it flows through the system:

| Stage | Location | Data Shape | Example |
|-------|----------|------------|---------|
| **User input** | CLI | `str` (raw) | `"find large files over 100MB"` |
| **Host context** | `utils.py` | `HostInfo` dataclass | `HostInfo(os="linux", distro="Linux-6.1.0...", arch="x86_64")` |
| **System prompt** | `utils.py` | `str` (~2KB) | `"You are a command helper tool..."` |
| **Combined input** | `openai_client.py` | `str` | `system_prompt + "\n\nUser Prompt:\n" + prompt` |
| **JSON Schema** | `openai_client.py` | `dict` | `{"type": "object", "properties": {"command": {"type": "string"}}, ...}` |
| **API request** | OpenAI SDK | HTTP POST JSON | `{model, input, text.format, tools, include}` |
| **API response** | OpenAI SDK | `Response` object | `response.output_text = '{"command": "find / -size +100M"}'` |
| **Parsed JSON** | `openai_client.py` | `dict` | `{"command": "find / -size +100M"}` |
| **Typed response** | `openai_client.py` | `CommandResponse` | `.command = "find / -size +100M"` |
| **Display** | `output.py` | Rich markup → ANSI | Gold-colored command + gray metadata |
| **Clipboard** | `output.py` | `str` (plain) | `"find / -size +100M"` |
| **Execution** | `executor.py` | `str` → shell process | `subprocess.run("find / -size +100M", shell=True)` |

---

## 6. Application State Machine

```
                    ┌──────────────┐
                    │  Parse Args  │
                    └──────┬───────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
         prompt is None         prompt provided
                │                     │
                ▼                     ▼
          Show Help            Spinner On
                │                     │
                ▼                     ▼
              EXIT              Call API ──────────► Error
                                  │                    │
                                  ▼                    ▼
                            Parse Response        Spinner Off
                                  │                    │
                                  ▼                    ▼
                            Spinner Off             EXIT(1)
                                  │
                                  ▼
                          Display Result
                                  │
                                  ▼
                    ┌─────── Menu Loop ──────────┐
                    │                            │
                    ▼                            │
              Wait for Input ◄───── Invalid ────┘
                    │
        ┌───────┬──┴────┬─────────┐
        ▼       ▼       ▼         ▼
     E(lab)  Ex(ec)   C(ont)    X(exit)
        │       │       │         │
        ▼       │       ▼         ▼
  Call API      │  get_user_    EXIT
  for explain   │  input()
        │       │       │
        ▼       │       ▼
  Print         │  generate()
  explanation   │  new prompt
        │       │       │
        │       │       ▼
        │       │  Print new
        │       │  command
        │       │       │
        └───────┼───────┘
                │ (all loop back to Wait for Input)
                │
                ▼
          subprocess.run()
                │
                ▼
              EXIT
```

---

## 7. Error Handling Strategy

| Error | Where Caught | Behavior |
|-------|-------------|----------|
| `OPENAI_KEY` not set | `openai_client.py` | `ValueError` raised immediately |
| API call fails (network, auth, rate limit) | `cmd/root.py` | `except Exception` → print to stderr → `sys.exit(1)` |
| JSON parse error | `openai_client.py` | `json.loads` raises `JSONDecodeError` → bubbles up |
| Pydantic validation error | `openai_client.py` | `ValidationError` if response doesn't match schema → bubbles up |
| Clipboard unavailable | `output.py` | Silently swallowed (try/except at module import + per-call) |
| Command execution fails | `executor.py` | Prints red error via Rich, returns exit code |
| Invalid menu input | `menu.py` | Returns `INVALID` → caller loop retries |

---

## 8. Threading Model

```
Main Thread                         Spinner Thread (daemon)
────────────                        ──────────────────────
cli() starts
  │
  ├── start_spinner() ──────────────► spin() loop starts
  │                                   writing \r frames
  │
  ├── generate(prompt) [BLOCKING]     ↕ continues animating
  │   └── HTTP request to OpenAI      ↕
  │   └── waits for response          ↕
  │
  ├── stop() ───────────────────────► event.set() → join()
  │                                   thread exits
  ├── print_ai_response()
  ├── show_menu() [BLOCKING on stdin]
  │   ...
```

Only **two threads** ever exist: the main thread and the spinner. The spinner is a daemon thread so it won't prevent process exit if the main thread crashes.

---

## 9. Dependency Map

| Dependency | Version | Used By | Purpose |
|-----------|---------|---------|---------|
| `openai` | >=1.0.0 | `openai_client.py` | API client (Responses endpoint) |
| `click` | >=8.0.0 | `cmd/root.py` | CLI argument parsing & help generation |
| `rich` | >=13.0.0 | `output.py`, `menu.py`, `executor.py` | Terminal styling (ANSI colors, markup) |
| `pyperclip` | >=1.8.0 | `output.py` | Cross-platform clipboard access |
| `pydantic` | >=2.0.0 | `openai_client.py` | Response schema generation + validation |
| `platform` | stdlib | `utils.py` | Host OS/arch detection |
| `threading` | stdlib | `spinner.py` | Background animation |
| `subprocess` | stdlib | `executor.py` | Shell command execution |
| `json` | stdlib | `openai_client.py` | Response text parsing |

---

## 10. Library Mapping (Go → Python)

| Go Library | Python Equivalent | Notes |
|---|---|---|
| `cobra` | `click` | CLI framework with decorators instead of structs |
| `lipgloss` | `rich` | Terminal styling via markup tags |
| `openai-go` | `openai` | Official SDK, Responses API |
| `gopsutil` | `platform` (stdlib) | No external dep needed in Python |
| `clipboard` | `pyperclip` | Cross-platform clipboard |
| `jsonschema` | `pydantic` | Schema gen + validation in one library |
