"""
=============================================================================
MINI JARVIS - Text-To-Speech Engine (voice_engine.py)
=============================================================================
This module turns textual responses into audible speech using `pyttsx3`.

Key Engineering Challenges Solved:
1. Non-Blocking Audio:
   Speaking takes time. If you run `engine.say()` and `engine.runAndWait()` on
   the main thread, your entire desktop window freezes until Jarvis stops talking!
   Solution: We run a background worker thread with a FIFO Queue.

2. No Overlapping Speech:
   Multiple commands arriving at once won't speak on top of each other.
   Every utterance queues sequentially, or can be interrupted with `stop()`.

3. Windows COM Thread Safety:
   On Windows, `pyttsx3` uses Microsoft SAPI5 which requires COM initialization
   via `pythoncom.CoInitialize()` within the thread that drives the audio.
=============================================================================
"""

import queue
import threading
import logging
from typing import List, Dict, Callable, Optional
import pyttsx3

# On Windows, pythoncom is part of pywin32, ensuring SAPI5 COM calls succeed in subthreads
try:
    import pythoncom
except ImportError:
    pythoncom = None

from database import db


class VoiceEngine:
    """Thread-safe, non-blocking Text-to-Speech manager using pyttsx3."""

    def __init__(self):
        self._speech_queue = queue.Queue()
        self._is_running = True
        self._is_speaking = False
        self._stop_requested = False

        # Callbacks to notify UI when speaking starts and ends
        self._on_start_callbacks: List[Callable[[], None]] = []
        self._on_finish_callbacks: List[Callable[[], None]] = []

        # Read saved voice preferences from DB (or fall back to defaults)
        self.rate = int(db.get_setting("voice_rate", "175"))
        self.volume = float(db.get_setting("voice_volume", "0.95"))
        self.voice_index = int(db.get_setting("voice_index", "0"))

        # Launch the dedicated audio worker thread
        self._worker_thread = threading.Thread(
            target=self._tts_worker,
            name="JarvisTTSWorker",
            daemon=True
        )
        self._worker_thread.start()

    def register_on_start(self, callback: Callable[[], None]) -> None:
        """Register a function to call right before speech begins (e.g. set status to 'SPEAKING')."""
        self._on_start_callbacks.append(callback)

    def register_on_finish(self, callback: Callable[[], None]) -> None:
        """Register a function to call right after speech ends (e.g. set status back to 'IDLE')."""
        self._on_finish_callbacks.append(callback)

    def _notify_start(self) -> None:
        self._is_speaking = True
        for cb in self._on_start_callbacks:
            try:
                cb()
            except Exception as e:
                logging.error(f"Error in TTS start callback: {e}")

    def _notify_finish(self) -> None:
        self._is_speaking = False
        for cb in self._on_finish_callbacks:
            try:
                cb()
            except Exception as e:
                logging.error(f"Error in TTS finish callback: {e}")

    def _tts_worker(self) -> None:
        """Background loop that processes incoming text messages sequentially."""
        if pythoncom:
            pythoncom.CoInitialize()

        try:
            engine = pyttsx3.init()
            self._apply_properties(engine)

            while self._is_running:
                try:
                    # Wait up to 0.5s for new text so the loop can react to shutdowns
                    item = self._speech_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if item is None:
                    # None is our poison pill sentinel indicating shutdown
                    self._speech_queue.task_done()
                    break

                # If an interruption was requested, skip queued utterance
                if self._stop_requested:
                    self._speech_queue.task_done()
                    self._stop_requested = False
                    continue

                text = str(item).strip()
                if not text:
                    self._speech_queue.task_done()
                    continue

                # Refresh properties in case user changed rate/volume/voice in settings
                self._apply_properties(engine)

                self._notify_start()
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as ex:
                    logging.error(f"TTS runAndWait error: {ex}")
                finally:
                    self._notify_finish()
                    self._speech_queue.task_done()

        finally:
            if pythoncom:
                pythoncom.CoUninitialize()

    def _apply_properties(self, engine: pyttsx3.Engine) -> None:
        """Applies speed, volume, and voice selection to the pyttsx3 engine."""
        try:
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            voices = engine.getProperty("voices")
            if voices and 0 <= self.voice_index < len(voices):
                engine.setProperty("voice", voices[self.voice_index].id)
        except Exception as e:
            logging.error(f"Failed to set engine properties: {e}")

    def speak(self, text: str) -> None:
        """
        Public method: Queues text to be spoken asynchronously.
        Does not block the calling thread!
        """
        if text and text.strip():
            self._speech_queue.put(text.strip())

    def stop(self) -> None:
        """Immediately discard pending audio in queue and mark stop request."""
        self._stop_requested = True
        # Drain remaining items in the queue
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
                self._speech_queue.task_done()
            except queue.Empty:
                break
        self._is_speaking = False
        self._notify_finish()

    def is_speaking(self) -> bool:
        """Returns True if Jarvis is currently outputting sound."""
        return self._is_speaking

    def set_rate(self, rate: int) -> None:
        """Set speaking rate in words per minute (e.g. 150 - 220) and save to DB."""
        self.rate = max(100, min(300, int(rate)))
        db.set_setting("voice_rate", self.rate)

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0) and save to DB."""
        self.volume = max(0.0, min(1.0, float(volume)))
        db.set_setting("voice_volume", self.volume)

    def set_voice_index(self, index: int) -> None:
        """Select voice by index (0 for David, 1 for Zira on Windows) and save to DB."""
        self.voice_index = max(0, int(index))
        db.set_setting("voice_index", self.voice_index)

    @staticmethod
    def get_available_voices() -> List[Dict[str, str]]:
        """
        Returns a list of available system voices for display in the UI.
        e.g. [{'id': '...', 'name': 'Microsoft David Desktop - English'}]
        """
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            result = []
            for i, v in enumerate(voices):
                result.append({
                    "index": i,
                    "id": getattr(v, "id", str(i)),
                    "name": getattr(v, "name", f"Voice #{i}")
                })
            return result
        except Exception as e:
            logging.error(f"Error querying voices: {e}")
            return [{"index": 0, "id": "default", "name": "System Default Voice"}]

    def shutdown(self) -> None:
        """Stops the worker thread cleanly upon application exit."""
        self._is_running = False
        self.stop()
        self._speech_queue.put(None)


# Singleton instance
voice = VoiceEngine()
