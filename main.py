"""
=============================================================================
MINI JARVIS - Main Entry Point (main.py)
=============================================================================
This file serves as the main orchestrator for Mini Jarvis.

System Architecture Overview:
1. config.py            -> Constants, colors, file paths, and environment vars
2. database.py          -> SQLite persistent storage (Memory, Notes, To-Dos)
3. voice_engine.py      -> Thread-safe Text-to-Speech (pyttsx3) worker
4. voice_listener.py    -> Speech-to-Text audio capture (SpeechRecognition)
5. brain.py             -> OpenAI / Groq / Ollama LLM + offline CSE knowledge base
6. assistant_commands.py-> Intent parser & tool execution (Apps, Web, Weather, Math)
7. vision.py            -> OpenCV camera stream & AI face detection HUD
8. ui.py                -> CustomTkinter futuristic Iron Man desktop dashboard

How to run:
    python main.py           # Launches the full futuristic desktop dashboard
    python main.py --cli     # Runs in terminal voice/chat mode (no GUI)
=============================================================================
"""

import sys
import logging
from config import DEFAULT_ASSISTANT_NAME
from database import db
from voice_engine import voice
from voice_listener import listener
from assistant_commands import commands
from brain import brain

# Configure logging format
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)


def run_cli_mode() -> None:
    """Runs Jarvis in lightweight terminal mode for testing without GUI."""
    user_name = db.get_user_name()
    print("=" * 65)
    print(f"      {DEFAULT_ASSISTANT_NAME.upper()} - TERMINAL CONSOLE MODE")
    print(f"      Operator: {user_name} | Type 'exit' to quit")
    print("=" * 65)

    greeting = f"Terminal systems online. Ready for your command, {user_name}."
    print(f"\n[JARVIS]: {greeting}\n")
    voice.speak(greeting)

    while True:
        try:
            user_input = input(f"[{user_name}] > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "bye", "shutdown"]:
                farewell = f"Shutting down core protocols. Have a great day, {user_name}."
                print(f"\n[JARVIS]: {farewell}\n")
                voice.speak(farewell)
                break

            # Handle command & response
            response = commands.handle_command(user_input)
            db.add_conversation("user", user_input)
            db.add_conversation("jarvis", response)

            print(f"\n[JARVIS]: {response}\n")
            voice.speak(response)

        except (KeyboardInterrupt, EOFError):
            print("\nShutting down Mini Jarvis...")
            break

    voice.shutdown()


def main() -> None:
    """Main application launcher."""
    # Check if CLI mode was requested via command line argument
    if len(sys.argv) > 1 and sys.argv[1].lower() in ["--cli", "-c", "cli"]:
        run_cli_mode()
    else:
        # Import and launch the futuristic desktop GUI
        from ui import JarvisUI
        app = JarvisUI()
        app.run()


if __name__ == "__main__":
    main()
