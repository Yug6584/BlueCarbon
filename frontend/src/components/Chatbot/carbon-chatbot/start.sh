#!/bin/bash

echo "========================================"
echo "Starting BlueCarbon-LEDGER Chatbot..."
echo "========================================"
echo ""

echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please run ./install.sh first"
    exit 1
fi

echo "Checking .env file..."
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please run ./install.sh first"
    exit 1
fi

echo ""
echo "Starting the chatbot server..."
echo ""
echo "========================================"
echo "Once started, open your browser and go to:"
echo "http://localhost:5000"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 app.py
