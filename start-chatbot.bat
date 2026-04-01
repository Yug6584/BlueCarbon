@echo off
echo ========================================
echo  Starting BlueCarbon AI Chatbot
echo ========================================
echo.

cd frontend\src\components\Chatbot\carbon-chatbot

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo ========================================
echo  Starting Chatbot Server on Port 5000
echo ========================================
echo.
echo Access the chatbot at: http://localhost:5000
echo The floating chatbot icon will appear in Company Panel
echo.

python app.py

pause
