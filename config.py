"""
=============================================================================
MINI JARVIS - Configuration Module (config.py)
=============================================================================
This file serves as the central hub for all settings, constants, file paths,
and visual theme options used throughout Mini Jarvis.

Why keep a separate config file?
- Software Engineering Best Practice: Avoid "magic numbers" and hardcoded
  values scattered around your code.
- Maintainability: If you want to change colors, speech speed, or API URLs,
  you do it in one single place.
=============================================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (if present)
load_dotenv()

# ---------------------------------------------------------------------------
# BASE DIRECTORIES & FILE PATHS
# ---------------------------------------------------------------------------
# Path to the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent

# Path to the SQLite memory database
DB_PATH = os.path.join(BASE_DIR, "jarvis_memory.db")

# Path to the .env file for storing user API keys safely
ENV_FILE_PATH = os.path.join(BASE_DIR, ".env")

# ---------------------------------------------------------------------------
# DEFAULT ASSISTANT & USER SETTINGS
# ---------------------------------------------------------------------------
DEFAULT_ASSISTANT_NAME = "Jarvis"
DEFAULT_USER_NAME = "Boss"  # Default greeting name (e.g., Sir, Boss, Tony)

# Text-to-Speech (TTS) Default Parameters
DEFAULT_VOICE_RATE = 175     # Speed: words per minute (typically 120-220)
DEFAULT_VOICE_VOLUME = 0.95  # Volume: 0.0 (silent) to 1.0 (maximum)
DEFAULT_VOICE_INDEX = 0      # 0 = Microsoft David (Male), 1 = Microsoft Zira (Female)

# ---------------------------------------------------------------------------
# LLM / AI BRAIN CONFIGURATION
# ---------------------------------------------------------------------------
# You can use OpenAI, Groq, OpenRouter, or a local model like Ollama!
# Free Groq base_url: "https://api.groq.com/openai/v1"
# Local Ollama base_url: "http://localhost:11434/v1"
# Default official OpenAI base_url: None (defaults to https://api.openai.com/v1)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()

# System prompt defining Jarvis's persona, capabilities, and tone
JARVIS_SYSTEM_PROMPT = (
    "You are JARVIS, an advanced, highly intelligent, loyal, and witty AI "
    "voice assistant inspired by Tony Stark's assistant in Iron Man. "
    "You communicate clearly, concisely, and respectfully. "
    "Keep spoken responses relatively brief (1 to 3 sentences) unless the user "
    "asks for an in-depth explanation or code. When answering coding or math "
    "questions, be accurate, structured, and easy to understand."
)

# ---------------------------------------------------------------------------
# FUTURISTIC JARVIS UI THEME COLORS (Hex Codes)
# ---------------------------------------------------------------------------
THEME = {
    "bg_dark": "#0a0e17",         # Deep sci-fi space black/blue background
    "bg_card": "#111827",         # Dark panel / card surface
    "bg_card_alt": "#1a2234",     # Alternate lighter card surface
    "accent_cyan": "#00d2ff",     # Stark Industries Electric Cyan
    "accent_blue": "#0284c7",     # Deep Hologram Blue
    "accent_glow": "#38bdf8",     # Neon glow highlight
    "text_primary": "#f8fafc",    # Crisp white for main headings/text
    "text_secondary": "#94a3b8",  # Muted silver for timestamps/subtext
    "text_accent": "#38bdf8",     # Electric cyan text for Jarvis responses
    "status_listening": "#10b981",# Emerald green when microphone is hot
    "status_thinking": "#f59e0b", # Amber/Gold when computing or calling API
    "status_speaking": "#00d2ff", # Cyan when speaking audio
    "status_idle": "#64748b",     # Slate grey when awaiting input
    "status_vision": "#a855f7",   # Neon purple when camera feed is active
    "danger": "#ef4444",          # Crimson red for delete/cancel actions
}

# ---------------------------------------------------------------------------
# COMMON WINDOWS APPLICATION SHORTCUTS
# ---------------------------------------------------------------------------
# Maps common names to system commands or executables
APP_SHORTCUTS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "command prompt": "cmd.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "control panel": "control.exe",
}
