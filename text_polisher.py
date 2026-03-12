#!/usr/bin/env python3
"""Text Polisher — macOS utility that polishes text via MLX."""

import os
import subprocess
import threading
import time

import pyperclip
from pynput.keyboard import Controller, Key, Listener

# ── Configuration ──────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_REPO = "mlx-community/Qwen3.5-9B-OptiQ-4bit"
PROMPT_FILE = os.path.join(SCRIPT_DIR, "prompt.txt")
MAX_TOKENS = 4096
DEFAULT_TOKENS_PER_SEC = 26.0  # conservative starting estimate

def load_prompt():
    """Load system prompt from prompt.txt (re-read each time so edits take effect immediately)."""
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

# MLX model (loaded at startup)
mlx_model = None
mlx_tokenizer = None
mlx_sampler = None
tokens_per_sec = DEFAULT_TOKENS_PER_SEC  # updated after each generation


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


def estimate_seconds(text):
    """Estimate generation time based on input token count and measured speed."""
    tokens = mlx_tokenizer.encode(text)
    estimated_output_tokens = len(tokens) * 1.1  # polished text ≈ same length + small margin
    return estimated_output_tokens / tokens_per_sec


NOTIFY_APP = os.path.join(SCRIPT_DIR, "TextPolisherNotify.app", "Contents", "MacOS", "notify")


def notify(title, message, duration=3, countdown=0):
    """Show a floating toast notification via the bundled helper app."""
    subprocess.Popen([NOTIFY_APP, title, message, str(duration), str(countdown)])


# ── MLX integration ───────────────────────────────────────────────

def load_mlx_model():
    """Load the MLX model and tokenizer."""
    global mlx_model, mlx_tokenizer, mlx_sampler
    from mlx_lm import load
    from mlx_lm.sample_utils import make_sampler

    print(f"[text-polisher] Loading {MODEL_REPO}...", flush=True)
    mlx_model, mlx_tokenizer = load(MODEL_REPO)
    # Non-thinking mode sampling parameters (recommended by Qwen)
    mlx_sampler = make_sampler(temp=0.7, top_p=0.8, top_k=20)
    print(f"[text-polisher] Model loaded.", flush=True)


def call_mlx(text):
    """Send text to MLX for polishing. Returns polished text or None."""
    global tokens_per_sec
    try:
        from mlx_lm import generate

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

        # Update measured speed for future estimates
        output_tokens = len(mlx_tokenizer.encode(response))
        if output_tokens > 0 and (t1 - t0) > 0:
            tokens_per_sec = output_tokens / (t1 - t0)
            print(f"[text-polisher] Speed: {tokens_per_sec:.1f} tok/s", flush=True)

        return response.strip()
    except Exception as e:
        print(f"[text-polisher] MLX error: {e}")
    return None


# ── Main polish flow ───────────────────────────────────────────────

def polish_text(paste=True):
    global processing
    if processing:
        return
    processing = True

    try:
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

        print(f"[text-polisher] Polishing {len(text)} chars...")

        # Show estimated time notification
        est_secs = estimate_seconds(text)
        notify("Text Polisher", "Polishing...", duration=est_secs + 2, countdown=int(est_secs))

        polished = call_mlx(text)

        if polished:
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
            notify("Text Polisher", "Polish failed, clipboard restored.")
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
    print("=" * 50)
    print("  Text Polisher (MLX)")
    print(f"  Model: {MODEL_REPO}")
    print("  Cmd+Shift+F  →  Polish & paste")
    print("  Cmd+Shift+Z  →  Polish & copy to clipboard")
    print("=" * 50)

    load_mlx_model()

    print("[text-polisher] Listening for hotkeys...")

    with Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
