# 🤖 BlueCarbon AI Chatbot Integration

## ✨ Features

The floating AI chatbot is now integrated into the **Company Panel** with the following features:

- 🎯 **Floating Icon**: Always accessible from bottom-right corner
- 💬 **Smart Conversations**: AI-powered responses about blue carbon
- 📄 **PDF Upload**: Upload and analyze documents
- 🌐 **Web Search**: Real-time information retrieval
- 🖼️ **Image Support**: Visual responses when relevant
- 🌍 **Multi-Language**: Support for 50+ languages
- 💾 **Chat History**: Persistent conversation sessions

## 🚀 Quick Start

### Step 1: Start the Chatbot Service

**Option A: Using the batch file (Windows)**
```bash
start-chatbot.bat
```

**Option B: Manual start**
```bash
cd frontend/src/components/Chatbot/carbon-chatbot
python app.py
```

### Step 2: Configure API Keys (First Time Only)

1. Open `frontend/src/components/Chatbot/carbon-chatbot/.env`
2. Add your API keys:

```env
# Required: Groq AI API Key (Free at https://console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# Optional: SerpAPI Key for web search (Free tier at https://serpapi.com)
SERPAPI_KEY=your_serpapi_key_here
```

**Get API Keys:**
- **Groq API**: Visit https://console.groq.com → Sign up → Get API key (Free)
- **SerpAPI**: Visit https://serpapi.com → Sign up → Get API key (100 free searches/month)

### Step 3: Use the Chatbot

1. Login to the **Company Panel** (yugcompany@gmail.com)
2. Look for the **purple chat icon** in the bottom-right corner
3. Click to open the chatbot
4. Start asking questions!

## 📍 Where to Find It

The floating chatbot appears on **ALL Company Panel pages**:
- ✅ Dashboard
- ✅ Project Management
- ✅ MRV Upload
- ✅ GIS Mapping
- ✅ Marketplace
- ✅ Credit Trading
- ✅ Government Schemes

## 💡 Example Questions

Try asking:
- "How do I calculate carbon credits for my mangrove project?"
- "What are the requirements for blue carbon certification?"
- "Show me the blue carbon cycle"
- "Explain MRV process for seagrass restoration"
- "What documents do I need for project submission?"

## 🎨 Chatbot Features

### 1. Smart Responses
- Context-aware answers about blue carbon
- Cites sources when available
- Provides relevant images automatically

### 2. PDF Analysis
- Click the 📎 icon to upload PDFs
- Ask questions about uploaded documents
- Supports project reports, research papers, etc.

### 3. Status Indicator
- 🟢 **Green**: Chatbot is online and ready
- 🔴 **Red**: Chatbot service is offline (start it using the batch file)

### 4. Chat Management
- 🔄 **New Chat**: Start fresh conversation
- 💬 **History**: All chats are automatically saved
- ❌ **Close**: Minimize the chat window

## 🛠️ Troubleshooting

### Chatbot shows "Offline"
**Solution**: Start the chatbot service
```bash
cd frontend/src/components/Chatbot/carbon-chatbot
python app.py
```

### "Module not found" error
**Solution**: Install dependencies
```bash
cd frontend/src/components/Chatbot/carbon-chatbot
pip install -r requirements.txt
```

### Port 5000 already in use
**Solution**: Change the port in `config.py`
```python
PORT = 5001  # Change to any available port
```
Then update the port in `frontend/src/components/FloatingChatbot.jsx`:
```javascript
const CHATBOT_API_URL = 'http://localhost:5001';
```

### API Key errors
**Solution**: 
1. Get a free API key from https://console.groq.com
2. Add it to `.env` file in the carbon-chatbot folder
3. Restart the chatbot service

## 📁 File Locations

- **Chatbot Component**: `frontend/src/components/FloatingChatbot.jsx`
- **Chatbot Service**: `frontend/src/components/Chatbot/carbon-chatbot/`
- **Configuration**: `frontend/src/components/Chatbot/carbon-chatbot/.env`
- **Start Script**: `start-chatbot.bat` (in project root)

## 🔧 Customization

### Change Chatbot Appearance

Edit `frontend/src/components/FloatingChatbot.jsx`:

```javascript
// Change colors
background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'

// Change position
bottom: 24,  // Distance from bottom
right: 24,   // Distance from right

// Change size
width: 400,  // Chat window width
height: 600, // Chat window height
```

### Add to Other Panels

To add the chatbot to Government or Admin panels:

1. Open the panel file (e.g., `GovernmentPanel.jsx`)
2. Import the component:
```javascript
import FloatingChatbot from '../../components/FloatingChatbot';
```
3. Add it to the return statement:
```javascript
return (
  <>
    <Layout>...</Layout>
    <FloatingChatbot />
  </>
);
```

## 🌟 Advanced Features

### Custom Welcome Message
Edit the welcome message in `FloatingChatbot.jsx`:
```javascript
text: 'Your custom welcome message here...'
```

### Add Custom Endpoints
The chatbot connects to these endpoints:
- `POST /chat` - Send messages
- `POST /upload` - Upload PDFs
- `GET /health` - Check status

You can extend the chatbot service by adding more endpoints in `app.py`.

## 📊 Monitoring

The chatbot service logs all interactions. Check the console where you started `python app.py` to see:
- Incoming questions
- API calls
- Processing time
- Errors

## 🎉 You're All Set!

The floating AI chatbot is now integrated and ready to assist users in the Company Panel. Start the service and enjoy intelligent assistance for all blue carbon related queries!

---

**Need Help?** Check the main chatbot README at:
`frontend/src/components/Chatbot/carbon-chatbot/README.md`
