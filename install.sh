#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.textpolisher.plist"
MODEL_REPO="mlx-community/Qwen3.5-9B-OptiQ-4bit"

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║       Text Polisher — Setup          ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ── 1. Homebrew ────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    echo "→ Installing Homebrew (macOS package manager)..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH for this session
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    echo "✓ Homebrew installed."
else
    echo "✓ Homebrew found."
fi

# ── 2. Python 3 ───────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "→ Installing Python 3..."
    brew install python@3
    echo "✓ Python 3 installed."
else
    echo "✓ Python 3 found: $(python3 --version)"
fi

# ── 3. Python virtual environment + dependencies ──────────────────
echo "→ Setting up Python environment..."
python3 -m venv "$SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo "✓ Dependencies installed (including mlx-lm)."

# ── 4. Download MLX model ─────────────────────────────────────────
echo "→ Downloading MLX model ($MODEL_REPO)... this may take a few minutes on first run."
"$SCRIPT_DIR/.venv/bin/python" -c "
from mlx_lm import load
print('Loading model to trigger download...')
load('$MODEL_REPO')
print('Model ready.')
"
echo "✓ Model downloaded."

# ── 5. Find the Python.app binary (needed for Accessibility) ──────
# macOS requires the actual running binary to have Accessibility access.
# Homebrew Python runs through Python.app, not the CLI binary.
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
REAL_PYTHON="$(python3 -c "import sys, os; print(os.path.realpath(sys.executable))")"
PYTHON_APP_DIR="$(dirname "$REAL_PYTHON")/../Resources/Python.app/Contents/MacOS/Python"

if [[ -f "$PYTHON_APP_DIR" ]]; then
    LAUNCH_PYTHON="$PYTHON_APP_DIR"
else
    LAUNCH_PYTHON="$PYTHON_BIN"
fi

# ── 6. Install launchd plist ──────────────────────────────────────
echo "→ Setting up auto-start on login..."
chmod +x "$SCRIPT_DIR/text_polisher.py"
mkdir -p ~/Library/LaunchAgents
mkdir -p ~/Library/Logs

LOG_PATH="$HOME/Library/Logs/text-polisher.log"

cat > ~/Library/LaunchAgents/$PLIST_NAME << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.textpolisher</string>
    <key>ProgramArguments</key>
    <array>
        <string>$LAUNCH_PYTHON</string>
        <string>$SCRIPT_DIR/text_polisher.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$SCRIPT_DIR/.venv/lib/python$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")/site-packages</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$LOG_PATH</string>
    <key>StandardErrorPath</key>
    <string>$LOG_PATH</string>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
</dict>
</plist>
EOF

launchctl unload ~/Library/LaunchAgents/$PLIST_NAME 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/$PLIST_NAME
echo "✓ Text Polisher is running and will auto-start on login."

# ── 7. Done ───────────────────────────────────────────────────────
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║          Setup complete!             ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
echo "  Cmd+Shift+F  →  Polish & paste"
echo "  Cmd+Shift+Z  →  Polish & copy to clipboard"
echo "  Model:   $MODEL_REPO (MLX)"
echo "  Logs:    ~/Library/Logs/text-polisher.log"
echo "  Prompt:  $SCRIPT_DIR/prompt.txt"
echo ""
echo "  ┌──────────────────────────────────────┐"
echo "  │  ONE MORE STEP — Accessibility       │"
echo "  │                                      │"
echo "  │  System Settings                     │"
echo "  │    → Privacy & Security              │"
echo "  │    → Accessibility                   │"
echo "  │                                      │"
echo "  │  Click + and add:                    │"
echo "  │  $LAUNCH_PYTHON"
echo "  │                                      │"
echo "  │  (Tip: in the file picker, press     │"
echo "  │   Cmd+Shift+G and paste the path)    │"
echo "  └──────────────────────────────────────┘"
echo ""

# Try to open Accessibility settings for the user
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || true
