@echo off
setlocal enabledelayedexpansion

echo ====================================
echo        UNIVERSAL AUTO TYPER
echo ====================================
echo.

REM --- Check Python is installed ------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on this computer.
    echo Please install Python 3.x from https://www.python.org/downloads/
    echo and make sure "Add Python to PATH" is checked during setup.
    echo.
    pause
    exit /b 1
)

REM --- Create virtual environment if it does not exist ---------------
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create the virtual environment.
        pause
        exit /b 1
    )
)

REM --- Activate virtual environment -----------------------------------
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate the virtual environment.
    pause
    exit /b 1
)

REM --- Install dependencies -------------------------------------------
echo Installing dependencies (this may take a minute the first time)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM --- Start the app ----------------------------------------------------
echo.
echo Starting application...
echo.
echo Local URL:
echo http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server.
echo.

python app.py

pause
