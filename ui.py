"""
=============================================================================
MINI JARVIS - Futuristic Desktop Interface (ui.py)
=============================================================================
This module constructs an Iron Man inspired GUI using CustomTkinter.

Key Technical Highlights:
1. Arc Reactor Visualizer:
   An interactive canvas drawing concentric glowing energy rings and rotating
   core arcs that pulse based on Jarvis's internal state (Idle, Listening, Thinking, Speaking).

2. Multi-Threaded UI Safety:
   Tkinter / CustomTkinter is not thread-safe. All updates coming from speech
   threads, audio recognition, or vision threads are routed through
   `root.after(0, ...)` to ensure 100% crash-free UI rendering.

3. Complete Feature Access:
   - Real-time chat dialogue with quick command chips
   - Voice controls (Push-to-Talk, Continuous Listen, Stop Speaking)
   - To-Do List manager with interactive completion checkboxes
   - Notes Vault with creation, viewing, and deletion
   - SQLite Memory viewer & User profile configuration
   - Live OpenCV Vision HUD with neural face detection stream
   - Voice speed, volume, and AI API settings
=============================================================================
"""

import math
import time
import threading
import tkinter as tk
from typing import Optional, Callable
import customtkinter as ctk
from PIL import Image

from config import THEME, DEFAULT_USER_NAME
from database import db
from voice_engine import voice
from voice_listener import listener
from assistant_commands import commands
from vision import vision
from brain import brain

# Configure CustomTkinter default appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ArcReactorCanvas(tk.Canvas):
    """Futuristic animated Stark Arc Reactor core."""

    def __init__(self, parent, size: int = 90, **kwargs):
        super().__init__(
            parent,
            width=size,
            height=size,
            bg=THEME["bg_card"],
            highlightthickness=0,
            **kwargs
        )
        self.size = size
        self.center = size // 2
        self.angle = 0
        self.pulse = 0
        self.pulse_dir = 1
        self.state_color = THEME["accent_cyan"]
        self._animate()

    def set_color(self, hex_color: str) -> None:
        self.state_color = hex_color

    def _animate(self) -> None:
        self.delete("all")
        cx, cy = self.center, self.center

        # Pulse breathing effect
        self.pulse += 0.08 * self.pulse_dir
        if self.pulse > 1.0:
            self.pulse_dir = -1
        elif self.pulse < 0.0:
            self.pulse_dir = 1

        glow_r = int(self.center * 0.88 + self.pulse * 3)
        inner_r = int(self.center * 0.55)
        core_r = int(self.center * 0.28)

        # Outer ring
        self.create_oval(
            cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r,
            outline=THEME["accent_blue"], width=2
        )

        # Middle energy ring
        self.create_oval(
            cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r,
            outline=self.state_color, width=2
        )

        # Rotating energy conduits (arcs)
        self.angle = (self.angle + 3) % 360
        for i in range(8):
            a = math.radians(self.angle + i * 45)
            x1 = cx + math.cos(a) * inner_r
            y1 = cy + math.sin(a) * inner_r
            x2 = cx + math.cos(a) * (glow_r - 2)
            y2 = cy + math.sin(a) * (glow_r - 2)
            self.create_line(x1, y1, x2, y2, fill=self.state_color, width=2)

        # Glowing central core
        self.create_oval(
            cx - core_r, cy - core_r, cx + core_r, cy + core_r,
            fill=self.state_color, outline="#ffffff", width=1
        )

        # Schedule next animation frame (~30 fps)
        self.after(33, self._animate)


