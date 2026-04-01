import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration management for enhanced carbon chatbot"""
    
    # API Keys - set these in your .env file
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    LLAMA_INDEX_API_KEY = os.getenv("LLAMA_INDEX_API_KEY", "")
    WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY", "")  # SerpApi key for web search
    
    # Feature flags based on available keys
    WEB_SEARCH_ENABLED = bool(WEB_SEARCH_API_KEY)  # Re-enabled with new API key
    
    # Directories
    DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
    PDFS_DIR = DATA_DIR / "pdfs"
    VECTORSTORE_DIR = DATA_DIR / "vectorstore"
    UPLOADS_DIR = DATA_DIR / "uploads"
    CHAT_HISTORY_DIR = DATA_DIR / "chat_history"
    REPORTS_DIR = DATA_DIR / "reports"
    CHARTS_DIR = DATA_DIR / "charts"
    
    # Performance Settings
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
    
    # Redis Configuration
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    
    # Model Configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")  # Updated to current model
    
    # Processing Configuration
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.2"))
    
    # Translation Configuration
    LIBRETRANSLATE_URL = os.getenv("LIBRETRANSLATE_URL", "https://libretranslate.de")
    SUPPORTED_LANGUAGES = {
        "hi": "Hindi",
        "bn": "Bengali", 
        "ta": "Tamil",
        "te": "Telugu",
        "mr": "Marathi",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "pt": "Portuguese",
        "zh": "Chinese",
        "zh-cn": "Chinese (Simplified)",
        "zh-tw": "Chinese (Traditional)",
        "ja": "Japanese",
        "ko": "Korean",
        "en": "English"
    }
    
    # OCR Configuration
    OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
    OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "eng")
    
    # Report Configuration
    REPORT_FORMATS = ["html", "pdf"]
    CHART_TYPES = ["line", "bar", "pie", "scatter", "histogram"]
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        for dir_path in [cls.PDFS_DIR, cls.VECTORSTORE_DIR, cls.UPLOADS_DIR, 
                        cls.CHAT_HISTORY_DIR, cls.REPORTS_DIR, cls.CHARTS_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate_config(cls):
        """Validate configuration settings"""
        if not cls.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is required")
        
        cls.create_directories()
        return True