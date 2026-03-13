#!/usr/bin/env python3
"""Text Polisher — macOS utility that polishes text via MLX or OpenRouter."""

import json
import os
import subprocess
import threading
import time

import pyperclip
from pynput.keyboard import Controller, Key, Listener

# ── Configuration ──────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
PROMPT_FILE = os.path.join(SCRIPT_DIR, "prompt.txt")
MAX_TOKENS = 4096

def load_config():
    """Load config.json (re-read each time so edits take effect on next polish)."""
    with open(CONFIG_FILE) as f:
        return json.load(f)

def get_active_model(config):
    """Return the active model's config dict."""
    return config["models"][str(config["active_model"])]

def load_prompt():
    """Load system prompt from prompt.txt."""
    try:
        with open(PROMPT_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Fix spelling, grammar, and punctuation only. Return ONLY the corrected text."

# ── State ──────────────────────────────────────────────────────────
keyboard = Controller()
processing = False
cmd_pressed = False
shift_pressed = False

# MLX model (loaded lazily, only if needed)
mlx_model = None
mlx_tokenizer = None
mlx_sampler = None
mlx_loaded_repo = None  # track which repo is loaded

# Measured speed (updated after each generation, falls back to config value)
measured_tokens_per_sec = None


# ── Helpers ────────────────────────────────────────────────────────

def simulate_keys(*keys):
    """Press a key combination (e.g. Cmd+C) and wait for the OS to process it."""
    for key in keys:
        keyboard.press(key)
    for key in reversed(keys):
        keyboard.release(key)
    time.sleep(0.1)


def get_clipboard():
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def set_clipboard(text):
    try:
        pyperclip.copy(text)
    except Exception:
        pass


def estimate_seconds(text, model_cfg):
    """Estimate generation time based on input token count and model speed."""
    speed = measured_tokens_per_sec or model_cfg["tokens_per_sec"]
    # Approximate token count: use MLX tokenizer if loaded, else ~4 chars/token
    if mlx_tokenizer and model_cfg["provider"] == "mlx":
        token_count = len(mlx_tokenizer.encode(text))
    else:
        token_count = len(text) / 4
    estimated_output_tokens = token_count * 1.1
    return estimated_output_tokens / speed


NOTIFY_APP = os.path.join(SCRIPT_DIR, "TextPolisherNotify.app", "Contents", "MacOS", "notify")


_notify_proc = None

def notify(title, message, duration=3, countdown=0):
    """Show a floating toast notification via the bundled helper app."""
    global _notify_proc
    dismiss_notify()
    _notify_proc = subprocess.Popen([NOTIFY_APP, title, message, str(duration), str(countdown)])

def dismiss_notify():
    """Dismiss the current notification if one is showing."""
    global _notify_proc
    if _notify_proc and _notify_proc.poll() is None:
        _notify_proc.kill()
    _notify_proc = None


# ── MLX integration ───────────────────────────────────────────────

def load_mlx_model(model_repo):
    """Load the MLX model and tokenizer (only if not already loaded for this repo)."""
    global mlx_model, mlx_tokenizer, mlx_sampler, mlx_loaded_repo
    if mlx_loaded_repo == model_repo:
        return
    from mlx_lm import load
    from mlx_lm.sample_utils import make_sampler

    print(f"[text-polisher] Loading {model_repo}...", flush=True)
    mlx_model, mlx_tokenizer = load(model_repo)
    mlx_sampler = make_sampler(temp=0.7, top_p=0.8, top_k=20)
    mlx_loaded_repo = model_repo
    print(f"[text-polisher] Model loaded.", flush=True)


def call_mlx(text, model_cfg):
    """Send text to MLX for polishing."""
    global measured_tokens_per_sec
    try:
        from mlx_lm import generate

        load_mlx_model(model_cfg["model_id"])

        messages = [
            {"role": "system", "content": load_prompt()},
            {"role": "user", "content": text},
        ]
        prompt = mlx_tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        t0 = time.time()
        response = generate(
            mlx_model,
            mlx_tokenizer,
            prompt=prompt,
            max_tokens=MAX_TOKENS,
            sampler=mlx_sampler,
        )
        t1 = time.time()

        output_tokens = len(mlx_tokenizer.encode(response))
        if output_tokens > 0 and (t1 - t0) > 0:
            measured_tokens_per_sec = output_tokens / (t1 - t0)
            print(f"[text-polisher] Speed: {measured_tokens_per_sec:.1f} tok/s", flush=True)

        return response.strip()
    except Exception as e:
        print(f"[text-polisher] MLX error: {e}")
    return None


# ── OpenRouter integration ────────────────────────────────────────

def call_openrouter(text, model_cfg, config):
    """Send text to OpenRouter for polishing."""
    global measured_tokens_per_sec
    import requests

    api_key = config.get("openrouter_api_key", "") or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("[text-polisher] No OpenRouter API key found in config or environment.")
        return None

    messages = [
        {"role": "system", "content": load_prompt()},
        {"role": "user", "content": text},
    ]

    try:
        t0 = time.time()
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_cfg["model_id"],
                "messages": messages,
                "max_tokens": min(MAX_TOKENS, int(len(text) / 3) + 256),
            },
            timeout=120,
        )
        if resp.status_code != 200:
            print(f"[text-polisher] OpenRouter HTTP {resp.status_code}: {resp.text}", flush=True)
            return None
        t1 = time.time()

        data = resp.json()
        result = data["choices"][0]["message"]["content"].strip()

        # Update measured speed from usage stats if available
        usage = data.get("usage", {})
        output_tokens = usage.get("completion_tokens", 0)
        if output_tokens > 0 and (t1 - t0) > 0:
            measured_tokens_per_sec = output_tokens / (t1 - t0)
            print(f"[text-polisher] Speed: {measured_tokens_per_sec:.1f} tok/s", flush=True)

        return result
    except Exception as e:
        print(f"[text-polisher] OpenRouter error: {e}")
    return None


