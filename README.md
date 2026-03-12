# Text Polisher

A lightweight macOS utility that fixes your spelling, grammar, and punctuation using a local AI. Everything runs locally on your Mac — no data sent to the cloud. Powered by [MLX](https://github.com/ml-explore/mlx).

## Setup (one command)

Open Terminal and run:

```bash
git clone https://github.com/edwindoit/text-polisher.git
cd text-polisher
./install.sh
```

The install script will automatically:
- Install Homebrew and Python 3 (if needed)
- Create a virtual environment with dependencies
- Download the MLX model (~5 GB)
- Set up auto-start on login

The only manual step is granting Accessibility permissions (the installer opens the settings page for you).

## Shortcuts

| Shortcut | Action |
|---|---|
| **Cmd+Shift+F** | Polish text and paste it back into the field |
| **Cmd+Shift+Z** | Polish text and copy to clipboard (doesn't paste) |

If text is selected, only the selection is polished. If nothing is selected, the entire field is selected and polished. A countdown notification shows the estimated time, and you'll hear a ping when it's done.

Works in: browsers, Notes, VS Code, Slack, and most other apps.

## Customizing the Prompt

Edit `prompt.txt` to change how the AI polishes your text. Changes take effect immediately, no restart needed.

## Changing the Model

Edit `MODEL_REPO` at the top of `text_polisher.py`. Any [MLX-compatible model](https://huggingface.co/mlx-community) will work. After changing, restart:

```bash
launchctl unload ~/Library/LaunchAgents/com.textpolisher.plist
launchctl load ~/Library/LaunchAgents/com.textpolisher.plist
```

The new model will be downloaded automatically on first run.

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.textpolisher.plist
rm ~/Library/LaunchAgents/com.textpolisher.plist
rm -rf ~/text-polisher  # or wherever you cloned it
```

## Troubleshooting

- **Hotkey not working** — Make sure you granted Accessibility permissions to the Python.app binary shown during install. Restart may be needed after granting.
- **Logs** — Check `~/Library/Logs/text-polisher.log`.
