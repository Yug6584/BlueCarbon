# 🚀 Quick Start Guide - BlueCarbon-LEDGER

## For Windows Users

### Installation (One-time setup)
1. Double-click `INSTALL.bat`
2. Wait for installation to complete
3. Edit `.env` file and add your Groq API key

### Running the Chatbot
1. Double-click `START.bat`
2. Open browser to `http://localhost:5000`
3. Start chatting!

---

## For Mac/Linux Users

### Installation (One-time setup)
```bash
chmod +x install.sh start.sh
./install.sh
nano .env  # Add your API keys
```

### Running the Chatbot
```bash
./start.sh
```
Then open browser to `http://localhost:5000`

---

## Getting API Keys

### Groq API Key (Required - Free)
1. Go to https://console.groq.com
2. Sign up for free account
3. Click "API Keys" → "Create API Key"
4. Copy the key and paste it in `.env` file

### SerpAPI Key (Optional - For web search)
1. Go to https://serpapi.com
2. Sign up for free account (100 searches/month free)
3. Copy your API key
4. Paste it in `.env` file

---

## First Time Usage

1. **Start the server** using START.bat (Windows) or ./start.sh (Mac/Linux)
2. **Open browser** to http://localhost:5000
3. **Try these commands**:
   - "What is blue carbon?"
   - "Show me mangrove images"
   - "Explain carbon sequestration"
4. **Upload a PDF** using the 📎 button
5. **Ask questions** about your uploaded document

---

## Features to Try

✅ **Basic Chat** - Ask any blue carbon related question
✅ **PDF Upload** - Upload and analyze documents
✅ **Web Search** - Get real-time information with images
✅ **Translation** - Click 🌐 to translate any message
✅ **Chat History** - All chats are automatically saved
✅ **Delete Chats** - Hover over chat and click 🗑️

---

## Troubleshooting

**Server won't start?**
- Make sure Python is installed
- Run INSTALL.bat/install.sh again
- Check if port 5000 is available

**No responses?**
- Check your Groq API key in .env file
- Verify internet connection
- Check console for error messages

**PDF upload fails?**
- Ensure PDF is under 10MB
- Check PDF is not password protected
- Wait 30-60 seconds for processing

---

## Need Help?

Check the full README.md for detailed documentation and troubleshooting.

**Happy Chatting! 🌊**
