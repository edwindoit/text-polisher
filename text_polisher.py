#!/usr/bin/env python3
"""Text Polisher — macOS utility that polishes text via Ollama."""

import os
import subprocess
import threading
import time

import pyperclip
import requests
from pynput.keyboard import Controller, Key, Listener

# ── Configuration ──────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3.5:9b"
PROMPT_FILE = os.path.join(SCRIPT_DIR, "prompt.txt")
TIMEOUT = 60


def load_prompt():
    """Load system prompt from prompt.txt (re-read each time so edits take effect immediately)."""
    try:
        with open(PROMPT_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "Fix spelling, grammar, and punctuation only. Return ONLY the corrected text."

# ── State ──────────────────────────────────────────────────────────
keyboard = Controller()
session = requests.Session()  # reuse HTTP connection to Ollama
processing = False
cmd_pressed = False
shift_pressed = False


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


# ── Ollama integration ─────────────────────────────────────────────

def call_ollama(text):
    """Send text to Ollama for polishing. Returns polished text or None."""
    try:
        resp = session.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": text,
                "system": load_prompt(),
                "stream": False,
                "options": {"num_predict": 4096},
                "think": False,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.ConnectionError:
        print("[text-polisher] Ollama is not reachable. Is it running?")
    except requests.Timeout:
        print("[text-polisher] Ollama request timed out.")
    except Exception as e:
        print(f"[text-polisher] Ollama error: {e}")
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
        polished = call_ollama(text)

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
    print("  Text Polisher")
    print(f"  Model: {MODEL}")
    print("  Cmd+Shift+F  →  Polish & paste")
    print("  Cmd+Shift+Z  →  Polish & copy to clipboard")
    print("=" * 50)

    # Check Ollama connectivity and pre-warm model into memory
    try:
        resp = session.get("http://localhost:11434/api/tags", timeout=5)
        resp.raise_for_status()
        print("[text-polisher] Ollama is reachable. Loading model...", flush=True)
        session.post(OLLAMA_URL, json={"model": MODEL, "prompt": "", "stream": False, "think": False}, timeout=30)
        print(f"[text-polisher] {MODEL} loaded into memory.", flush=True)
    except Exception:
        print("[text-polisher] WARNING: Cannot reach Ollama. Make sure it's running.")

    print("[text-polisher] Listening for hotkeys...")

    with Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
