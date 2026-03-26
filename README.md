# Text Polisher

A lightweight macOS utility that fixes your spelling, grammar, and punctuation with a single shortcut. Uses [OpenRouter](https://openrouter.ai) to access a wide range of AI models. Optionally, you can run a local model via [MLX](https://github.com/ml-explore/mlx) for fully offline use.

## Setup

```bash
git clone https://github.com/edwindoit/text-polisher.git
cd text-polisher
cp config.example.json config.json
```

Open `config.json` and add your [OpenRouter API key](https://openrouter.ai/settings/keys):

```json
"openrouter_api_key": "sk-or-v1-your-key-here"
```

Then run the installer:

```bash
./install.sh
```

The install script will:
- Install Homebrew and Python 3 (if needed)
- Create a virtual environment with dependencies
- Set up auto-start on login

The only manual step is granting Accessibility permissions (the installer opens the settings page for you).

## Shortcuts

| Shortcut | Action |
|---|---|
| **Cmd+Shift+F** | Polish text and paste it back into the field |
| **Cmd+Shift+Z** | Polish text and copy to clipboard (doesn't paste) |

If text is selected, only the selection is polished. If nothing is selected, the entire field is selected and polished. A countdown notification shows the estimated time, and you'll hear a ping when it's done.

Works in: browsers, Notes, VS Code, Slack, and most other apps.

## Configuration

All configuration lives in `config.json` (see `config.example.json` for the format). You can add multiple models and switch between them by changing `active_model`.

### Adding models

Any model available on [OpenRouter](https://openrouter.ai/models) can be added:

```json
{
  "name": "Claude Sonnet 4.6",
  "provider": "openrouter",
  "model_id": "anthropic/claude-sonnet-4.6",
  "tokens_per_sec": 80.0
}
```

### Local models (optional)

To run a model locally without an API key, add an MLX model entry:

```json
{
  "name": "Qwen3 14B (MLX local)",
  "provider": "mlx",
  "model_id": "mlx-community/Qwen3-14B-6bit",
  "tokens_per_sec": 16.0
}
```

Any [MLX-compatible model](https://huggingface.co/mlx-community) will work. The model is downloaded automatically on first use.

## Customizing the Prompt

Edit `prompt.txt` to change how the AI polishes your text. Changes take effect immediately, no restart needed.

## Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.textpolisher.plist
rm ~/Library/LaunchAgents/com.textpolisher.plist
rm -rf ~/text-polisher  # or wherever you cloned it
```

## Troubleshooting

- **Hotkey not working** — Make sure you granted Accessibility permissions to the Python.app binary shown during install. A restart may be needed after granting.
- **"Out of credits" notification** — Top up your OpenRouter credits at [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys).
- **Logs** — Check `~/Library/Logs/text-polisher.log`.
