"""
=============================================================================
MINI JARVIS - Assistant Commands Engine (assistant_commands.py)
=============================================================================
This module contains the intent recognition and command routing system.
It parses natural spoken or typed user input and routes it to the proper tool:
- System time and date
- Application launch (Chrome, Notepad, Calculator, Paint, etc.)
- Web searches & website openers (Google, YouTube, Wikipedia, etc.)
- Safe mathematical expression evaluator (using AST instead of dangerous eval)
- Note taking and retrieval (stored in SQLite)
- To-Do list management (stored in SQLite)
- Real-time weather reporting (using live meteorological API)
- User profile memory (remembering & updating preferred name)
- Hardware diagnostics (CPU, RAM, Battery)
=============================================================================
"""

import os
import re
import ast
import operator
import webbrowser
import subprocess
import datetime
import requests
import psutil
from typing import Tuple, Optional, Any

from config import APP_SHORTCUTS
from database import db
from brain import brain


# Safe operators map for AST-based mathematical evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_eval_math(expr: str) -> Optional[float]:
    """
    Safely evaluates a basic mathematical expression using Python's AST module.

    Computer Science Security Note:
    Using `eval(expr)` is dangerous because a malicious string like `eval("__import__('os').system('rmdir /s /q C:\\')")`
    could destroy the system. Using AST parses the string into an Abstract Syntax Tree
    and only allows mathematical operators and numbers!
    """
    try:
        # Normalize spoken words to math symbols
        expr = expr.lower()
        expr = expr.replace("plus", "+").replace("minus", "-")
        expr = expr.replace("times", "*").replace("multiplied by", "*").replace("into", "*").replace("x", "*")
        expr = expr.replace("divided by", "/").replace("divide", "/").replace("over", "/")
        expr = expr.replace("power of", "**").replace("power", "**")

        # Extract only allowed mathematical characters: digits, spaces, decimal dots, and operators
        cleaned = re.findall(r"[\d\.\+\-\*\/\(\)\s]+", expr)
        if not cleaned:
            return None
        expr_str = "".join(cleaned).strip()
        if not expr_str:
            return None

        node = ast.parse(expr_str, mode="eval")

        def _eval_node(n: Any) -> float:
            if isinstance(n, ast.Expression):
                return _eval_node(n.body)
            elif isinstance(n, ast.Constant):  # Python 3.8+ numbers
                return float(n.value)
            elif isinstance(n, ast.UnaryOp):
                op_type = type(n.op)
                if op_type in SAFE_OPERATORS:
                    return SAFE_OPERATORS[op_type](_eval_node(n.operand))
            elif isinstance(n, ast.BinOp):
                op_type = type(n.op)
                if op_type in SAFE_OPERATORS:
                    left = _eval_node(n.left)
                    right = _eval_node(n.right)
                    return SAFE_OPERATORS[op_type](left, right)
            raise ValueError(f"Unsupported syntax: {ast.dump(n)}")

        return _eval_node(node)
    except Exception:
        return None


