@echo off
title .oppsie TUI Dashboard
echo Launching .oppsie Image Converter TUI App...
python "%~dp0app\main.py"
if %errorlevel% neq 0 (
    echo.
    echo Application exited with an error (Code %errorlevel%^).
    echo Ensure Python is in your PATH and dependencies are installed:
    echo pip install -r requirements.txt
    pause
)
