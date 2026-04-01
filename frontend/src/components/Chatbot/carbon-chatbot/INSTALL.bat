@echo off
echo ========================================
echo BlueCarbon-LEDGER Installation Script
echo ========================================
echo.

echo Step 1: Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please install Python 3.8 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)
echo Python found!
echo.

echo Step 2: Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)
echo Dependencies installed successfully!
echo.

echo Step 3: Checking .env file...
if not exist .env (
    echo WARNING: .env file not found!
    echo Creating .env file from template...
    (
        echo # BlueCarbon-LEDGER Configuration
        echo.
        echo # Required: Groq AI API Key ^(Get from https://console.groq.com^)
        echo GROQ_API_KEY=your_groq_api_key_here
        echo.
        echo # Optional: SerpAPI Key for web search ^(Get from https://serpapi.com^)
        echo SERPAPI_KEY=your_serpapi_key_here
        echo.
        echo # Optional: LibreTranslate URL
        echo LIBRETRANSLATE_URL=https://libretranslate.com
    ) > .env
    echo .env file created! Please edit it and add your API keys.
    echo.
)
echo.

echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit the .env file and add your API keys
echo 2. Run START.bat to start the chatbot
echo.
pause
