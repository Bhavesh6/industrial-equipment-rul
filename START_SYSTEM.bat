@echo off
title EquipmentHealth RS-380 SCADA & RUL Prognostics
color 0B

echo ===============================================================================
echo       RS-380 INDUSTRIAL MOTOR DIGITAL TWIN ^& RUL PROGNOSTICS SCADA
echo ===============================================================================
echo.

:: 1. Security Authorization Gate (SHA-256 Cryptographic Hash Check)
echo -------------------------------------------------------------------------------
echo   [SECURITY ACCESS GATE]
echo   This software is proprietary property of Bhavesh.
echo -------------------------------------------------------------------------------
set /p ENTERED_PIN="Enter Authorized Security PIN to launch: "
python -c "import hashlib, sys; sys.exit(0 if hashlib.sha256('%ENTERED_PIN%'.encode()).hexdigest() == 'd54f809b260c113249010badffefde4bf0565be9603ad6de383864d8c83b1bcf' else 1)"
if errorlevel 1 (
    color 0C
    echo.
    echo ===============================================================================
    echo [ACCESS DENIED] Invalid Authorization PIN!
    echo Unauthorized access attempt logged. Exiting...
    echo ===============================================================================
    pause
    exit /b 1
)
color 0A
echo.
echo [ACCESS GRANTED] Security PIN verified. Initializing system...
echo.

:: 2. Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please install Python 3.10, 3.11, or 3.12 from:
    echo    https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PY_VER=%%i
echo [*] Detected: %PY_VER%

:: 3. Check and verify core dependencies
echo [*] Verifying system dependencies...
python -c "import pandas, sklearn, joblib, serial, dotenv, requests" >nul 2>&1
if errorlevel 1 (
    echo [!] Missing required dependencies. Installing automatically from requirements.txt...
    echo [*] Running: pip install -r requirements.txt
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        color 0C
        echo [ERROR] Failed to install dependencies. Please check your internet connection.
        pause
        exit /b 1
    )
    echo [OK] All dependencies successfully installed!
) else (
    echo [OK] All dependencies verified!
)

:: 4. Launch the Web Browser after 2 seconds in background
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000"

:: 5. Start the SCADA Server & Motor Telemetry Engine
echo.
echo ===============================================================================
echo   SCADA Server is starting on http://localhost:8000
echo   Hardware bridge active (COM5 Serial + Wi-Fi UDP 8888)
echo   Press Ctrl+C at any time in this window to stop the system.
echo ===============================================================================
echo.

python dashboard/serve.py 8000

if errorlevel 1 (
    color 0C
    echo.
    echo [ERROR] Server terminated unexpectedly.
    pause
)
