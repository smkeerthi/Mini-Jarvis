"""
=============================================================================
MINI JARVIS - System Diagnostics & Self-Test Suite (test_system.py)
=============================================================================
Run this script to verify that every subsystem in Mini Jarvis is working:
    python test_system.py
=============================================================================
"""

import sys
import time

def test_component(name: str, test_func):
    print(f"Testing {name.ljust(35)} ... ", end="", flush=True)
    try:
        result = test_func()
        print(f"[  OK  ] -> {result}")
        return True
    except Exception as e:
        print(f"[ FAILED ] -> {e}")
        return False


def test_database():
    from database import db
    # Test setting
    db.set_setting("diagnostic_test", "passed")
    val = db.get_setting("diagnostic_test")
    assert val == "passed"

    # Test todo
    tid = db.add_todo("Test task")
    assert tid > 0
    db.delete_todo(tid)

    # Test note
    nid = db.add_note("Test content", "Diagnostic Note")
    assert nid > 0
    db.delete_note(nid)

    return "SQLite Database CRUD operational"


def test_commands():
    from assistant_commands import commands
    # Time
    time_resp = commands.handle_command("what time is it")
    assert "time" in time_resp.lower()

    # Math
    math_resp = commands.handle_command("calculate 12 * 8")
    assert "96" in math_resp

    # Diagnostics
    diag_resp = commands.handle_command("system diagnostics")
    assert "cpu" in diag_resp.lower()

    return "Intent parser & AST math evaluator operational"


def test_brain():
    from brain import brain
    resp = brain.ask("explain recursion")
    assert len(resp) > 20
    return "Cognitive brain responder operational"


def test_voice_engine():
    from voice_engine import voice
    voices = voice.get_available_voices()
    return f"pyttsx3 ready with {len(voices)} voices (Default: {voices[0]['name']})"


def test_speech_recognition():
    import speech_recognition as sr
    mics = sr.Microphone.list_microphone_names()
    return f"PyAudio & SpeechRecognition detected {len(mics)} audio endpoints"


def test_vision():
    import cv2
    from vision import vision
    has_detector = vision._detector is not None
    return f"OpenCV v{cv2.__version__} with YuNet face detector {'[ACTIVE]' if has_detector else '[STANDBY]'}"


def test_gui():
    import customtkinter as ctk
    return f"CustomTkinter v{ctk.__version__} loaded successfully"


def main():
    print("=" * 65)
    print("       MINI JARVIS - SYSTEM DIAGNOSTIC REPORT")
    print("=" * 65)

    tests = [
        ("SQLite Memory & Settings", test_database),
        ("Assistant Commands & Safe Math", test_commands),
        ("Cognitive Brain & Reasoning", test_brain),
        ("Speech Synthesis (pyttsx3)", test_voice_engine),
        ("Audio Input (SpeechRecognition)", test_speech_recognition),
        ("Computer Vision (OpenCV)", test_vision),
        ("Desktop Dashboard (CustomTkinter)", test_gui),
    ]

    passed = 0
    for name, func in tests:
        if test_component(name, func):
            passed += 1

    print("=" * 65)
    print(f"Results: {passed}/{len(tests)} subsystems passed.")
    if passed == len(tests):
        print("ALL SYSTEMS GREEN! Mini Jarvis is ready for launch.")
        print("Run 'python main.py' to open the futuristic dashboard!")
    print("=" * 65)


if __name__ == "__main__":
    main()
