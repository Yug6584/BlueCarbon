@echo off
echo ========================================
echo Starting BlueCarbon-LEDGER Chatbot...
echo ========================================
echo.

echo Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please run INSTALL.bat first
    pause
    exit /b 1
)

echo Checking .env file...
if not exist .env (
    echo ERROR: .env file not found!
    echo Please run INSTALL.bat first
    pause
    exit /b 1
)

echo.
echo Starting the chatbot server...
echo.
echo ========================================
echo Once started, open your browser and go to:
echo http://localhost:5000
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

python app.py

pause
