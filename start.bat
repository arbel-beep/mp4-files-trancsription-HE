@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ---- one-time setup: venv + deps ----
if not exist ".venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Python not found. Install Python 3.9+ from https://python.org and re-run.
        pause
        exit /b 1
    )
    echo [setup] Installing dependencies, this can take a few minutes...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r transcription\requirements.txt
)

set PY=".venv\Scripts\python.exe"

:menu
cls
echo ============================================
echo   MP4 Transcriber (Hebrew) - launcher
echo ============================================
echo.
echo   1. Split oversized videos (ffmpeg)
echo   2. Transcribe - Local (free, slower)
echo   3. Transcribe - OpenAI API (paid, faster)
echo   4. Exit
echo.
set /p choice="Pick an option (1-4): "

if "%choice%"=="1" goto split
if "%choice%"=="2" goto local
if "%choice%"=="3" goto openai
if "%choice%"=="4" exit /b 0
goto menu

:split
set /p vfolder="Folder with videos to split: "
%PY% video-splitter\split_videos.py "%vfolder%"
pause
goto menu

:local
set /p vfolder="Folder with videos to transcribe: "
set /p model="Model (tiny/base/small/medium/large-v3) [medium]: "
if "%model%"=="" set model=medium
%PY% transcription\transcribe_local.py "%vfolder%" --model %model%
pause
goto menu

:openai
if not exist "transcription\.env" (
    echo.
    echo [setup] No transcription\.env found - it stores your OpenAI API key.
    set /p apikey="Paste your OpenAI API key (sk-...): "
    echo OPENAI_API_KEY=!apikey!> transcription\.env
    echo [setup] Saved to transcription\.env
)
set /p vfolder="Folder with videos to transcribe: "
%PY% transcription\transcribe_openai.py "%vfolder%"
pause
goto menu