class CommandHandler:
    """Dispatches user intents to specialized tools or to the AI Brain."""

    def handle_command(self, text: str) -> str:
        """
        Main routing function:
        1. Checks if the utterance matches a deterministic personal assistant command.
        2. If not, passes it to the AI brain for intelligent conversation and Q&A.
        """
        raw_text = text.strip()
        if not raw_text:
            return "I am listening, but I didn't hear any command."

        low_text = raw_text.lower()
        user_name = db.get_user_name()

        # -------------------------------------------------------------------
        # 1. TIME & DATE COMMANDS
        # -------------------------------------------------------------------
        if any(phrase in low_text for phrase in ["current time", "what time", "tell me the time", "what's the time"]):
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            return f"The current time is {time_str}, {user_name}."

        if any(phrase in low_text for phrase in ["current date", "what date", "today's date", "what is the date", "what day is today"]):
            now = datetime.datetime.now()
            date_str = now.strftime("%A, %B %d, %Y")
            return f"Today is {date_str}."

        # -------------------------------------------------------------------
        # 2. USER PROFILE & NAME MEMORY
        # -------------------------------------------------------------------
        # e.g., "Call me Tony", "My name is Bruce Wayne", "Remember my name is Alex"
        name_match = re.search(r"(?:call me|my name is|remember my name as)\s+([a-zA-Z0-9_\s]+)", low_text)
        if name_match:
            new_name = name_match.group(1).strip().title()
            db.set_user_name(new_name)
            return f"Certainly. I will address you as {new_name} from now on."

        if any(phrase in low_text for phrase in ["what is my name", "who am i", "do you know my name"]):
            return f"Your name is {user_name}, as recorded in my core memory banks."

        # -------------------------------------------------------------------
        # 3. APPLICATION LAUNCHING
        # -------------------------------------------------------------------
        if low_text.startswith("open ") or low_text.startswith("launch ") or low_text.startswith("start "):
            app_target = re.sub(r"^(open|launch|start)\s+", "", low_text).strip()

            # Check if it's Chrome
            if "chrome" in app_target:
                try:
                    subprocess.Popen(["start", "chrome"], shell=True)
                    return f"Opening Google Chrome, {user_name}."
                except Exception as e:
                    return f"Failed to launch Chrome: {e}"

            # Check common Windows applications in lookup dict
            for app_key, exe in APP_SHORTCUTS.items():
                if app_key in app_target:
                    try:
                        subprocess.Popen(exe, shell=True)
                        return f"Launching {app_key.title()} for you."
                    except Exception as e:
                        return f"Unable to start {app_key}: {e}"

            # Check if it looks like a website (e.g. "open github.com" or "open reddit")
            if "." in app_target and " " not in app_target:
                url = app_target if app_target.startswith("http") else f"https://{app_target}"
                webbrowser.open(url)
                return f"Opening {app_target} in your default browser."

        # -------------------------------------------------------------------
        # 4. WEB BROWSING & SEARCH
        # -------------------------------------------------------------------
        # Google search
        if low_text.startswith("search google for ") or low_text.startswith("google ") or low_text.startswith("search for "):
            query = re.sub(r"^(search google for|google|search for)\s+", "", low_text).strip()
            if query:
                search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
                webbrowser.open(search_url)
                return f"Searching Google for '{query}'."

        # YouTube search or open
        if "youtube" in low_text:
            if "search" in low_text or "play" in low_text:
                query = re.sub(r".*(?:search youtube for|play|on youtube)\s*", "", low_text).strip()
                if query:
                    yt_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
                    webbrowser.open(yt_url)
                    return f"Searching YouTube for '{query}'."
            webbrowser.open("https://www.youtube.com")
            return f"Opening YouTube, {user_name}."

        # Wikipedia search
        if "wikipedia" in low_text:
            query = re.sub(r".*(?:search wikipedia for|on wikipedia|wikipedia)\s*", "", low_text).strip()
            if query:
                wiki_url = f"https://en.wikipedia.org/wiki/{requests.utils.quote(query)}"
                webbrowser.open(wiki_url)
                return f"Opening Wikipedia article on '{query}'."

        # -------------------------------------------------------------------
        # 5. MATHEMATICS & CALCULATIONS
        # -------------------------------------------------------------------
        if any(w in low_text for w in ["calculate", "what is", "evaluate", "solve", "how much is"]) and any(op in low_text for op in ["+", "-", "*", "/", "plus", "minus", "times", "divided by", "into", "%"]):
            # Extract expression
            math_candidate = re.sub(r"^(calculate|what is|evaluate|solve|how much is)\s+", "", low_text).strip()
            result = safe_eval_math(math_candidate)
            if result is not None:
                # Format integer or float cleanly
                formatted = f"{int(result)}" if result.is_integer() else f"{result:.4f}".rstrip("0").rstrip(".")
                return f"The result of {math_candidate} is {formatted}."

        # -------------------------------------------------------------------
        # 6. NOTES MANAGEMENT
        # -------------------------------------------------------------------
        # Add note: "take a note buy bread", "save note study graphs", "write note ..."
        note_match = re.search(r"(?:take a note|save note|write note|add note)\s+(?:that\s+)?(.+)", low_text)
        if note_match:
            note_content = note_match.group(1).strip()
            note_id = db.add_note(note_content, title="Voice Note")
            return f"Note recorded: '{note_content}'."

        # Read notes: "show my notes", "read notes", "list notes"
        if any(phrase in low_text for phrase in ["show notes", "show my notes", "read my notes", "list notes", "my notes"]):
            notes = db.get_all_notes()
            if not notes:
                return "You do not have any saved notes in memory."
            preview = ", ".join([f"Note {n['id']}: {n['content']}" for n in notes[:5]])
            return f"You have {len(notes)} saved notes. Here are the latest: {preview}."

        # -------------------------------------------------------------------
        # 7. TO-DO LIST MANAGEMENT
        # -------------------------------------------------------------------
        # Add to-do: "add todo finish homework", "add to my todo list review os concepts"
        todo_match = re.search(r"(?:add to-do|add todo|add to my todo list|new task)\s+(?:to\s+)?(.+)", low_text)
        if todo_match:
            task_desc = todo_match.group(1).strip()
            db.add_todo(task_desc)
            return f"Added to your to-do list: '{task_desc}'."

        # View to-dos: "show todos", "what is on my todo list", "list tasks"
        if any(phrase in low_text for phrase in ["show todos", "show to-do", "todo list", "my tasks", "list tasks"]):
            todos = db.get_all_todos()
            if not todos:
                return "Your to-do list is currently empty. You are all caught up!"
            pending = [t['task'] for t in todos if not t['is_completed']]
            if not pending:
                return "All your pending tasks are completed!"
            tasks_preview = "; ".join(pending[:4])
            return f"You have {len(pending)} pending tasks: {tasks_preview}."

        # -------------------------------------------------------------------
        # 8. WEATHER LOOKUP (Live Meteorological API)
        # -------------------------------------------------------------------
        if "weather" in low_text or "temperature" in low_text:
            return self._fetch_weather(low_text)

        # -------------------------------------------------------------------
        # 9. HARDWARE DIAGNOSTICS & SYSTEM STATUS
        # -------------------------------------------------------------------
        if any(phrase in low_text for phrase in ["system status", "diagnostics", "battery", "cpu usage", "system performance"]):
            return self._get_system_diagnostics()

        # -------------------------------------------------------------------
        # 10. DELEGATE TO INTELLIGENT AI BRAIN
        # -------------------------------------------------------------------
        # If no specific local assistant command triggered, pass to the LLM / offline brain
        return brain.ask(raw_text)

    def _fetch_weather(self, query: str) -> str:
        """
        Retrieves real-time weather using wttr.in.
        Zero API keys required — highly dependable for students!
        """
        try:
            # Extract city if user asked "weather in Chicago" or "weather for London"
            match = re.search(r"weather (?:in|for|at)\s+([a-zA-Z\s]+)", query)
            city = match.group(1).strip() if match else ""

            # wttr.in format=3 returns: "City: condition +temp"
            endpoint = f"https://wttr.in/{requests.utils.quote(city)}?format=3" if city else "https://wttr.in/?format=3"
            response = requests.get(endpoint, timeout=4)
            if response.status_code == 200 and response.text.strip():
                clean_text = response.text.strip().replace("  ", " ")
                return f"Current meteorological report: {clean_text}"
            return "Unable to fetch the current weather forecast at this moment."
        except Exception as e:
            return "Meteorological servers are currently unreachable. Please check your internet connection."

    def _get_system_diagnostics(self) -> str:
        """Reads CPU, Memory, and Battery status via psutil."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.2)
            mem = psutil.virtual_memory()
            mem_percent = mem.percent

            battery = psutil.sensors_battery()
            battery_info = ""
            if battery:
                plugged = "plugged in" if battery.power_plugged else "on battery power"
                battery_info = f" Battery level is at {int(battery.percent)} percent and {plugged}."

            return (
                f"Diagnostic check complete: CPU load is at {cpu_percent} percent. "
                f"Memory utilization is at {mem_percent} percent.{battery_info} "
                f"All systems are green."
            )
        except Exception as e:
            return f"Diagnostic scan encountered a minor error: {e}"


# Singleton instance
commands = CommandHandler()
