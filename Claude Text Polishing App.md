# Text Polisher — macOS Utility

## What This Is

A lightweight Python-based macOS utility that polishes text in any text field via a local LLM (Ollama). The user presses Cmd+L and the app automatically grabs text, sends it to Ollama for refinement, and pastes the corrected version back.

## Prerequisites (already installed)

- macOS
- Ollama (already installed locally)
- Python 3

## Project Structure

```
text-polisher/
├── text_polisher.py        # Main script with hotkey listener + Ollama integration
├── requirements.txt        # Python dependencies
├── install.sh              # One-command setup script
├── com.textpolisher.plist  # launchd plist for auto-start on login
└── README.md               # Usage instructions
```

## Implementation Plan

### Step 1: Project scaffolding

Create the directory structure and `requirements.txt` with:
- pynput
- pyperclip
- requests

### Step 2: Core script — `text_polisher.py`

Build the main script with these components:

**Configuration block at top:**
- `OLLAMA_URL = "http://localhost:11434/api/generate"`
- `MODEL = "mistral"` (configurable)
- `HOTKEY = "l"` (configurable)
- System prompt: instruct the LLM to fix spelling/grammar/punctuation only, preserve tone and meaning, return ONLY corrected text with no explanations or markdown

**Key simulation helpers:**
- Use `pynput.keyboard.Controller` to simulate keypresses
- `simulate_keys(*keys)` — press combo like Cmd+C, with ~150ms sleep after for OS processing
- `get_clipboard()` / `set_clipboard(text)` via pyperclip

**Ollama integration:**
- `call_ollama(text) -> str | None`
- POST to `/api/generate` with `stream: false`
- Timeout of 30s
- Handle connection errors gracefully (print warning, don't crash)

**Main polish flow — `polish_text()`:**
1. Guard against re-entry (use a `processing` flag)
2. Save original clipboard contents
3. Clear clipboard
4. Simulate Cmd+C to try copying current selection
5. Wait 200ms, check clipboard
6. If empty: simulate Cmd+A then Cmd+C (fallback to select all)
7. If still empty: abort, restore clipboard
8. Call `call_ollama(text)`
9. If success: set clipboard to polished text, simulate Cmd+V
10. If failure: restore original clipboard

**Global hotkey listener:**
- Track Cmd key state manually via `on_press` / `on_release`
- On Cmd+L: spawn `polish_text()` in a daemon thread (don't block the listener)
- Use `pynput.keyboard.Listener`

**Startup routine:**
- Print banner with model name and hotkey
- Ping `http://localhost:11434/api/tags` to verify Ollama is reachable
- Warn if not connected
- Start listener

### Step 3: Install script — `install.sh`

Bash script that:
1. Checks Python 3 is available
2. Creates a venv in the project directory (`python3 -m venv .venv`)
3. Installs requirements into the venv
4. Checks Ollama is reachable, pulls `mistral` model if not already present
5. Prints instructions about Accessibility permissions
6. Makes `text_polisher.py` executable

### Step 4: Launch agent — `com.textpolisher.plist`

A launchd plist so the polisher starts automatically on login:
- Label: `com.textpolisher`
- ProgramArguments: path to venv python + path to `text_polisher.py`
- RunAtLoad: true
- KeepAlive: true
- StandardOutPath / StandardErrorPath: `~/Library/Logs/text-polisher.log`

Include instructions in install.sh to:
- Copy plist to `~/Library/LaunchAgents/`
- Load with `launchctl load`

### Step 5: README.md

Write a clear README covering:
- What it does (with the Cmd+L flow)
- Quick start: `./install.sh && python3 text_polisher.py`
- How to change the model (edit MODEL in config)
- How to change the hotkey (edit HOTKEY in config)
- How to grant Accessibility permissions (System Settings path)
- How to enable auto-start on login (launchd)
- How to stop/uninstall
- Troubleshooting: Ollama not running, Accessibility not granted, hotkey conflicts (Cmd+L in browsers)

## Design Decisions

- **Cmd+L hotkey**: This conflicts with browser address bar focus. Note this in README and make it trivially configurable. Good alternatives: Cmd+Shift+L, Ctrl+Cmd+L, or Cmd+;
- **Selection vs select-all**: Try Cmd+C first. If clipboard is empty after, fall back to Cmd+A then Cmd+C. This handles both cases.
- **No GUI**: Runs as a background process. Prints status to terminal/log. Keep it minimal.
- **Error handling**: Never crash. Log errors, restore clipboard, and continue listening.
- **Thread safety**: Use a boolean `processing` guard so overlapping Cmd+L presses don't stack.

## Testing Checklist

After implementation, verify:
- [ ] `pip install -r requirements.txt` works
- [ ] Script starts and connects to Ollama
- [ ] Cmd+L with selected text polishes only selection
- [ ] Cmd+L with no selection polishes entire field
- [ ] Cmd+L with empty field does nothing (no crash)
- [ ] Works in: browser text field, Notes app, VS Code, Slack, terminal input
- [ ] Clipboard is usable after polishing (not wiped)
- [ ] Multiple rapid Cmd+L presses don't cause issues
- [ ] Script recovers gracefully if Ollama is not running
- [ ] install.sh completes without errors
- [ ] launchd plist loads and auto-starts the script