class JarvisUI:
    """Main Application Window for Mini Jarvis."""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("MINI JARVIS — Stark Industries AI Assistant")
        self.root.geometry("1100x780")
        self.root.minsize(950, 680)
        self.root.configure(fg_color=THEME["bg_dark"])

        # Vision image reference to prevent garbage collection
        self._current_vision_ctk_img = None

        self._build_header()
        self._build_tabs()

        # Wire up engine callbacks for asynchronous status notifications
        voice.register_on_start(lambda: self.safe_update_status("SPEAKING", THEME["status_speaking"]))
        voice.register_on_finish(lambda: self.safe_update_status("IDLE", THEME["status_idle"]))

        listener.on_listening_state_change = self._on_listening_state_change
        listener.on_text_recognized = self._on_voice_text_received
        listener.on_error = lambda err: self.safe_add_message("System", err)

        # Initial welcome message
        self.root.after(500, self._boot_greeting)

    # -----------------------------------------------------------------------
    # THREAD-SAFE UI HELPERS
    # -----------------------------------------------------------------------
    def safe_run(self, func: Callable, *args, **kwargs) -> None:
        """Schedules a function to run safely on the Tkinter main thread."""
        self.root.after(0, lambda: func(*args, **kwargs))

    def safe_update_status(self, text: str, color: str) -> None:
        """Updates the status pill and Arc Reactor color safely from any thread."""
        def _apply():
            self.status_label.configure(text=f"● {text}", text_color=color)
            self.reactor.set_color(color)
        self.safe_run(_apply)

    def safe_add_message(self, sender: str, text: str) -> None:
        """Appends a new message bubble to the chat feed safely from any thread."""
        self.safe_run(self.add_message, sender, text)

    # -----------------------------------------------------------------------
    # HEADER & SYSTEM STATUS BAR
    # -----------------------------------------------------------------------
    def _build_header(self) -> None:
        header_frame = ctk.CTkFrame(
            self.root,
            fg_color=THEME["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["accent_blue"]
        )
        header_frame.pack(fill="x", padx=16, pady=(14, 8))

        # Arc Reactor Core Visualizer
        self.reactor = ArcReactorCanvas(header_frame, size=80)
        self.reactor.pack(side="left", padx=16, pady=8)

        # Title and Stark Branding
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", fill="y", pady=10)

        title_lbl = ctk.CTkLabel(
            title_box,
            text="MINI  JARVIS",
            font=ctk.CTkFont(family="Consolas", size=24, weight="bold"),
            text_color=THEME["accent_cyan"]
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            title_box,
            text="AUTONOMOUS PERSONAL AI & TACTICAL ASSISTANT • STARK INDUSTRIES",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=THEME["text_secondary"]
        )
        sub_lbl.pack(anchor="w")

        # Right-aligned live status badge
        status_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        status_box.pack(side="right", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(
            status_box,
            text="● IDLE",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=THEME["status_idle"]
        )
        self.status_label.pack(anchor="e")

        self.user_label = ctk.CTkLabel(
            status_box,
            text=f"OPERATOR: {db.get_user_name().upper()}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=THEME["text_secondary"]
        )
        self.user_label.pack(anchor="e")

    # -----------------------------------------------------------------------
    # TABVIEW NAVIGATION
    # -----------------------------------------------------------------------
    def _build_tabs(self) -> None:
        self.tabview = ctk.CTkTabview(
            self.root,
            fg_color=THEME["bg_card"],
            segmented_button_fg_color=THEME["bg_card_alt"],
            segmented_button_selected_color=THEME["accent_blue"],
            segmented_button_selected_hover_color=THEME["accent_glow"],
            segmented_button_unselected_hover_color=THEME["bg_card_alt"],
            text_color=THEME["text_primary"],
            corner_radius=12
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # Create individual tabs
        self.tab_chat = self.tabview.add("Console HUD")
        self.tab_todos = self.tabview.add("To-Do Hub")
        self.tab_notes = self.tabview.add("Notes Vault")
        self.tab_memory = self.tabview.add("Memory Log")
        self.tab_vision = self.tabview.add("Tactical Vision")
        self.tab_settings = self.tabview.add("Settings")

        # Build contents for each tab
        self._build_chat_tab()
        self._build_todos_tab()
        self._build_notes_tab()
        self._build_memory_tab()
        self._build_vision_tab()
        self._build_settings_tab()

    # -----------------------------------------------------------------------
    # TAB 1: CONSOLE HUD & CHAT
    # -----------------------------------------------------------------------
    def _build_chat_tab(self) -> None:
        parent = self.tab_chat

        # Quick action suggestion chips
        chips_frame = ctk.CTkFrame(parent, fg_color="transparent")
        chips_frame.pack(fill="x", padx=10, pady=(6, 4))

        quick_queries = [
            ("Weather Report", "What is the weather today?"),
            ("System Status", "Run system diagnostics"),
            ("My To-Dos", "Show my to-do list"),
            ("Explain Recursion", "Explain recursion with an example"),
            ("What's The Time", "What time is it?"),
        ]

        for label, query in quick_queries:
            btn = ctk.CTkButton(
                chips_frame,
                text=label,
                font=ctk.CTkFont(size=11),
                fg_color=THEME["bg_card_alt"],
                hover_color=THEME["accent_blue"],
                height=26,
                corner_radius=14,
                command=lambda q=query: self.process_query(q)
            )
            btn.pack(side="left", padx=4)

        # Scrollable chat messages container
        self.chat_container = ctk.CTkScrollableFrame(
            parent,
            fg_color=THEME["bg_dark"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["bg_card_alt"]
        )
        self.chat_container.pack(fill="both", expand=True, padx=10, pady=6)

        # Bottom Input Controls Frame
        input_frame = ctk.CTkFrame(parent, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(4, 10))

        # Text input box
        self.chat_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Enter a command, ask a question, or use your microphone...",
            font=ctk.CTkFont(size=13),
            fg_color=THEME["bg_card_alt"],
            border_color=THEME["accent_blue"],
            text_color=THEME["text_primary"],
            height=42,
            corner_radius=8
        )
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.chat_input.bind("<Return>", lambda event: self._on_send_click())

        # Send Button
        self.send_btn = ctk.CTkButton(
            input_frame,
            text="SEND",
            font=ctk.CTkFont(weight="bold"),
            fg_color=THEME["accent_blue"],
            hover_color=THEME["accent_glow"],
            width=80,
            height=42,
            corner_radius=8,
            command=self._on_send_click
        )
        self.send_btn.pack(side="left", padx=(0, 6))

        # Push to Talk / Single Listen Button
        self.mic_btn = ctk.CTkButton(
            input_frame,
            text="🎤 LISTEN",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#065f46",
            hover_color="#059669",
            width=100,
            height=42,
            corner_radius=8,
            command=self._on_listen_click
        )
        self.mic_btn.pack(side="left", padx=(0, 6))

        # Continuous listening toggle switch
        self.continuous_var = ctk.BooleanVar(value=False)
        self.continuous_switch = ctk.CTkSwitch(
            input_frame,
            text="Auto-Listen",
            variable=self.continuous_var,
            font=ctk.CTkFont(size=11),
            progress_color=THEME["status_listening"],
            command=self._on_continuous_toggle
        )
        self.continuous_switch.pack(side="left", padx=4)

        # Mute / Stop Speaking Button
        self.stop_speech_btn = ctk.CTkButton(
            input_frame,
            text="⏹ STOP",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#7f1d1d",
            hover_color=THEME["danger"],
            width=80,
            height=42,
            corner_radius=8,
            command=self._on_stop_speech_click
        )
        self.stop_speech_btn.pack(side="left", padx=(6, 0))

    def add_message(self, sender: str, text: str) -> None:
        """Appends a styled conversation card to the chat HUD."""
        is_user = (sender.lower() == "user")
        is_jarvis = (sender.lower() == "jarvis")

        card = ctk.CTkFrame(
            self.chat_container,
            fg_color=THEME["bg_card_alt"] if is_user else THEME["bg_card"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["accent_cyan"] if is_jarvis else "#374151"
        )
        card.pack(fill="x", padx=6, pady=4, anchor="e" if is_user else "w")

        # Header with Sender and Timestamp
        header_text = f"{db.get_user_name().upper()}" if is_user else "JARVIS"
        ts = time.strftime("%I:%M:%S %p")
        meta_label = ctk.CTkLabel(
            card,
            text=f"{header_text}  •  {ts}",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=THEME["accent_cyan"] if is_jarvis else THEME["text_secondary"]
        )
        meta_label.pack(anchor="w", padx=12, pady=(8, 2))

        # Message Body
        msg_label = ctk.CTkLabel(
            card,
            text=text,
            font=ctk.CTkFont(size=13),
            text_color=THEME["text_primary"],
            wraplength=760,
            justify="left"
        )
        msg_label.pack(anchor="w", padx=12, pady=(0, 10))

        # Auto-scroll to the bottom of the feed
        self.chat_container._parent_canvas.yview_moveto(1.0)

    def _boot_greeting(self) -> None:
        user = db.get_user_name()
        msg = f"Greetings, {user}. Mini Jarvis is initialized and standing by for your commands."
        self.add_message("Jarvis", msg)
        voice.speak(msg)

    def _on_send_click(self) -> None:
        text = self.chat_input.get().strip()
        if text:
            self.chat_input.delete(0, "end")
            self.process_query(text)

    def _on_listen_click(self) -> None:
        """Triggers a single-phrase listen on a background thread."""
        self.safe_update_status("LISTENING...", THEME["status_listening"])

        def _callback(text: Optional[str]):
            if text:
                self.safe_run(self.process_query, text)
            else:
                self.safe_update_status("IDLE", THEME["status_idle"])

        listener.listen_once_async(_callback)

    def _on_continuous_toggle(self) -> None:
        if self.continuous_var.get():
            listener.start_continuous_listening()
            self.safe_update_status("AUTO-LISTEN ON", THEME["status_listening"])
        else:
            listener.stop_continuous_listening()
            self.safe_update_status("IDLE", THEME["status_idle"])

    def _on_listening_state_change(self, is_listening: bool) -> None:
        if is_listening:
            self.safe_update_status("LISTENING...", THEME["status_listening"])
        else:
            if not voice.is_speaking():
                self.safe_update_status("IDLE", THEME["status_idle"])

    def _on_voice_text_received(self, text: str) -> None:
        self.safe_run(self.process_query, text)

    def _on_stop_speech_click(self) -> None:
        voice.stop()
        self.safe_update_status("IDLE", THEME["status_idle"])

    def process_query(self, text: str) -> None:
        """
        Processes a prompt asynchronously:
        1. Records user message in chat feed and database.
        2. Sets status to THINKING.
        3. Routes to command handler / AI brain in a worker thread.
        4. Speaks and displays Jarvis's response.
        """
        raw_text = text.strip()
        if not raw_text:
            return

        self.add_message("User", raw_text)
        db.add_conversation("user", raw_text)
        self.safe_update_status("THINKING...", THEME["status_thinking"])

        def _worker():
            try:
                response = commands.handle_command(raw_text)
            except Exception as e:
                response = f"An internal error occurred while processing: {e}"

            db.add_conversation("jarvis", response)
            self.safe_add_message("Jarvis", response)
            voice.speak(response)

            # Refresh dependent tabs in case commands modified to-dos or notes
            self.safe_run(self.refresh_todos)
            self.safe_run(self.refresh_notes)

        threading.Thread(target=_worker, daemon=True).start()

    # -----------------------------------------------------------------------
    # TAB 2: TO-DO HUB
    # -----------------------------------------------------------------------
    def _build_todos_tab(self) -> None:
        parent = self.tab_todos

        # Top Add Task Bar
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", padx=16, pady=12)

        self.todo_entry = ctk.CTkEntry(
            bar,
            placeholder_text="Enter a new task (e.g., 'Study Binary Search Trees')...",
            font=ctk.CTkFont(size=13),
            fg_color=THEME["bg_card_alt"],
            border_color=THEME["accent_blue"],
            height=40
        )
        self.todo_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.todo_entry.bind("<Return>", lambda e: self._on_add_todo())

        add_btn = ctk.CTkButton(
            bar,
            text="+ ADD TASK",
            font=ctk.CTkFont(weight="bold"),
            fg_color=THEME["accent_blue"],
            hover_color=THEME["accent_glow"],
            height=40,
            command=self._on_add_todo
        )
        add_btn.pack(side="left", padx=(0, 6))

        clear_btn = ctk.CTkButton(
            bar,
            text="CLEAR ALL",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#7f1d1d",
            hover_color=THEME["danger"],
            height=40,
            command=self._on_clear_todos
        )
        clear_btn.pack(side="left")

        # Scrollable Task List
        self.todos_list_frame = ctk.CTkScrollableFrame(
            parent,
            fg_color=THEME["bg_dark"],
            corner_radius=8
        )
        self.todos_list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.refresh_todos()

    def _on_add_todo(self) -> None:
        task_text = self.todo_entry.get().strip()
        if task_text:
            db.add_todo(task_text)
            self.todo_entry.delete(0, "end")
            self.refresh_todos()

    def _on_clear_todos(self) -> None:
        db.clear_all_todos()
        self.refresh_todos()

    def refresh_todos(self) -> None:
        """Rerenders all to-do rows from the SQLite database."""
        for widget in self.todos_list_frame.winfo_children():
            widget.destroy()

        todos = db.get_all_todos()
        if not todos:
            empty_lbl = ctk.CTkLabel(
                self.todos_list_frame,
                text="No pending tasks found. Speak 'Add to-do [task]' or type above!",
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_secondary"]
            )
            empty_lbl.pack(pady=30)
            return

        for item in todos:
            todo_id = item["id"]
            is_done = bool(item["is_completed"])

            row = ctk.CTkFrame(self.todos_list_frame, fg_color=THEME["bg_card_alt"], corner_radius=6)
            row.pack(fill="x", pady=4, padx=6)

            chk_var = ctk.BooleanVar(value=is_done)
            chk = ctk.CTkCheckBox(
                row,
                text=item["task"],
                variable=chk_var,
                font=ctk.CTkFont(size=13),
                command=lambda tid=todo_id: self._on_toggle_todo(tid)
            )
            chk.pack(side="left", padx=12, pady=10)

            del_btn = ctk.CTkButton(
                row,
                text="✕",
                width=32,
                height=28,
                fg_color="#7f1d1d",
                hover_color=THEME["danger"],
                command=lambda tid=todo_id: self._on_delete_todo(tid)
            )
            del_btn.pack(side="right", padx=10)

    def _on_toggle_todo(self, todo_id: int) -> None:
        db.toggle_todo(todo_id)
        self.refresh_todos()

    def _on_delete_todo(self, todo_id: int) -> None:
        db.delete_todo(todo_id)
        self.refresh_todos()

    # -----------------------------------------------------------------------
    # TAB 3: NOTES VAULT
    # -----------------------------------------------------------------------
    def _build_notes_tab(self) -> None:
        parent = self.tab_notes

        top_bar = ctk.CTkFrame(parent, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=12)

        self.note_title_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="Note Title (e.g., 'Sorting Algorithms')...",
            font=ctk.CTkFont(size=13),
            width=220,
            height=38,
            fg_color=THEME["bg_card_alt"],
            border_color=THEME["accent_blue"]
        )
        self.note_title_entry.pack(side="left", padx=(0, 8))

        self.note_content_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="Note Content...",
            font=ctk.CTkFont(size=13),
            height=38,
            fg_color=THEME["bg_card_alt"],
            border_color=THEME["accent_blue"]
        )
        self.note_content_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        save_note_btn = ctk.CTkButton(
            top_bar,
            text="+ SAVE NOTE",
            font=ctk.CTkFont(weight="bold"),
            fg_color=THEME["accent_blue"],
            hover_color=THEME["accent_glow"],
            height=38,
            command=self._on_save_note
        )
        save_note_btn.pack(side="left")

        # Scrollable list of notes
        self.notes_list_frame = ctk.CTkScrollableFrame(
            parent,
            fg_color=THEME["bg_dark"],
            corner_radius=8
        )
        self.notes_list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.refresh_notes()

    def _on_save_note(self) -> None:
        title = self.note_title_entry.get().strip() or "Quick Note"
        content = self.note_content_entry.get().strip()
        if content:
            db.add_note(content, title=title)
            self.note_title_entry.delete(0, "end")
            self.note_content_entry.delete(0, "end")
            self.refresh_notes()

    def refresh_notes(self) -> None:
        """Rerenders all saved notes from the SQLite database."""
        for widget in self.notes_list_frame.winfo_children():
            widget.destroy()

        notes = db.get_all_notes()
        if not notes:
            empty_lbl = ctk.CTkLabel(
                self.notes_list_frame,
                text="No notes recorded yet. Say 'Take a note [text]' or type above!",
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_secondary"]
            )
            empty_lbl.pack(pady=30)
            return

        for note in notes:
            nid = note["id"]
            card = ctk.CTkFrame(self.notes_list_frame, fg_color=THEME["bg_card_alt"], corner_radius=8)
            card.pack(fill="x", pady=6, padx=6)

            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=12, pady=(10, 2))

            title_lbl = ctk.CTkLabel(
                header,
                text=f"📌 {note['title']}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=THEME["accent_cyan"]
            )
            title_lbl.pack(side="left")

            ts_lbl = ctk.CTkLabel(
                header,
                text=note["timestamp"],
                font=ctk.CTkFont(size=11),
                text_color=THEME["text_secondary"]
            )
            ts_lbl.pack(side="left", padx=12)

            del_btn = ctk.CTkButton(
                header,
                text="DELETE",
                width=65,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color="#7f1d1d",
                hover_color=THEME["danger"],
                command=lambda note_id=nid: self._on_delete_note(note_id)
            )
            del_btn.pack(side="right")

            content_lbl = ctk.CTkLabel(
                card,
                text=note["content"],
                font=ctk.CTkFont(size=13),
                wraplength=760,
                justify="left"
            )
            content_lbl.pack(anchor="w", padx=12, pady=(2, 12))

    def _on_delete_note(self, note_id: int) -> None:
        db.delete_note(note_id)
        self.refresh_notes()

    # -----------------------------------------------------------------------
    # TAB 4: MEMORY LOG & HISTORY
    # -----------------------------------------------------------------------
    def _build_memory_tab(self) -> None:
        parent = self.tab_memory

        top_frame = ctk.CTkFrame(parent, fg_color=THEME["bg_card_alt"], corner_radius=8)
        top_frame.pack(fill="x", padx=16, pady=12)

        info_lbl = ctk.CTkLabel(
            top_frame,
            text="PERSISTENT CONVERSATION MEMORY (SQLITE3)",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=THEME["accent_cyan"]
        )
        info_lbl.pack(side="left", padx=16, pady=12)

        clear_history_btn = ctk.CTkButton(
            top_frame,
            text="WIPE CHAT MEMORY",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#7f1d1d",
            hover_color=THEME["danger"],
            command=self._on_wipe_memory
        )
        clear_history_btn.pack(side="right", padx=16, pady=12)

        self.memory_scroll = ctk.CTkScrollableFrame(parent, fg_color=THEME["bg_dark"], corner_radius=8)
        self.memory_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.refresh_memory()

    def _on_wipe_memory(self) -> None:
        db.clear_conversation_history()
        self.refresh_memory()

    def refresh_memory(self) -> None:
        for widget in self.memory_scroll.winfo_children():
            widget.destroy()

        history = db.get_recent_conversations(limit=50)
        if not history:
            lbl = ctk.CTkLabel(
                self.memory_scroll,
                text="Memory banks are currently clear.",
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_secondary"]
            )
            lbl.pack(pady=30)
            return

        for item in history:
            sender = item["sender"].upper()
            row = ctk.CTkFrame(self.memory_scroll, fg_color=THEME["bg_card_alt"], corner_radius=6)
            row.pack(fill="x", pady=3, padx=6)

            txt = f"[{item['timestamp']}] {sender}: {item['message']}"
            color = THEME["accent_cyan"] if item["sender"] == "jarvis" else THEME["text_primary"]

            lbl = ctk.CTkLabel(
                row,
                text=txt,
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color=color,
                wraplength=760,
                justify="left"
            )
            lbl.pack(anchor="w", padx=10, pady=6)

    # -----------------------------------------------------------------------
    # TAB 5: TACTICAL VISION (OPENCV HUD)
    # -----------------------------------------------------------------------
    def _build_vision_tab(self) -> None:
        parent = self.tab_vision

        ctrl_bar = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl_bar.pack(fill="x", padx=16, pady=10)

        self.vision_btn = ctk.CTkButton(
            ctrl_bar,
            text="ACTIVATE OPTICAL SENSORS",
            font=ctk.CTkFont(weight="bold"),
            fg_color=THEME["accent_blue"],
            hover_color=THEME["accent_glow"],
            height=38,
            command=self._on_toggle_vision
        )
        self.vision_btn.pack(side="left", padx=(0, 12))

        self.vision_status_lbl = ctk.CTkLabel(
            ctrl_bar,
            text="OPTICAL FEED: OFFLINE",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=THEME["status_idle"]
        )
        self.vision_status_lbl.pack(side="left")

        # Frame container for video canvas
        video_frame = ctk.CTkFrame(parent, fg_color=THEME["bg_dark"], corner_radius=8)
        video_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self.video_label = ctk.CTkLabel(video_frame, text="")
        self.video_label.pack(expand=True, pady=10)

    def _on_toggle_vision(self) -> None:
        if vision.is_running():
            vision.stop()
            self.vision_btn.configure(text="ACTIVATE OPTICAL SENSORS", fg_color=THEME["accent_blue"])
            self.vision_status_lbl.configure(text="OPTICAL FEED: OFFLINE", text_color=THEME["status_idle"])
            self.video_label.configure(image=None)
        else:
            success = vision.start(callback=self._on_vision_frame)
            if success:
                self.vision_btn.configure(text="DEACTIVATE OPTICAL SENSORS", fg_color="#7f1d1d")
                self.vision_status_lbl.configure(text="OPTICAL FEED: ACTIVE & TRACKING", text_color=THEME["status_vision"])
            else:
                self.vision_status_lbl.configure(text="CAMERA HARDWARE UNAVAILABLE", text_color=THEME["danger"])

    def _on_vision_frame(self, pil_image: Image.Image) -> None:
        """Callback from background vision thread to update image widget."""
        def _render():
            # Resize image cleanly to fit dashboard viewport
            img_resized = pil_image.resize((600, 450), Image.Resampling.BILINEAR)
            ctk_img = ctk.CTkImage(light_image=img_resized, dark_image=img_resized, size=(600, 450))
            self._current_vision_ctk_img = ctk_img
            self.video_label.configure(image=ctk_img)

        self.safe_run(_render)

    # -----------------------------------------------------------------------
    # TAB 6: SETTINGS
    # -----------------------------------------------------------------------
    def _build_settings_tab(self) -> None:
        parent = self.tab_settings

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=14)

        # 1. Voice Output Preferences
        voice_card = ctk.CTkFrame(scroll, fg_color=THEME["bg_card_alt"], corner_radius=8)
        voice_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            voice_card,
            text="SPEECH SYNTHESIS CONFIGURATION",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=THEME["accent_cyan"]
        ).pack(anchor="w", padx=16, pady=(12, 6))

        # Speaking Speed Slider
        ctk.CTkLabel(voice_card, text="Speaking Speed (Words per Minute):", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(4, 0))
        self.speed_slider = ctk.CTkSlider(
            voice_card,
            from_=110,
            to=240,
            number_of_steps=26,
            progress_color=THEME["accent_cyan"],
            command=lambda v: voice.set_rate(int(v))
        )
        self.speed_slider.set(voice.rate)
        self.speed_slider.pack(fill="x", padx=16, pady=4)

        # Speaking Volume Slider
        ctk.CTkLabel(voice_card, text="Audio Output Volume:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(8, 0))
        self.vol_slider = ctk.CTkSlider(
            voice_card,
            from_=0.1,
            to=1.0,
            number_of_steps=18,
            progress_color=THEME["accent_cyan"],
            command=lambda v: voice.set_volume(float(v))
        )
        self.vol_slider.set(voice.volume)
        self.vol_slider.pack(fill="x", padx=16, pady=4)

        # Voice Selection
        ctk.CTkLabel(voice_card, text="System Voice Persona:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(8, 0))
        voices_list = voice.get_available_voices()
        voice_names = [v["name"] for v in voices_list]
        initial_voice = voice_names[0] if voice_names else "Default"
        if 0 <= voice.voice_index < len(voice_names):
            initial_voice = voice_names[voice.voice_index]

        self.voice_opt = ctk.CTkOptionMenu(
            voice_card,
            values=voice_names,
            command=lambda val: voice.set_voice_index(voice_names.index(val))
        )
        self.voice_opt.set(initial_voice)
        self.voice_opt.pack(anchor="w", padx=16, pady=(4, 16))

        # 2. Operator Profile
        profile_card = ctk.CTkFrame(scroll, fg_color=THEME["bg_card_alt"], corner_radius=8)
        profile_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            profile_card,
            text="OPERATOR PROFILE",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=THEME["accent_cyan"]
        ).pack(anchor="w", padx=16, pady=(12, 6))

        ctk.CTkLabel(profile_card, text="Preferred Addressing Name:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(4, 0))
        self.name_entry = ctk.CTkEntry(profile_card, height=36)
        self.name_entry.insert(0, db.get_user_name())
        self.name_entry.pack(fill="x", padx=16, pady=(4, 14))

        # 3. AI Cognitive Brain / LLM API Configuration
        brain_card = ctk.CTkFrame(scroll, fg_color=THEME["bg_card_alt"], corner_radius=8)
        brain_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            brain_card,
            text="COGNITIVE BRAIN / LLM API SETTINGS",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=THEME["accent_cyan"]
        ).pack(anchor="w", padx=16, pady=(12, 4))

        ctk.CTkLabel(
            brain_card,
            text="Compatible with OpenAI, Groq (free), OpenRouter, or local Ollama (http://localhost:11434/v1).",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_secondary"]
        ).pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkLabel(brain_card, text="API Key:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(2, 0))
        self.api_key_entry = ctk.CTkEntry(brain_card, height=36, show="•")
        if brain.api_key:
            self.api_key_entry.insert(0, brain.api_key)
        self.api_key_entry.pack(fill="x", padx=16, pady=(4, 8))

        ctk.CTkLabel(brain_card, text="Base URL (Optional, leave blank for standard OpenAI):", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(2, 0))
        self.base_url_entry = ctk.CTkEntry(brain_card, height=36)
        if brain.base_url:
            self.base_url_entry.insert(0, brain.base_url)
        self.base_url_entry.pack(fill="x", padx=16, pady=(4, 8))

        ctk.CTkLabel(brain_card, text="Model Identifier (e.g. gpt-4o-mini, llama-3.3-70b-versatile):", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=16, pady=(2, 0))
        self.model_entry = ctk.CTkEntry(brain_card, height=36)
        self.model_entry.insert(0, brain.model)
        self.model_entry.pack(fill="x", padx=16, pady=(4, 16))

        # Save Button
        save_btn = ctk.CTkButton(
            scroll,
            text="SAVE ALL SETTINGS",
            font=ctk.CTkFont(weight="bold"),
            fg_color=THEME["accent_blue"],
            hover_color=THEME["accent_glow"],
            height=42,
            command=self._on_save_all_settings
        )
        save_btn.pack(fill="x", pady=10)

    def _on_save_all_settings(self) -> None:
        new_name = self.name_entry.get().strip() or DEFAULT_USER_NAME
        db.set_user_name(new_name)
        self.user_label.configure(text=f"OPERATOR: {new_name.upper()}")

        api_key = self.api_key_entry.get().strip()
        base_url = self.base_url_entry.get().strip()
        model = self.model_entry.get().strip()
        brain.update_credentials(api_key, base_url, model)

        confirm_msg = f"Settings updated successfully, {new_name}."
        self.add_message("Jarvis", confirm_msg)
        voice.speak("Configuration saved successfully.")

    def run(self) -> None:
        """Starts the Tkinter UI main event loop."""
        def _on_close():
            # Graceful shutdown of audio and vision background threads
            listener.stop_continuous_listening()
            vision.stop()
            voice.shutdown()
            self.root.destroy()

        self.root.protocol("WM_DELETE_WINDOW", _on_close)
        self.root.mainloop()
