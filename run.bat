@echo off
title MINI JARVIS - Personal AI Assistant
cls
echo ===================================================
echo       INITIALIZING MINI JARVIS PROTOCOLS
echo ===================================================
echo Checking Python environment...
python --version
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b
)

echo Starting Mini Jarvis Desktop HUD...
python main.py
if errorlevel 1 (
    echo.
    echo [NOTICE] Application terminated with an error code.
    pause
)
