@echo off
title EquipmentHealth - Install Dependencies
color 0B

echo ===============================================================================
echo       RS-380 INDUSTRIAL MOTOR SCADA - DEPENDENCY INSTALLATION WIZARD
echo ===============================================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PY_VER=%%i
echo [*] Found: %PY_VER%
echo [*] Upgrading pip and installing requirements...
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    color 0C
    echo.
    echo [ERROR] One or more dependencies failed to install.
    echo Please verify your internet connection.
    pause
    exit /b 1
)

echo.
echo ===============================================================================
echo [SUCCESS] All libraries and dependencies have been installed successfully!
echo You can now double-click "START_SYSTEM.bat" to run the project.
echo ===============================================================================
echo.
pause
