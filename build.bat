@echo off
setlocal enabledelayedexpansion

echo ====================================
echo   BUILDING UniversalAutoTyper.exe
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

REM --- Install dependencies (app requirements + PyInstaller) ----------
echo Installing dependencies (this may take a minute)...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)

REM --- Clean previous build artifacts ----------------------------------
if exist "build\" rmdir /s /q build
if exist "dist\UniversalAutoTyper.exe" del /q "dist\UniversalAutoTyper.exe"
if exist "UniversalAutoTyper.spec" del /q "UniversalAutoTyper.spec"

REM --- Build the standalone EXE -----------------------------------------
echo.
echo Building standalone application...
echo.
REM Called via "python -m PyInstaller" rather than the bare "pyinstaller"
REM command, since pip can install its scripts into a folder that isn't
REM on PATH (harmless warning during the pip install step above) - this
REM way works regardless of PATH.
python -m PyInstaller --noconfirm --onefile --windowed --name UniversalAutoTyper local_app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed. See the output above for details.
    pause
    exit /b 1
)

echo.
echo ====================================
echo   BUILD COMPLETE
echo ====================================
echo.
echo Your standalone app is ready at:
echo dist\UniversalAutoTyper.exe
echo.
echo You can copy this single .exe anywhere and double-click it directly
echo - no project folder, terminal, or run.bat required.
echo.
pause