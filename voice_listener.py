"""
=============================================================================
MINI JARVIS - Speech Recognition Module (voice_listener.py)
=============================================================================
This module captures audio from your microphone and converts it into text
using the `SpeechRecognition` library.

Computer Science & Engineering Insights:
1. Signal Processing & Ambient Calibration:
   Microphones pick up air conditioning, fans, and room acoustics.
   `recognizer.adjust_for_ambient_noise()` samples ambient sound for 0.5s to
   set an energy threshold so background hum is filtered out.

2. Asynchronous Audio Capture:
   Speech listening is an I/O-bound blocking operation. If done directly on
   the main thread, the interface will freeze. We run it in a background
   daemon thread.

3. Graceful Error Handling:
   - WaitTimeoutError: The user was quiet or didn't speak in time.
   - UnknownValueError: Speech was too muffled or unintelligible.
   - RequestError: The speech recognition API was unreachable.
   - PyAudio/Device Errors: No microphone connected.
=============================================================================
"""

import threading
import logging
from typing import Callable, Optional
import speech_recognition as sr


class VoiceListener:
    """Manages audio capture and Speech-to-Text conversion."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Pause threshold: seconds of non-speaking audio before a phrase is considered complete
        self.recognizer.pause_threshold = 0.8
        # Dynamic energy threshold adapts to changing room noise
        self.recognizer.dynamic_energy_threshold = True

        self._is_listening = False
        self._is_continuous = False
        self._thread: Optional[threading.Thread] = None

        # Callbacks to notify UI and orchestrator
        self.on_listening_state_change: Optional[Callable[[bool], None]] = None
        self.on_text_recognized: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

    def listen_once(self, timeout: float = 5.0, phrase_time_limit: float = 10.0) -> Optional[str]:
        """
        Listens synchronously for a single phrase.
        Returns the recognized string, or None if silence/error.
        """
        try:
            with sr.Microphone() as source:
                # Calibrate for ambient noise quickly
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                if self.on_listening_state_change:
                    self.on_listening_state_change(True)

                # Listen for sound
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

                if self.on_listening_state_change:
                    self.on_listening_state_change(False)

                # Send audio to Google Speech Recognition engine
                text = self.recognizer.recognize_google(audio)
                return text

        except sr.WaitTimeoutError:
            # User simply did not speak within timeout
            return None
        except sr.UnknownValueError:
            # Noise or speech was unintelligible
            return None
        except sr.RequestError as e:
            if self.on_error:
                self.on_error("Speech recognition network service unavailable.")
            return None
        except Exception as e:
            logging.error(f"Microphone error: {e}")
            if self.on_error:
                self.on_error("Microphone access error. Please check your mic settings.")
            return None
        finally:
            if self.on_listening_state_change:
                self.on_listening_state_change(False)

    def listen_once_async(self, callback: Callable[[Optional[str]], None]) -> None:
        """Runs listen_once in a background thread so the UI never stutters."""
        def _worker():
            result = self.listen_once()
            callback(result)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def start_continuous_listening(self) -> None:
        """
        Starts a background listening loop that continuously listens
        and triggers on_text_recognized whenever a sentence is understood.
        """
        if self._is_listening:
            return

        self._is_listening = True
        self._is_continuous = True

        def _loop():
            while self._is_listening and self._is_continuous:
                recognized_text = self.listen_once(timeout=4.0, phrase_time_limit=8.0)
                if recognized_text and recognized_text.strip():
                    if self.on_text_recognized:
                        self.on_text_recognized(recognized_text.strip())

        self._thread = threading.Thread(target=_loop, daemon=True, name="ContinuousListenerThread")
        self._thread.start()

    def stop_continuous_listening(self) -> None:
        """Stops the continuous listening loop."""
        self._is_continuous = False
        self._is_listening = False
        if self.on_listening_state_change:
            self.on_listening_state_change(False)

    def is_listening(self) -> bool:
        """Returns True if the microphone is currently active."""
        return self._is_listening


# Singleton instance
listener = VoiceListener()
