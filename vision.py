"""
=============================================================================
MINI JARVIS - Computer Vision & Tactical HUD Module (vision.py)
=============================================================================
This module integrates OpenCV to provide Mini Jarvis with optical vision.

Features:
1. Real-Time Camera Stream:
   Captures video frames from the webcam in a dedicated background thread.
2. AI Face Detection:
   Uses OpenCV's deep-learning YuNet model (`FaceDetectorYN`) to detect
   human faces and facial landmarks in real time.
3. Stark Industries Tactical HUD (Heads-Up Display):
   Overlays futuristic glowing cyan targeting reticles, lock-on brackets,
   crosshairs, telemetry coordinates, and status readouts.
4. UI Bridge:
   Converts OpenCV BGR frames to RGB / PIL Images for display in CustomTkinter.
=============================================================================
"""

import os
import time
import threading
import logging
from typing import Optional, Callable
import cv2
import numpy as np
from PIL import Image

from config import BASE_DIR

YUNET_MODEL_PATH = os.path.join(BASE_DIR, "assets", "face_detection_yunet_2023mar.onnx")


class VisionEngine:
    """Manages webcam capture, neural face detection, and tactical HUD rendering."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._detector = None
        self.frame_callback: Optional[Callable[[Image.Image], None]] = None

        self._init_detector()

    def _init_detector(self) -> None:
        """Initializes the modern OpenCV YuNet Deep Learning Face Detector."""
        if os.path.exists(YUNET_MODEL_PATH):
            try:
                self._detector = cv2.FaceDetectorYN.create(
                    model=YUNET_MODEL_PATH,
                    config="",
                    input_size=(320, 240),
                    score_threshold=0.6,
                    nms_threshold=0.3,
                    top_k=10
                )
            except Exception as e:
                logging.warning(f"Could not initialize YuNet face detector: {e}")
                self._detector = None

    def start(self, callback: Optional[Callable[[Image.Image], None]] = None) -> bool:
        """Starts video capture in a background thread."""
        if self._is_running:
            return True

        if callback:
            self.frame_callback = callback

        self._is_running = True
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="JarvisVisionThread",
            daemon=True
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        """Stops the camera stream."""
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def is_running(self) -> bool:
        """Returns True if the vision system is currently streaming."""
        return self._is_running

    def _capture_loop(self) -> None:
        """Background video capture and overlay loop."""
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            # Try default backend if DirectShow is not supported
            cap = cv2.VideoCapture(self.camera_index)

        if not cap.isOpened():
            logging.error("Failed to open webcam.")
            self._is_running = False
            return

        # Optimize resolution for low latency
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        prev_time = time.time()

        while self._is_running:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            # Mirror frame horizontally for natural webcam feel
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]

            # Calculate FPS
            curr_time = time.time()
            fps = 1.0 / max(curr_time - prev_time, 0.001)
            prev_time = curr_time

            # 1. Neural Face Detection
            faces_detected = 0
            if self._detector:
                try:
                    self._detector.setInputSize((w, h))
                    _, faces = self._detector.detect(frame)
                    if faces is not None:
                        faces_detected = len(faces)
                        for face in faces:
                            # Box coordinates
                            bx, by, bw, bh = map(int, face[:4])
                            self._draw_tactical_bracket(frame, bx, by, bw, bh)
                except Exception as e:
                    logging.debug(f"Detection step error: {e}")

            # 2. Render Futuristic HUD Overlay
            self._draw_hud_overlay(frame, fps, faces_detected)

            # Convert to PIL Image for CustomTkinter
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)

            if self.frame_callback:
                try:
                    self.frame_callback(pil_img)
                except Exception:
                    pass

            time.sleep(0.02)  # Cap loop at ~40 FPS

        cap.release()

    def _draw_tactical_bracket(self, frame: np.ndarray, x: int, y: int, w: int, h: int) -> None:
        """Draws Iron Man lock-on targeting brackets around a detected face."""
        cyan = (255, 210, 0)      # BGR for Stark Cyan
        gold = (0, 215, 255)      # BGR for Gold
        corner_len = max(15, int(w * 0.2))

        # Top-Left corner
        cv2.line(frame, (x, y), (x + corner_len, y), cyan, 2)
        cv2.line(frame, (x, y), (x, y + corner_len), cyan, 2)

        # Top-Right corner
        cv2.line(frame, (x + w, y), (x + w - corner_len, y), cyan, 2)
        cv2.line(frame, (x + w, y), (x + w, y + corner_len), cyan, 2)

        # Bottom-Left corner
        cv2.line(frame, (x, y + h), (x + corner_len, y + h), cyan, 2)
        cv2.line(frame, (x, y + h), (x, y + h - corner_len), cyan, 2)

        # Bottom-Right corner
        cv2.line(frame, (x + w, y + h), (x + w - corner_len, y + h), cyan, 2)
        cv2.line(frame, (x + w, y + h), (x + w, y + h - corner_len), cyan, 2)

        # Tactical Label
        cv2.putText(
            frame,
            "[ TARGET LOCKED ]",
            (x, max(15, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            gold,
            1,
            cv2.LINE_AA
        )

    def _draw_hud_overlay(self, frame: np.ndarray, fps: float, faces: int) -> None:
        """Draws telemetry info, crosshairs, and holographic headers."""
        h, w = frame.shape[:2]
        cyan = (255, 210, 0)  # BGR
        dim_cyan = (150, 100, 0)

        # Center Crosshair
        cx, cy = w // 2, h // 2
        cv2.circle(frame, (cx, cy), 28, dim_cyan, 1)
        cv2.line(frame, (cx - 40, cy), (cx - 10, cy), cyan, 1)
        cv2.line(frame, (cx + 10, cy), (cx + 40, cy), cyan, 1)
        cv2.line(frame, (cx, cy - 40), (cx, cy - 10), cyan, 1)
        cv2.line(frame, (cx, cy + 10), (cx, cy + 40), cyan, 1)

        # Top Header Telemetry
        cv2.putText(
            frame,
            "JARVIS TACTICAL OPTICS v2.0",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            cyan,
            1,
            cv2.LINE_AA
        )

        status_str = f"STATUS: TRACKING | TARGETS: {faces} | FPS: {fps:.1f}"
        cv2.putText(
            frame,
            status_str,
            (20, 52),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            dim_cyan,
            1,
            cv2.LINE_AA
        )

        # Bottom Border Timestamp
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(
            frame,
            f"SYSTEM TIME: {ts}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            dim_cyan,
            1,
            cv2.LINE_AA
        )


# Singleton instance
vision = VisionEngine()
