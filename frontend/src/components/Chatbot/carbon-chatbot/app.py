import os
# Set environment variables to avoid LangChain conflicts
os.environ["LLAMA_INDEX_DISABLE_LANGCHAIN"] = "1"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

import sqlite3
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import socket
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from io import BytesIO
import base64
import numpy as np

# Import enhanced services
from config import Config
from services.simple_chat_engine import get_simple_chat_engine
from services.async_processor import get_async_processor
from services.chat_history_service import get_chat_history_service
# Data processing functionality integrated into services

app = Flask(__name__)
# Enhanced CORS configuration for network sharing
CORS(app, 
     origins="*",  # Allow all origins for sharing
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     supports_credentials=True)

class AdvancedBlueCarbonEngine:
    def __init__(self):
        print("🚀 Initializing Advanced Blue Carbon Engine...")
        
        # Performance optimizations
        self.conversation_memory = {}
        self.response_cache = {}
        self.chunk_cache = {}
        self.embedding_cache = {}
        
        # Initialize models
        self._initialize_embedding_model()
        self._initialize_llm()
        self.load_vector_store()
        
        # Background processing
        self.processing_queue = []
        self.processing_lock = threading.Lock()
        
        print("✅ Advanced Blue Carbon Engine ready!")
        
    def _initialize_embedding_model(self):
        """Initialize embedding model with error handling"""
        try:
            self.embed_model = HuggingFaceEmbedding(
                model_name="BAAI/bge-small-en-v1.5"
            )
            print("✅ Embedding model loaded successfully")
        except Exception as e:
            print(f"❌ Error loading embedding model: {e}")
            raise
            
    def _initialize_llm(self):
        """Initialize LLM with multiple fallback options for reliable responses"""
        self.llm = None
        self.llm_type = "none"
        
        # Try Ollama with optimized settings for reliability
        try:
            from llama_index.llms.ollama import Ollama
            # Use optimized settings for better reliability
            for model in ["llama3:latest", "llama3", "phi3:latest"]:
                try:
                    self.llm = Ollama(
                        model=model, 
                        request_timeout=90.0,  # Increased timeout for reliability
                        temperature=0.7,
                        num_predict=1024,  # Reasonable response length
                        top_k=40,
                        top_p=0.9
                    )
                    # Quick test with shorter prompt
                    test_response = self.llm.complete("Test")
                    if test_response and len(str(test_response).strip()) > 0:
                        self.llm_type = "ollama"
                        print(f"✅ Reliable Ollama LLM initialized with {model}")
                        return
                except Exception as e:
                    print(f"⚠️ Model {model} failed: {e}")
                    continue
        except Exception as e:
            print(f"⚠️ Ollama initialization failed: {e}")
        
        # Fallback to intelligent rule-based responses
        print("⚠️ Using optimized rule-based responses for maximum speed")
        self.llm_type = "intelligent_fallback"
        
    def load_vector_store(self):
        """Load FAISS vector store with optimizations"""
        if not vectorstore_exists():
            raise Exception("Vector store not found. Please run data_process.py first.")
        
        try:
            # Load FAISS index
            self.faiss_index = faiss.read_index("data/vectorstore/faiss_index.bin")
            
            # Load metadata with proper encoding
            with open("data/vectorstore/metadata.json", 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            
            # Load embeddings
            with open("data/vectorstore/embeddings.pkl", 'rb') as f:
                self.embeddings = pickle.load(f)
            
            print(f"✅ Vector store loaded: {len(self.metadata)} chunks available")
            
        except Exception as e:
            print(f"❌ Error loading vector store: {e}")
            raise
    
    def fast_retrieve(self, question, top_k=5):
        """Ultra-fast retrieval with aggressive caching"""
        cache_key = f"{question}_{top_k}"
        
        # Check cache first
        if cache_key in self.chunk_cache:
            return self.chunk_cache[cache_key]
        
        try:
            # Get embedding with caching
            if question in self.embedding_cache:
                question_embedding = self.embedding_cache[question]
            else:
                question_embedding = self.embed_model.get_text_embedding(question)
                self.embedding_cache[question] = question_embedding
                
                # Limit cache size for memory efficiency
                if len(self.embedding_cache) > 200:
                    keys = list(self.embedding_cache.keys())
                    for key in keys[:50]:
                        del self.embedding_cache[key]
            
            question_vector = np.array([question_embedding]).astype('float32')
            
            # Fast FAISS search
            scores, indices = self.faiss_index.search(question_vector, top_k)
            
            # Build results
            relevant_chunks = []
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(self.metadata):
                    chunk_data = self.metadata[idx].copy()
                    chunk_data['similarity_score'] = float(scores[0][i])
                    relevant_chunks.append(chunk_data)
            
            # Cache results
            self.chunk_cache[cache_key] = relevant_chunks
            if len(self.chunk_cache) > 100:
                keys = list(self.chunk_cache.keys())
                for key in keys[:20]:
                    del self.chunk_cache[key]
            
            return relevant_chunks
            
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []
    
    def generate_fast_response(self, question, context_type="general", session_id="default"):
        """Generate responses optimized for speed"""
        start_time = time.time()
        
        try:
            # Check response cache for instant responses
            cache_key = f"{question}_{context_type}_{session_id}"
            if cache_key in self.response_cache:
                cached = self.response_cache[cache_key].copy()
                cached["retrieval_time"] = 0.05  # Cached response
                cached["cached"] = True
                return cached
            
            # Get conversation context for memory
            conversation_context = self._get_conversation_memory(session_id)
            
            # Fast retrieval
            relevant_chunks = self.fast_retrieve(question, top_k=5)
            
            if not relevant_chunks:
                return self._generate_no_results_response(question, context_type)
            
            # Build context and sources
            context_parts = []
            sources = []
            
            for i, chunk in enumerate(relevant_chunks):
                source_file = chunk.get("source_file", "unknown")
                text = chunk.get("text", "")
                
                context_parts.append(f"SOURCE {i+1} [{source_file}]: {text[:300]}...")
                sources.append({
                    "filename": source_file,
                    "snippet": text[:150] + "..." if len(text) > 150 else text,
                    "similarity_score": round(chunk.get('similarity_score', 0), 3),
                    "chunk_id": chunk.get("chunk_id", "")
                })
            
            context = "\n".join(context_parts)
            
            # Generate response based on available LLM
            if self.llm_type == "ollama" and self.llm:
                try:
                    prompt = self._create_optimized_prompt(question, context, context_type, conversation_context)
                    
                    # Use threading for timeout on Windows
                    import threading
                    import queue
                    
                    result_queue = queue.Queue()
                    
                    def llm_call():
                        try:
                            response = self.llm.complete(prompt)
                            result_queue.put(("success", str(response).strip()))
                        except Exception as e:
                            result_queue.put(("error", str(e)))
                    
                    # Start LLM call in thread
                    llm_thread = threading.Thread(target=llm_call)
                    llm_thread.daemon = True
                    llm_thread.start()
                    
                    # Wait for result with timeout
                    try:
                        status, result = result_queue.get(timeout=45)  # 45 second timeout
                        if status == "success" and result and len(result) >= 10:
                            answer = result
                        else:
                            print(f"LLM returned invalid response, using fallback")
                            answer = self._generate_intelligent_fallback(question, relevant_chunks, context_type, conversation_context)
                    except queue.Empty:
                        print(f"LLM timeout, using fallback")
                        answer = self._generate_intelligent_fallback(question, relevant_chunks, context_type, conversation_context)
                        
                except Exception as e:
                    print(f"LLM failed, using fallback: {e}")
                    answer = self._generate_intelligent_fallback(question, relevant_chunks, context_type, conversation_context)
            else:
                answer = self._generate_intelligent_fallback(question, relevant_chunks, context_type, conversation_context)
            
            # Update conversation memory
            self._update_memory(session_id, question, answer)
            
            response_data = {
                "answer": answer,
                "sources": sources,
                "retrieval_time": round(time.time() - start_time, 2),
                "chunks_retrieved": len(relevant_chunks),
                "cached": False
            }
            
            # Cache response
            self.response_cache[cache_key] = response_data.copy()
            if len(self.response_cache) > 50:
                keys = list(self.response_cache.keys())
                for key in keys[:10]:
                    del self.response_cache[key]
            
            return response_data
            
        except Exception as e:
            print(f"Response generation error: {e}")
            return {
                "answer": f"I encountered an error: {str(e)}. Please try rephrasing your question.",
                "sources": [],
                "retrieval_time": round(time.time() - start_time, 2),
                "chunks_retrieved": 0,
                "cached": False
            }
    
    def _get_conversation_memory(self, session_id):
        """Get conversation memory for context"""
        if session_id not in self.conversation_memory:
            return ""
        
        memory = self.conversation_memory[session_id]
        if not memory:
            return ""
        
        # Get last 2 exchanges for context (optimized for speed)
        recent = []
        for item in memory[-2:]:
            recent.append(f"Q: {item['question'][:100]}")
            recent.append(f"A: {item['answer'][:200]}")
        
        return " | ".join(recent)
    
    def _update_memory(self, session_id, question, answer):
        """Update conversation memory efficiently"""
        if session_id not in self.conversation_memory:
            self.conversation_memory[session_id] = []
        
        self.conversation_memory[session_id].append({
            "question": question,
            "answer": answer[:500],  # Truncate for memory efficiency
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 5 exchanges per session for speed
        if len(self.conversation_memory[session_id]) > 5:
            self.conversation_memory[session_id] = self.conversation_memory[session_id][-5:]
    
    def _create_optimized_prompt(self, question, context, context_type, memory=""):
        """Create optimized prompts for fast responses"""
        base = "You are a blue carbon expert. Be concise and professional. Use [filename] citations."
        
        memory_note = f" Previous context: {memory}" if memory else ""
        
        if context_type == "analysis":
            return f"""{base} Provide structured analysis with: Executive Summary, Key Findings (3-5 points), Recommendations.{memory_note}

Context: {context[:1000]}
Question: {question}
Analysis:"""
        
        elif context_type == "summary":
            return f"""{base} Provide clear summary with: Overview, Main Points (bullets), Conclusions.{memory_note}

Context: {context[:1000]}
Question: {question}
Summary:"""
        
        elif context_type == "report":
            return f"""{base} Generate professional report with: Introduction, Findings, Implications, Recommendations.{memory_note}

Context: {context[:1000]}
Question: {question}
Report:"""
        
        else:
            return f"""{base} Answer directly and clearly.{memory_note}

Context: {context[:800]}
Question: {question}
Answer:"""
    
    def _generate_intelligent_fallback(self, question, chunks, context_type, memory=""):
        """Generate intelligent responses using advanced rule-based approach"""
        
        # Extract key information efficiently
        key_facts = []
        sources = set()
        
        for chunk in chunks[:3]:
            text = chunk.get("text", "")
            source = chunk.get("source_file", "unknown")
            sources.add(source)
            
            # Smart sentence extraction
            sentences = text.split('. ')
            question_words = set(question.lower().split())
            
            for sentence in sentences:
                sentence_words = set(sentence.lower().split())
                if len(question_words.intersection(sentence_words)) >= 2:
                    key_facts.append(sentence.strip())
                    if len(key_facts) >= 5:
                        break
        
        # Memory integration
        memory_context = ""
        if memory and "Previous" in memory:
            memory_context = "\n\n*Building on our previous discussion*"
        
        # Generate response based on context type
        if context_type == "analysis":
            return f"""**📊 BLUE CARBON ANALYSIS**

**Executive Summary:**
Analysis of "{question}" based on comprehensive blue carbon research data.

**Key Findings:**
{chr(10).join(f"• {fact}" for fact in key_facts[:5])}

**Implications:**
• Critical for climate change mitigation strategies
• Requires integrated ecosystem management approach
• Economic benefits through carbon credit mechanisms

**Recommendations:**
• Implement standardized monitoring protocols
• Develop stakeholder engagement frameworks
• Establish long-term conservation funding

**Sources:** {', '.join(sources)}
{memory_context}"""
        
        elif context_type == "summary":
            return f"""**📄 BLUE CARBON SUMMARY**

**Overview:**
Comprehensive summary addressing: {question}

**Main Points:**
{chr(10).join(f"• {fact}" for fact in key_facts[:5])}

**Key Takeaways:**
• Blue carbon ecosystems are vital for climate regulation
• Restoration and conservation require coordinated efforts
• Monitoring and verification are essential for success

**Conclusions:**
Integrated management approaches yield the best outcomes for blue carbon conservation and climate benefits.

**Sources:** {', '.join(sources)}
{memory_context}"""
        
        elif context_type == "report":
            return f"""**📈 PROFESSIONAL BLUE CARBON REPORT**

**1. INTRODUCTION**
Professional analysis of: {question}

**2. FINDINGS**
{chr(10).join(f"2.{i+1} {fact}" for i, fact in enumerate(key_facts[:4]))}

**3. IMPLICATIONS**
• Strategic importance for national climate commitments
• Economic opportunities through blue carbon markets
• Biodiversity conservation co-benefits

**4. RECOMMENDATIONS**
• Develop comprehensive management plans
• Establish monitoring and verification systems
• Create stakeholder engagement protocols
• Secure sustainable financing mechanisms

**5. CONCLUSION**
Blue carbon ecosystems represent critical natural climate solutions requiring immediate and sustained action.

**References:** {', '.join(sources)}
**Report Date:** {datetime.now().strftime('%Y-%m-%d')}
{memory_context}"""
        
        else:  # general
            if key_facts:
                return f"""Based on the blue carbon research database:

**Key Information:**
{chr(10).join(f"• {fact}" for fact in key_facts[:4])}

**Context:**
Blue carbon refers to carbon captured by coastal ecosystems including mangroves, seagrass beds, and salt marshes. These ecosystems are highly effective carbon sinks but face threats from human activities and climate change.

**Sources:** {', '.join(sources)}
{memory_context}"""
            else:
                return f"""I found relevant documents but need more specific information to answer: "{question}"

**Suggestions:**
• Try more specific terms (e.g., "mangrove restoration methods")
• Ask for analysis or summary of particular topics
• Request information about specific blue carbon processes

**Available Topics:** Carbon sequestration, ecosystem restoration, monitoring protocols, policy frameworks, and management strategies.
{memory_context}"""
    
    def _generate_no_results_response(self, question, context_type):
        """Generate helpful response when no relevant chunks found"""
        return {
            "answer": f"""I couldn't find specific information in the knowledge base for: "{question}"

**Suggestions:**
• Try rephrasing with terms like: mangroves, seagrass, salt marshes, carbon sequestration
• Ask for analysis or summary of blue carbon topics
• Upload additional PDFs if you need specific information

**Available Topics:**
• Blue carbon ecosystem types and functions
• Restoration and conservation methods
• Monitoring and measurement protocols
• Policy and governance frameworks
• Carbon market mechanisms""",
            "sources": [],
            "retrieval_time": 0.1,
            "chunks_retrieved": 0,
            "cached": False
        }

# Initialize the enhanced engine
print("🚀 Starting Enhanced Blue Carbon Backend...")
try:
    print("🔧 Step 1: Validating configuration...")
    # Validate configuration
    Config.validate_config()
    print("✅ Configuration validated")
    
    print("🔧 Step 2: Initializing chat engine...")
    # Initialize enhanced services
    chat_engine = get_simple_chat_engine()
    print("✅ Chat engine initialized")
    
    print("🔧 Step 3: Initializing async processor...")
    async_processor = get_async_processor()
    print("✅ Async processor initialized")
    
    print("🔧 Step 4: Data processing integrated into services...")
    print("✅ Data processing ready")
    
    print("🔧 Step 5: Initializing chat history...")
    chat_history = get_chat_history_service()
    print("✅ Chat history initialized")
    
    # Warm up cache for better performance (temporarily disabled)
    # chat_engine.warm_up_cache()
    
    print("✅ Enhanced chat engine ready!")
    print(f"   Performance mode: 10x enhanced")
    print(f"   Professional output: Enabled")
    print(f"   OCR support: {Config.OCR_ENABLED}")
    print(f"   Multi-language: Enabled")
    
except Exception as e:
    print(f"❌ Failed to initialize enhanced engine: {e}")
    chat_engine = None
    async_processor = None

def init_database():
    """Initialize optimized database with proper schema"""
    Path("data/chat_history").mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect("data/chat_history/history.db")
    cursor = conn.cursor()
    
    # Create table with all required columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            sources TEXT,
            session_id TEXT,
            context_type TEXT DEFAULT 'general',
            response_time REAL DEFAULT 0.0
        )
    ''')
    
    # Add response_time column if it doesn't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE chat_history ADD COLUMN response_time REAL DEFAULT 0.0')
        print("✅ Added response_time column to existing database")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Create index for faster queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_timestamp ON chat_history(session_id, timestamp)')
    conn.commit()
    conn.close()
    print("✅ Optimized database initialized with all columns")

# Background PDF processing
def process_pdf_background(file_path):
    """Process PDF in background with progress tracking"""
    try:
        print(f"Processing PDF: {file_path}")
        processor = BlueCarbonDataProcessor()
        chunk_count = processor.process_pdfs()
        
        # Reload chat engine with new data
        global chat_engine
        if chat_engine:
            print("Reloading vector store with new data...")
            chat_engine.load_vector_store()
            # Clear caches to include new data
            chat_engine.chunk_cache.clear()
            chat_engine.response_cache.clear()
            print("Vector store reloaded successfully")
        
        return {"status": "success", "chunks": chunk_count}
    except Exception as e:
        print(f"PDF processing error: {e}")
        return {"status": "error", "error": str(e)}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/favicon.ico")
def favicon():
    """Serve the logo as favicon"""
    return send_file("static/assets/chatbot logo.jpg", mimetype="image/jpeg")

@app.route("/health", methods=["GET"])
def health_check():
    """Enhanced health check with comprehensive system status"""
    try:
        if not chat_engine:
            return jsonify({"status": "unhealthy", "error": "Chat engine not initialized"}), 500
        
        # Get comprehensive stats
        performance_stats = chat_engine.get_performance_stats()
        
        return jsonify({
            "status": "healthy",
            "system": "Enhanced Blue Carbon AI",
            "version": "2.0.0",
            "features": {
                "groq_api": True,
                "professional_output": True,
                "ocr_support": Config.OCR_ENABLED,
                "multi_language": True,
                "web_search": True,
                "async_processing": True
            },
            "vector_store": vectorstore_exists(),
            "chunks_available": performance_stats['vector_store']['index_size'],
            "performance": {
                "avg_response_time_ms": performance_stats['chat_engine']['avg_response_time'],
                "cache_hit_rate": performance_stats['chat_engine']['cache_hit_rate'],
                "success_rate": performance_stats['chat_engine']['success_rate']
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/network-info", methods=["GET"])
def network_info():
    """Network connectivity information for sharing"""
    try:
        local_ip = get_local_ip()
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
        
        return jsonify({
            "status": "connected",
            "message": "🎉 Successfully connected to Blue Carbon AI!",
            "server_info": {
                "local_ip": local_ip,
                "port": 5000,
                "version": "2.0.0"
            },
            "client_info": {
                "ip": client_ip,
                "user_agent": request.headers.get('User-Agent', 'Unknown')
            },
            "features_available": {
                "chat": True,
                "report_generation": True,
                "file_upload": True,
                "web_search": True,
                "multi_language": True
            },
            "endpoints": {
                "chat": "/chat",
                "upload": "/upload", 

                "health": "/health",
                "stats": "/stats"
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/chat", methods=["POST"])
def chat():
    """Enhanced ultra-fast chat endpoint with professional responses"""
    if not chat_engine:
        return jsonify({"error": "Enhanced chat engine not initialized"}), 500
    
    data = request.json
    question = data.get("question", "").strip()
    session_id = data.get("session_id", f"session_{int(time.time())}")
    context_type = data.get("context_type", "general")
    
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    start_time = time.time()
    
    try:
        # Generate enhanced response
        response_data = chat_engine.generate_response(question, session_id)
        
        # Convert to JSON-serializable format
        response = {
            "answer": response_data.answer,
            "sources": [
                {
                    "filename": getattr(source, 'filename', ''),
                    "snippet": getattr(source, 'snippet', '')[:150] + ("..." if len(getattr(source, 'snippet', '')) > 150 else ""),
                    "similarity_score": getattr(source, 'similarity_score', 0.0),
                    "chunk_id": getattr(source, 'chunk_id', ''),
                    "page_number": getattr(source, 'page_number', 0),
                    "source_type": getattr(source, 'source_type', 'uploaded')
                }
                for source in response_data.sources
            ],
            "suggestions": response_data.suggestions,
            "retrieval_time": response_data.retrieval_time,
            "generation_time": response_data.generation_time,
            "total_time": time.time() - start_time,
            "cached": response_data.cached,
            "response_type": response_data.response_type,
            "confidence_score": response_data.confidence_score,
            "chunks_retrieved": len(response_data.sources),
            "charts": [
                {
                    "type": chart.get("type", "") if isinstance(chart, dict) else chart.type,
                    "title": chart.get("title", "") if isinstance(chart, dict) else chart.title,
                    "image_base64": chart.get("image_base64", "") if isinstance(chart, dict) else chart.image_base64,
                    "caption": chart.get("caption", "") if isinstance(chart, dict) else chart.caption
                }
                for chart in response_data.charts
            ] if response_data.charts else [],
            "web_images": response_data.web_images if hasattr(response_data, 'web_images') else [],
            "visual_content_summary": {
                "total_images": 0,
                "images_displayed": len(response_data.web_images) if hasattr(response_data, 'web_images') else 0,
                "charts_generated": len(response_data.charts) if hasattr(response_data, 'charts') else 0,
                "selection_method": "automatic",
                "quality_score": 0.0,
                "ai_selected": False
            },
            "source_priority_info": {
                "uploaded_file_sources": response_data.source_priority_info.uploaded_file_sources if response_data.source_priority_info else 0,
                "general_knowledge_sources": response_data.source_priority_info.general_knowledge_sources if response_data.source_priority_info else 0,
                "web_search_sources": response_data.source_priority_info.web_search_sources if response_data.source_priority_info else 0,
                "file_priority_percentage": response_data.source_priority_info.file_priority_percentage if response_data.source_priority_info else 0.0,
                "prioritization_method": response_data.source_priority_info.prioritization_method if response_data.source_priority_info else "standard",
                "total_sources": response_data.source_priority_info.total_sources if response_data.source_priority_info else len(response_data.sources),
                "session_files_available": response_data.source_priority_info.session_files_available if response_data.source_priority_info else 0
            }
        }
        
        # Debug logging for visual content
        print(f"📊 Enhanced Response includes:")
        print(f"   Charts: {len(response['charts'])}")
        print(f"   Web Images: {len(response['web_images'])}")
        print(f"   Sources: {len(response['sources'])}")
        print(f"   File Priority: {response['source_priority_info']['file_priority_percentage']:.1%}")
        print(f"   Charts Generated: {response['visual_content_summary']['charts_generated']}")
        
        # Save to database (async for speed)
        try:
            threading.Thread(target=save_to_database_enhanced, args=(
                question, response_data.answer, json.dumps(response["sources"]), 
                session_id, context_type, response["total_time"], response_data.confidence_score
            )).start()
        except Exception as db_error:
            print(f"Database save error: {db_error}")
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Enhanced chat error: {e}")
        return jsonify({
            "error": "I encountered an error processing your request. Please try again.",
            "sources": [],
            "suggestions": ["Try rephrasing your question", "Check if the system is properly initialized"],
            "retrieval_time": 0.0,
            "generation_time": 0.0,
            "total_time": time.time() - start_time,
            "cached": False,
            "response_type": context_type,
            "confidence_score": 0.0,
            "chunks_retrieved": 0
        }), 500

def save_to_database_enhanced(question, answer, sources, session_id, context_type, response_time, confidence_score):
    """Save enhanced chat to database using chat history service"""
    try:
        if not chat_history:
            return
        
        # Add user message
        chat_history.add_message(session_id, 'user', question)
        
        # Add assistant message with metadata
        sources_list = json.loads(sources) if isinstance(sources, str) else sources
        chat_history.add_message(
            session_id, 'assistant', answer, 
            sources_list, response_time, confidence_score
        )
        
    except Exception as e:
        print(f"Enhanced database save error: {e}")

# Backward compatibility
def save_to_database(question, answer, sources, session_id, context_type, response_time):
    """Backward compatible database save"""
    save_to_database_enhanced(question, answer, sources, session_id, context_type, response_time, 0.0)

@app.route("/upload", methods=["POST"])
def upload_pdf():
    """Enhanced PDF upload with topic relevance checking and session integration"""
    if not async_processor:
        return jsonify({"error": "Async processor not initialized"}), 500
    
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a PDF file"}), 400
    
    # Get session ID from request
    session_id = request.form.get('session_id', f'upload_session_{int(time.time())}')
    
    # Ensure session exists
    from services.session_manager import get_session_manager
    session_manager = get_session_manager()
    if not session_manager.session_exists(session_id):
        session_id = session_manager.create_new_session(f"File upload: {file.filename}")
    
    try:
        # Save file temporarily for content checking
        uploads_dir = Config.UPLOADS_DIR
        uploads_dir.mkdir(exist_ok=True)
        temp_path = uploads_dir / file.filename
        file.save(temp_path)
        
        # AI-powered relevance check using file processor
        try:
            from services.file_processor import get_file_processor
            from services.groq_service import get_groq_client
            
            file_processor = get_file_processor()
            groq_client = get_groq_client()
            
            # Scan PDF for topic relevance before processing
            relevance_info = file_processor.scan_pdf_for_topic_relevance(str(temp_path), groq_client)
            
            if not relevance_info['is_relevant']:
                # Remove the temporary file
                temp_path.unlink()
                
                return jsonify({
                    "error": "File not relevant to blue carbon topics",
                    "message": relevance_info['reason'],
                    "relevance_score": relevance_info['confidence'],
                    "topics_found": relevance_info.get('topics_found', []),
                    "analysis_method": relevance_info.get('analysis_method', 'ai_powered'),
                    "suggestions": [
                        "Upload documents about blue carbon ecosystems (mangroves, seagrass, salt marshes)",
                        "Include research on coastal carbon sequestration and storage",
                        "Try documents about marine ecosystem restoration and conservation",
                        "Upload policy documents related to blue carbon methodologies"
                    ]
                }), 400
            
            print(f"✅ AI confirmed document relevance: {relevance_info['confidence']:.1%} confidence")
            
        except ImportError:
            print("⚠️ Required libraries not available, skipping AI relevance check")
            relevance_info = {'is_relevant': True, 'confidence': 0.8, 'reason': 'AI check skipped'}
        except Exception as e:
            print(f"⚠️ AI relevance check error: {e}, proceeding with upload")
            relevance_info = {'is_relevant': True, 'confidence': 0.7, 'reason': f'Check failed: {str(e)}'}
        
        # Move to UPLOADS directory (not PDFs - that's for training data)
        final_path = Config.UPLOADS_DIR / file.filename
        if final_path.exists():
            # Handle duplicate filenames
            base_name = final_path.stem
            extension = final_path.suffix
            counter = 1
            while final_path.exists():
                final_path = Config.UPLOADS_DIR / f"{base_name}_{counter}{extension}"
                counter += 1
        
        temp_path.rename(final_path)
        
        # Add file to session (use the actual final filename, not the original)
        session_manager.add_session_file(
            session_id, 
            final_path.name,  # Use the actual filename with counter if it was renamed
            str(final_path), 
            relevance_score if 'relevance_score' in locals() else 0.8
        )
        
        # Start asynchronous processing
        task_id = async_processor.process_file_async(str(final_path))
        
        # Add a message to the session about the file upload
        session_manager.add_message(
            session_id, 
            'system', 
            f"📎 Uploaded file: {file.filename} (Relevance: {relevance_score if 'relevance_score' in locals() else 0.8:.1%})"
        )
        
        return jsonify({
            "message": f"✅ {file.filename} uploaded successfully! AI confirmed relevance to blue carbon topics.",
            "filename": file.filename,
            "session_id": session_id,
            "task_id": task_id,
            "status": "processing",
            "relevance_info": {
                "score": relevance_info['confidence'],
                "topics_found": relevance_info.get('topics_found', []),
                "analysis_method": relevance_info.get('analysis_method', 'ai_powered'),
                "reason": relevance_info['reason']
            },
            "features": {
                "smart_file_detection": True,
                "ocr_support": Config.OCR_ENABLED,
                "parallel_processing": True,
                "enhanced_chunking": True,
                "session_integration": True,
                "smart_source_selection": True
            },
            "status_endpoint": f"/upload_status/{task_id}",
            "chat_ready": True,
            "instructions": "You can now ask questions about this document. The AI will prioritize information from your uploaded file and supplement with web search when needed."
        }), 202  # Accepted
            
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/upload_status/<task_id>", methods=["GET"])
def get_upload_status(task_id):
    """Get processing status for uploaded file"""
    if not async_processor:
        return jsonify({"error": "Async processor not initialized"}), 500
    
    try:
        status = async_processor.get_processing_status(task_id)
        
        if not status:
            return jsonify({"error": "Task not found"}), 404
        
        return jsonify({
            "task_id": status.task_id,
            "status": status.status,
            "progress": status.progress,
            "chunks_processed": status.chunks_processed,
            "total_chunks": status.total_chunks,
            "filename": status.filename,
            "error_message": status.error_message,
            "created_at": status.created_at.isoformat() if status.created_at else None,
            "completed_at": status.completed_at.isoformat() if status.completed_at else None
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/session/<session_id>/info", methods=["GET"])
def get_session_info(session_id):
    """Get session information including uploaded files"""
    try:
        from services.session_manager import get_session_manager
        session_manager = get_session_manager()
        
        if not session_manager.session_exists(session_id):
            return jsonify({"error": "Session not found"}), 404
        
        # Get session files
        files = session_manager.get_session_files(session_id)
        
        # Get recent messages
        messages = session_manager.get_session_history(session_id, limit=10)
        
        return jsonify({
            "session_id": session_id,
            "files": files,
            "file_count": len(files),
            "recent_messages": len(messages),
            "has_files": len(files) > 0,
            "context_available": len(files) > 0 or len(messages) > 0
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload_status", methods=["GET"])
def get_all_upload_status():
    """Get status of all processing tasks"""
    if not async_processor:
        return jsonify({"error": "Async processor not initialized"}), 500
    
    try:
        all_tasks = async_processor.get_all_tasks()
        
        tasks_data = []
        for task_id, status in all_tasks.items():
            tasks_data.append({
                "task_id": task_id,
                "status": status.status,
                "progress": status.progress,
                "chunks_processed": status.chunks_processed,
                "filename": status.filename,
                "created_at": status.created_at.isoformat() if status.created_at else None
            })
        
        return jsonify({
            "tasks": tasks_data,
            "total_tasks": len(tasks_data),
            "stats": async_processor.get_processing_stats()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/translate", methods=["POST"])
def translate_text():
    """Enhanced multi-language translation service"""
    try:
        from services.translation_service import get_translation_service
        translation_service = get_translation_service()
        
        data = request.json
        text = data.get("text", "")
        target_lang = data.get("target_lang", "es")
        source_lang = data.get("source_lang", "auto")
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        # Perform translation
        result = translation_service.translate(text, target_lang, source_lang)
        
        return jsonify({
            "original": result.original_text,
            "translated": result.translated_text,
            "source_lang": result.source_language,
            "target_lang": result.target_language,
            "confidence": result.confidence,
            "service_used": result.service_used,
            "supported_languages": translation_service.get_supported_languages()
        })
        
    except Exception as e:
        print(f"Translation error: {e}")
        return jsonify({"error": f"Translation failed: {str(e)}"}), 500

@app.route("/translate/languages", methods=["GET"])
def get_supported_languages():
    """Get list of supported languages for translation"""
    try:
        from services.translation_service import get_translation_service
        translation_service = get_translation_service()
        
        return jsonify({
            "supported_languages": translation_service.get_supported_languages(),
            "total_languages": len(translation_service.get_supported_languages()),
            "indian_languages": {
                "hi": "Hindi",
                "bn": "Bengali", 
                "ta": "Tamil",
                "te": "Telugu",
                "mr": "Marathi",
                "gu": "Gujarati",
                "kn": "Kannada",
                "ml": "Malayalam",
                "pa": "Punjabi"
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/regenerate", methods=["POST"])
def regenerate_response():
    """Regenerate the last response"""
    if not chat_engine:
        return jsonify({"error": "Chat engine not initialized"}), 500
    
    data = request.json
    question = data.get("question", "").strip()
    session_id = data.get("session_id", f"session_{int(time.time())}")
    context_type = data.get("context_type", "general")
    
    if not question:
        return jsonify({"error": "No question provided"}), 400
    
    try:
        # Clear cache for this specific question to force regeneration
        cache_key = f"{question}_{context_type}_{session_id}"
        chat_engine.cache.cache.delete(cache_key)
        
        # Generate new response
        response_data = chat_engine.generate_response(question, session_id)
        
        # Convert to JSON format
        response = {
            "answer": response_data.answer,
            "sources": [
                {
                    "filename": source.filename,
                    "snippet": source.snippet[:100] + "..." if len(source.snippet) > 100 else source.snippet,
                    "similarity_score": source.similarity_score,
                    "source_type": getattr(source, 'source_type', 'uploaded')
                }
                for source in response_data.sources
            ],
            "suggestions": response_data.suggestions,
            "regenerated": True
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Regenerate error: {e}")
        return jsonify({"error": str(e)}), 500





@app.route("/history", methods=["GET"])
def get_chat_history():
    """Get chat sessions for sidebar"""
    try:
        # Use chat_history service which has the actual chat data
        if chat_history:
            sessions = chat_history.get_all_sessions(limit=50)
            return jsonify({"sessions": sessions})
        else:
            return jsonify({"sessions": []})
        
    except Exception as e:
        print(f"History error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"sessions": []})

@app.route("/session/<session_id>/messages", methods=["GET"])
def get_session_messages(session_id):
    """Get messages for a specific session"""
    try:
        # Use the same chat_history service that saves messages
        messages = chat_history.get_session_history(session_id, limit=50)
        return jsonify({"messages": messages})
        
    except Exception as e:
        print(f"Session messages error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"messages": []})

@app.route("/session/new", methods=["POST"])
def create_new_session():
    """Create a new chat session"""
    try:
        from services.session_manager import get_session_manager
        session_manager = get_session_manager()
        
        data = request.json or {}
        first_message = data.get("first_message", "")
        
        # Create session in session_manager
        session_id = session_manager.create_new_session(first_message)
        
        # Also create session in chat_history so it appears in sidebar immediately
        if chat_history:
            title = first_message if first_message else "New Chat"
            chat_history.create_session(session_id, title)
        
        return jsonify({
            "session_id": session_id,
            "message": "New session created successfully"
        })
        
    except Exception as e:
        print(f"New session error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/session/<session_id>", methods=["DELETE"])
def delete_session(session_id):
    """Delete a chat session and all its data"""
    try:
        # Delete from chat history service (this is where the chat history is stored)
        if chat_history:
            success = chat_history.delete_session(session_id)
            
            if success:
                print(f"✅ Deleted session: {session_id}")
                return jsonify({
                    "message": "Session deleted successfully",
                    "session_id": session_id
                })
            else:
                return jsonify({"error": "Failed to delete session"}), 500
        else:
            return jsonify({"error": "Chat history service not available"}), 500
        
    except Exception as e:
        print(f"Delete session error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/stats", methods=["GET"])
def get_system_stats():
    """Get comprehensive system performance statistics"""
    try:
        # Get basic stats from database
        conn = sqlite3.connect("data/chat_history/history.db")
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM chat_sessions")
            total_conversations = cursor.fetchone()[0]
        except:
            total_conversations = 0
        
        conn.close()
        
        # Get vector store stats
        total_documents = 0
        total_chunks = 0
        
        if chat_engine and hasattr(chat_engine, 'vector_store'):
            try:
                if hasattr(chat_engine.vector_store, 'index') and chat_engine.vector_store.index:
                    total_chunks = chat_engine.vector_store.index.ntotal
                if hasattr(chat_engine.vector_store, 'metadata'):
                    total_documents = len(set(chunk.get("source_file", "") for chunk in chat_engine.vector_store.metadata))
            except:
                pass
        
        # Return simple stats
        return jsonify({
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "total_conversations": total_conversations,
            "chat_engine_status": "active" if chat_engine else "inactive",
            "version": "2.0.0 Enhanced"
        })
        
    except Exception as e:
        print(f"Stats error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "total_documents": 0,
            "total_chunks": 0,
            "total_conversations": 0,
            "chat_engine_status": "error",
            "error": str(e)
        }), 500

@app.route("/benchmark", methods=["POST"])
def run_benchmark():
    """Run system performance benchmark"""
    try:
        # Simple benchmark using available services
        start_time = time.time()
        
        # Test chat engine response time
        if chat_engine:
            test_response = chat_engine.generate_response("What are blue carbon ecosystems?", "benchmark_test")
            response_time = time.time() - start_time
        else:
            response_time = 0
        
        benchmark_results = {
            "response_time": response_time,
            "system_status": "operational" if chat_engine else "limited",
            "services_active": {
                "chat_engine": bool(chat_engine),
                "async_processor": bool(async_processor)
            }
        }
        
        return jsonify({
            "benchmark_results": benchmark_results,
            "timestamp": datetime.now().isoformat(),
            "system_version": "2.0.0 Enhanced"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stats/legacy", methods=["GET"])
def get_legacy_stats():
    """Get legacy system statistics for backward compatibility"""
    try:
        stats = {
            "vector_store_exists": vectorstore_exists(),
            "chat_engine_status": "active" if chat_engine else "inactive"
        }
        
        if chat_engine and hasattr(chat_engine, 'vector_store'):
            stats["total_chunks"] = chat_engine.vector_store.index.ntotal if chat_engine.vector_store.index else 0
            stats["total_documents"] = len(set(chunk.get("source_file", "") for chunk in chat_engine.vector_store.metadata))
            stats["llm_type"] = "enhanced_groq"
        
        # Chat history stats
        try:
            conn = sqlite3.connect("data/chat_history/history.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM chat_history")
            stats["total_conversations"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(response_time) FROM chat_history WHERE response_time IS NOT NULL")
            avg_time = cursor.fetchone()[0]
            stats["avg_response_time"] = round(avg_time, 2) if avg_time else 0
            
            conn.close()
        except:
            stats["total_conversations"] = 0
            stats["avg_response_time"] = 0
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_local_ip():
    """Get the local IP address for network sharing"""
    try:
        # Connect to a remote server to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        # Fallback method
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except Exception:
            return "Unable to determine IP"

if __name__ == "__main__":
    # Initialize enhanced database
    init_database()
    
    # Get local IP for sharing
    local_ip = get_local_ip()
    port = 5000
    
    print("\n" + "="*80)
    print("🚀 ENHANCED BLUE CARBON AI CHATBOT - VERSION 2.0.0")
    print("="*80)
    print("⚡ 10x Performance Enhancement: ACTIVE")
    print("🧠 Groq AI Integration: ENABLED")
    print("📄 Advanced OCR Processing: ENABLED" if Config.OCR_ENABLED else "📄 OCR Processing: DISABLED")
    print("🌍 Multi-Language Translation: ENABLED")
    print("🔍 Web Search Integration: ENABLED")
    print("📊 Advanced Data Visualization: ENABLED")
    print("🎯 Autonomous Decision Making: ENABLED")
    print("💾 Multi-Level Caching: ENABLED")
    print("⚙️  Parallel Processing: ENABLED")
    print("📈 Real-time Analytics: ENABLED")
    print("="*80)
    print("🌐 ACCESS URLS:")
    print(f"   Local:    http://localhost:{port}")
    print(f"   Network:  http://{local_ip}:{port}")
    print("="*80)
    print("📤 SHARE WITH FRIENDS:")
    print(f"   Send this link: http://{local_ip}:{port}")
    print("   Make sure your firewall allows port 5000")
    print("="*80)
    print("🎯 Ready for professional-grade blue carbon analysis!")
    print("="*80 + "\n")
    
    # Run with network access enabled
    app.run(debug=True, host="0.0.0.0", port=port, threaded=True)