# ── Main polish flow ───────────────────────────────────────────────

def polish_text(paste=True):
    global processing, measured_tokens_per_sec
    if processing:
        return
    processing = True

    try:
        config = load_config()
        model_cfg = get_active_model(config)
        model_name = model_cfg["name"]

        # Reset measured speed so we use the config estimate for this model
        measured_tokens_per_sec = None

        # Save original clipboard
        original_clipboard = get_clipboard()

        # Clear clipboard and try copying the current selection
        set_clipboard("")
        simulate_keys(Key.cmd, "c")
        time.sleep(0.1)

        text = get_clipboard()

        # If nothing was selected, fall back to select-all
        if not text:
            simulate_keys(Key.cmd, "a")
            simulate_keys(Key.cmd, "c")
            time.sleep(0.1)
            text = get_clipboard()

        # If still empty, abort
        if not text:
            set_clipboard(original_clipboard)
            print("[text-polisher] No text found to polish.")
            return

        print(f"[text-polisher] Polishing {len(text)} chars with {model_name}...")

        # Show estimated time notification
        est_secs = estimate_seconds(text, model_cfg)
        notify("Polishing...", model_name, duration=est_secs + 2, countdown=int(est_secs))

        # Route to the right provider
        if model_cfg["provider"] == "mlx":
            polished = call_mlx(text, model_cfg)
        elif model_cfg["provider"] == "openrouter":
            polished = call_openrouter(text, model_cfg, config)
        else:
            print(f"[text-polisher] Unknown provider: {model_cfg['provider']}")
            polished = None

        if polished:
            dismiss_notify()
            set_clipboard(polished)
            if paste:
                simulate_keys(Key.cmd, "v")
                time.sleep(0.1)
                print("[text-polisher] Done (pasted).")
            else:
                print("[text-polisher] Done (copied to clipboard).")
            subprocess.Popen(["afplay", "/System/Library/Sounds/Ping.aiff"])
        else:
            set_clipboard(original_clipboard)
            notify("Polish failed", "Clipboard restored.")
            print("[text-polisher] Polish failed, clipboard restored.")

    except Exception as e:
        print(f"[text-polisher] Unexpected error: {e}")
    finally:
        processing = False


# ── Hotkey listener (Cmd+Shift+F) ─────────────────────────────────

def on_press(key):
    global cmd_pressed, shift_pressed
    if key == Key.cmd or key == Key.cmd_r:
        cmd_pressed = True
    elif key == Key.shift or key == Key.shift_r:
        shift_pressed = True
    elif cmd_pressed and shift_pressed:
        try:
            if hasattr(key, "char") and key.char == "f":
                threading.Thread(target=polish_text, args=(True,), daemon=True).start()
            elif hasattr(key, "char") and key.char == "z":
                threading.Thread(target=polish_text, args=(False,), daemon=True).start()
        except AttributeError:
            pass


def on_release(key):
    global cmd_pressed, shift_pressed
    if key == Key.cmd or key == Key.cmd_r:
        cmd_pressed = False
    elif key == Key.shift or key == Key.shift_r:
        shift_pressed = False


# ── Startup ────────────────────────────────────────────────────────

def main():
    config = load_config()
    model_cfg = get_active_model(config)

    print("=" * 50)
    print("  Text Polisher")
    print(f"  Active model: {model_cfg['name']}")
    print(f"  Provider: {model_cfg['provider']}")
    print("  Cmd+Shift+F  →  Polish & paste")
    print("  Cmd+Shift+Z  →  Polish & copy to clipboard")
    print("=" * 50)

    # Pre-load MLX model if that's the active provider
    if model_cfg["provider"] == "mlx":
        load_mlx_model(model_cfg["model_id"])

    print("[text-polisher] Listening for hotkeys...")

    with Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
