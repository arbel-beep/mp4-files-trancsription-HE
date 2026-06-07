@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ---- auto-install missing tools (skips anything already present) ----
set NEEDS_RESTART=0

REM "where python" can find Windows' Store-alias stub even with no real
REM Python installed, so actually run it (and the "py" launcher) to check.
set PYLAUNCHER=
python --version >nul 2>nul
if not errorlevel 1 set PYLAUNCHER=python
if not defined PYLAUNCHER (
    py -3 --version >nul 2>nul
    if not errorlevel 1 set PYLAUNCHER=py -3
)

if not defined PYLAUNCHER (
    echo [setup] Python not found - installing via winget...
    winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [ERROR] Could not install Python automatically. Install it from https://python.org and re-run.
        pause
        exit /b 1
    )
    set NEEDS_RESTART=1
) else (
    echo [setup] Python found - skipping.
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo [setup] ffmpeg not found - installing via winget...
    winget install -e --id Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo [ERROR] Could not install ffmpeg automatically. Install it from https://ffmpeg.org/download.html and re-run.
        pause
        exit /b 1
    )
    set NEEDS_RESTART=1
) else (
    echo [setup] ffmpeg found - skipping.
)

if "%NEEDS_RESTART%"=="1" (
    echo.
    echo [setup] Newly installed tools need a fresh terminal to be on PATH.
    echo [setup] Close this window and double-click start.bat again to continue.
    pause
    exit /b 0
)

REM ---- one-time setup: venv + deps (skips if venv already exists) ----
if not exist ".venv\Scripts\python.exe" (
    echo [setup] Creating virtual environment...
    %PYLAUNCHER% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Could not create the virtual environment with "%PYLAUNCHER%".
        echo [ERROR] Make sure Python 3.9+ is installed from https://python.org and re-run.
        pause
        exit /b 1
    )
    echo [setup] Installing dependencies, this can take a few minutes...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r transcription\requirements.txt
) else (
    echo [setup] Virtual environment found - skipping setup.
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
