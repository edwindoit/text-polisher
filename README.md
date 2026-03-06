# Text Polisher

A lightweight macOS utility that fixes your spelling, grammar, and punctuation using a local AI. Everything runs locally on your Mac - no data sent to the cloud.

## Setup (one command)

Open Terminal and run:

```bash
git clone https://github.com/edwindoit/text-polisher.git
cd text-polisher
./install.sh
```

The install script will automatically:
- Install Homebrew (if needed)
- Install Python 3 (if needed)
- Install Ollama (if needed)
- Download the AI model (~6.6 GB)
- Set up auto-start on login

The only manual step is granting Accessibility permissions (the installer opens the settings page for you).

## Shortcuts

| Shortcut | Action |
|---|---|
| **Cmd+Shift+F** | Polish text and paste it back into the field |
| **Cmd+Shift+Z** | Polish text and copy to clipboard (doesn't paste) |

If text is selected, only the selection is polished. If nothing is selected, the entire field is selected and polished. You'll hear a ping sound when it's done.

Works in: browsers, Notes, VS Code, Slack, and most other apps.

## Customizing the Prompt

Edit `prompt.txt` to change how the AI polishes your text. Changes take effect immediately, no restart needed.

## Changing the Model

Edit `MODEL` at the top of `text_polisher.py`. Smaller models are faster, larger models are more accurate:

| Model | Size | Speed |
|---|---|---|
| `qwen3.5:4b` | 3.4 GB | Fast |
| `qwen3.5:9b` | 6.6 GB | Medium (default) |
| `mistral` | 4.4 GB | Slow |

After changing, pull the new model and restart:
```bash
ollama pull <model-name>
launchctl unload ~/Library/LaunchAgents/com.textpolisher.plist
launchctl load ~/Library/LaunchAgents/com.textpolisher.plist
```

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.textpolisher.plist
rm ~/Library/LaunchAgents/com.textpolisher.plist
rm -rf ~/text-polisher  # or wherever you cloned it
```

## Troubleshooting

- **Hotkey not working** — Make sure you granted Accessibility permissions to the Python.app binary shown during install. Restart may be needed after granting.
- **Ollama not reachable** — Open the Ollama app, or run `ollama serve`.
- **Logs** — Check `~/Library/Logs/text-polisher.log`.
