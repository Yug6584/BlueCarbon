#!/bin/bash

echo "========================================"
echo "BlueCarbon-LEDGER Installation Script"
echo "========================================"
echo ""

echo "Step 1: Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.8 or higher"
    exit 1
fi
echo "Python found: $(python3 --version)"
echo ""

echo "Step 2: Installing dependencies..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies!"
    exit 1
fi
echo "Dependencies installed successfully!"
echo ""

echo "Step 3: Checking .env file..."
if [ ! -f .env ]; then
    echo "WARNING: .env file not found!"
    echo "Creating .env file from template..."
    cat > .env << 'EOF'
# BlueCarbon-LEDGER Configuration

# Required: Groq AI API Key (Get from https://console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# Optional: SerpAPI Key for web search (Get from https://serpapi.com)
SERPAPI_KEY=your_serpapi_key_here

# Optional: LibreTranslate URL
LIBRETRANSLATE_URL=https://libretranslate.com
EOF
    echo ".env file created! Please edit it and add your API keys."
    echo ""
fi

echo "========================================"
echo "Installation Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Edit the .env file and add your API keys:"
echo "   nano .env"
echo "2. Run ./start.sh to start the chatbot"
echo ""
