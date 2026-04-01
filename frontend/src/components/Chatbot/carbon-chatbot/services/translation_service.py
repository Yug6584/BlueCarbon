import requests
import time
from typing import Dict, Any, Optional, List
from models.response_models import TranslationResult
from config import Config

class TranslationService:
    """Multi-language translation service with local and online options"""
    
    def __init__(self):
        self.supported_languages = Config.SUPPORTED_LANGUAGES
        
        # Try to initialize local translation models
        self.local_translator = None
        self.local_available = False
        
        try:
            from transformers import MarianMTModel, MarianTokenizer
            self.MarianMTModel = MarianMTModel
            self.MarianTokenizer = MarianTokenizer
            self.local_available = True
            print("✅ Local translation models available")
        except ImportError:
            print("⚠️ Transformers not available for local translation")
        
        # Fallback using googletrans (simple version)
        self.google_translator = None
        self.google_available = False
        
        try:
            from googletrans import Translator
            self.google_translator = Translator()
            self.google_available = True
            print("✅ Google Translate fallback available")
        except ImportError:
            print("⚠️ Google Translate not available")
        
        print(f"🌍 TranslationService initialized")
        print(f"   Local models: {self.local_available}")
        print(f"   Google fallback: {self.google_available}")
        print(f"   Supported languages: {len(self.supported_languages)}")
    
    def detect_language(self, text: str) -> str:
        """Detect language of input text"""
        try:
            # Try LibreTranslate first
            response = requests.post(
                f"{self.libretranslate_url}/detect",
                json={"q": text[:500]},  # Limit text for detection
                timeout=5.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("language", "en")
            
        except Exception as e:
            print(f"LibreTranslate detection error: {e}")
        
        # Fallback to Google Translate
        if self.google_available:
            try:
                detection = self.google_translator.detect(text)
                if hasattr(detection, 'lang'):
                    return detection.lang
            except Exception as e:
                print(f"Google Translate detection error: {e}")
        
        return "en"  # Default to English
    
    def translate_libretranslate(self, text: str, target_lang: str, source_lang: str = "auto") -> Optional[TranslationResult]:
        """Translate using LibreTranslate"""
        try:
            # Auto-detect source language if needed
            if source_lang == "auto":
                source_lang = self.detect_language(text)
            
            # Skip translation if source and target are the same
            if source_lang == target_lang:
                return TranslationResult(
                    original_text=text,
                    translated_text=text,
                    source_language=source_lang,
                    target_language=target_lang,
                    confidence=1.0,
                    service_used="libretranslate"
                )
            
            # Perform translation
            response = requests.post(
                f"{self.libretranslate_url}/translate",
                json={
                    "q": text,
                    "source": source_lang,
                    "target": target_lang,
                    "format": "text"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                translated_text = result.get("translatedText", text)
                
                return TranslationResult(
                    original_text=text,
                    translated_text=translated_text,
                    source_language=source_lang,
                    target_language=target_lang,
                    confidence=0.9,  # LibreTranslate doesn't provide confidence
                    service_used="libretranslate"
                )
            else:
                print(f"LibreTranslate error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"LibreTranslate translation error: {e}")
        
        return None
    
    def translate_google(self, text: str, target_lang: str, source_lang: str = "auto") -> Optional[TranslationResult]:
        """Translate using Google Translate (fallback)"""
        if not self.google_available:
            return None
        
        try:
            import asyncio
            
            # Normalize Chinese language codes for Google Translate
            # Google Translate uses 'zh-cn' for simplified and 'zh-tw' for traditional
            normalized_target = target_lang
            if target_lang == 'zh':
                normalized_target = 'zh-cn'  # Default to simplified Chinese
            
            # Create async function for translation
            async def async_translate():
                if source_lang == "auto":
                    translation = await self.google_translator.translate(text, dest=normalized_target)
                    detected_lang = getattr(translation, 'src', 'unknown')
                else:
                    translation = await self.google_translator.translate(text, src=source_lang, dest=normalized_target)
                    detected_lang = source_lang
                return translation, detected_lang
            
            # Run async translation
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            translation, detected_lang = loop.run_until_complete(async_translate())
            
            if hasattr(translation, 'text'):
                return TranslationResult(
                    original_text=text,
                    translated_text=translation.text,
                    source_language=detected_lang,
                    target_language=target_lang,
                    confidence=getattr(translation, 'confidence', None),
                    service_used="google_translate"
                )
            else:
                print("Google Translate: No text attribute in response")
                return None
            
        except Exception as e:
            print(f"Google Translate error: {e}")
            import traceback
            traceback.print_exc()
        
        return None
    
    def translate_local(self, text: str, target_lang: str, source_lang: str = "en") -> Optional[TranslationResult]:
        """Translate using local Marian models"""
        if not self.local_available:
            return None
        
        try:
            # Simple language mapping for Marian models
            model_map = {
                "es": "Helsinki-NLP/opus-mt-en-es",
                "fr": "Helsinki-NLP/opus-mt-en-fr", 
                "de": "Helsinki-NLP/opus-mt-en-de",
                "hi": "Helsinki-NLP/opus-mt-en-hi"
            }
            
            if target_lang not in model_map:
                return None
            
            model_name = model_map[target_lang]
            
            # Load model and tokenizer
            tokenizer = self.MarianTokenizer.from_pretrained(model_name)
            model = self.MarianMTModel.from_pretrained(model_name)
            
            # Translate
            inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            translated = model.generate(**inputs)
            translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language=source_lang,
                target_language=target_lang,
                confidence=0.9,
                service_used="local_marian"
            )
            
        except Exception as e:
            print(f"Local translation error: {e}")
            return None
    
    def translate_simple(self, text: str, target_lang: str) -> TranslationResult:
        """Simple translation with basic language support"""
        # Basic translation dictionary for common phrases
        translations = {
            "es": {
                "hello": "hola",
                "thank you": "gracias", 
                "blue carbon": "carbono azul",
                "mangroves": "manglares",
                "seagrass": "pastos marinos",
                "carbon sequestration": "secuestro de carbono"
            },
            "fr": {
                "hello": "bonjour",
                "thank you": "merci",
                "blue carbon": "carbone bleu", 
                "mangroves": "mangroves",
                "seagrass": "herbiers marins",
                "carbon sequestration": "séquestration du carbone"
            },
            "hi": {
                "hello": "नमस्ते",
                "thank you": "धन्यवाद",
                "blue carbon": "नीला कार्बन",
                "mangroves": "मैंग्रोव",
                "seagrass": "समुद्री घास"
            }
        }
        
        if target_lang in translations:
            translated_text = text.lower()
            for en_phrase, translated_phrase in translations[target_lang].items():
                translated_text = translated_text.replace(en_phrase, translated_phrase)
            
            return TranslationResult(
                original_text=text,
                translated_text=translated_text,
                source_language="en",
                target_language=target_lang,
                confidence=0.7,
                service_used="simple_dictionary"
            )
        
        return TranslationResult(
            original_text=text,
            translated_text=text,
            source_language="en", 
            target_language=target_lang,
            confidence=0.0,
            service_used="none"
        )

    def translate(self, text: str, target_lang: str, source_lang: str = "auto") -> TranslationResult:
        """Translate text with multiple fallback options"""
        if not text.strip():
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_language="unknown",
                target_language=target_lang,
                confidence=0.0,
                service_used="none"
            )
        
        # Validate target language
        if target_lang not in self.supported_languages:
            available_langs = ", ".join(self.supported_languages.keys())
            raise ValueError(f"Unsupported target language: {target_lang}. Available: {available_langs}")
        
        # Try Google Translate FIRST (most reliable)
        if self.google_available:
            print(f"🌐 Attempting Google Translate: {target_lang}")
            result = self.translate_google(text, target_lang, source_lang)
            if result and result.translated_text != text:
                print(f"✅ Google Translate successful")
                return result
            else:
                print(f"⚠️ Google Translate failed or returned same text")
        
        # Try local translation (for supported languages)
        if source_lang == "en" or source_lang == "auto":
            print(f"🔧 Attempting local translation: {target_lang}")
            result = self.translate_local(text, target_lang, "en")
            if result and result.translated_text != text:
                print(f"✅ Local translation successful")
                return result
        
        # Fallback to simple dictionary translation (last resort)
        print(f"⚠️ Using simple dictionary fallback")
        result = self.translate_simple(text, target_lang)
        if result.confidence > 0:
            return result
        
        # If all fails, return original text
        print(f"❌ All translation methods failed")
        return TranslationResult(
            original_text=text,
            translated_text=text,
            source_language=source_lang if source_lang != "auto" else "unknown",
            target_language=target_lang,
            confidence=0.0,
            service_used="none"
        )
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
        return self.supported_languages.copy()
    
    def batch_translate(self, texts: List[str], target_lang: str, source_lang: str = "auto") -> List[TranslationResult]:
        """Translate multiple texts"""
        results = []
        
        for text in texts:
            try:
                result = self.translate(text, target_lang, source_lang)
                results.append(result)
                time.sleep(0.1)  # Rate limiting
            except Exception as e:
                print(f"Batch translation error for text '{text[:50]}...': {e}")
                results.append(TranslationResult(
                    original_text=text,
                    translated_text=text,
                    source_language="unknown",
                    target_language=target_lang,
                    confidence=0.0,
                    service_used="error"
                ))
        
        return results

# Global instance
_translation_service = None

def get_translation_service() -> TranslationService:
    """Get global translation service instance"""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service