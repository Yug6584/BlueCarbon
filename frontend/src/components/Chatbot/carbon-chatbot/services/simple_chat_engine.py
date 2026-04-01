import time
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from models.response_models import ResponseData, Source
from services.groq_service import get_groq_client
from services.vector_store import get_vector_store
from services.embedding_service import get_embedding_processor
from services.web_search_service import get_web_search_service
from services.session_manager import get_session_manager
from services.file_chunk_matcher import get_file_chunk_matcher
from services.context_builder import get_context_builder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/chat_history/chat_engine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimpleChatEngine:
    """BlueCarbon AI - Three-tier retrieval system for environmental intelligence"""
    
    # Allowed file topics for BlueCarbon AI
    ALLOWED_TOPICS = {
        'blue_carbon', 'carbon_credits', 'coastal_restoration', 'mangroves', 'seagrass', 
        'salt_marshes', 'marine_ecosystems', 'carbon_sequestration', 'climate_change',
        'environmental_policy', 'coastal_management', 'biodiversity', 'ocean_conservation',
        'wetlands', 'ecosystem_services', 'carbon_markets', 'sustainability', 'restoration',
        'conservation', 'marine_biology', 'coastal_ecology', 'environmental_science'
    }
    
    def __init__(self):
        print("🌊 Initializing BlueCarbon AI - Environmental Intelligence Assistant...")
        logger.info("Initializing BlueCarbon AI SimpleChatEngine")
        
        try:
            self.groq_client = get_groq_client()
            self.vector_store = get_vector_store()
            self.embedding_processor = get_embedding_processor()
            self.web_search = get_web_search_service()
            self.session_manager = get_session_manager()
            
            # Error tracking
            self.error_counts = {'groq': 0, 'vector': 0, 'web': 0, 'file': 0}
            self.last_error_reset = datetime.now()
            
            logger.info("BlueCarbon AI initialized successfully")
            print("✅ BlueCarbon AI ready for environmental intelligence!")
        except Exception as e:
            logger.error(f"Failed to initialize BlueCarbon AI: {e}")
            raise
    
    def _needs_images(self, query: str) -> bool:
        """Detect if query needs images/visual content"""
        IMAGE_KEYWORDS = [
            'image', 'picture', 'photo', 'diagram', 'illustration', 
            'visual', 'show me', 'cycle', 'process', 'chart', 'graph',
            'infographic', 'visualization', 'drawing', 'figure', 'map',
            'flowchart', 'schematic', 'blueprint', 'sketch'
        ]
        query_lower = query.lower()
        needs_images = any(keyword in query_lower for keyword in IMAGE_KEYWORDS)
        
        if needs_images:
            print(f"🖼️ Image keywords detected in query - will fetch images from web")
        
        return needs_images
    
    def _ai_decide_image_needs(self, query: str) -> Dict[str, Any]:
        """AI-driven decision on whether images are needed and how many (0-3)"""
        try:
            print("🤖 AI analyzing query for image needs...")
            
            system_prompt = """You are an intelligent assistant that decides if a query needs visual content (images).

Analyze the user's question and decide:
1. Does this question benefit from images? (yes/no)
2. How many images would be helpful? (0-3)

GUIDELINES:
- Questions about "what is", "how does", "explain", "show" → likely need images
- Questions about processes, cycles, diagrams → definitely need images (2-3)
- Questions about specific data, numbers, calculations → no images needed (0)
- Questions about definitions or concepts → 1-2 images helpful
- Questions about comparisons or examples → 1-2 images helpful

Respond ONLY with JSON format:
{"needs_images": true/false, "count": 0-3, "reason": "brief explanation"}

Examples:
Query: "what is blue carbon cycle?"
Response: {"needs_images": true, "count": 2, "reason": "Cycle diagrams help visualize the process"}

Query: "calculate carbon credits for 5 acres"
Response: {"needs_images": false, "count": 0, "reason": "Calculation question, no visuals needed"}

Query: "show me mangrove restoration examples"
Response: {"needs_images": true, "count": 3, "reason": "User explicitly asks to see examples"}

Query: "explain carbon sequestration"
Response: {"needs_images": true, "count": 1, "reason": "Concept explanation benefits from one visual"}"""

            user_prompt = f"""Query: "{query}"

Analyze this query and decide if images are needed and how many (0-3).
Respond ONLY with JSON."""

            response = self.groq_client.complete(
                f"{system_prompt}\n\n{user_prompt}",
                temperature=0.3,  # Lower temperature for consistent decisions
                max_tokens=150
            )
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON from response (handle cases where AI adds extra text)
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                decision = json.loads(json_match.group())
                
                # Validate and constrain values
                needs_images = decision.get('needs_images', False)
                count = min(max(int(decision.get('count', 0)), 0), 3)  # Constrain 0-3
                reason = decision.get('reason', 'AI decision')
                
                print(f"🤖 AI Decision: needs_images={needs_images}, count={count}")
                print(f"   Reason: {reason}")
                
                return {
                    'needs_images': needs_images,
                    'count': count,
                    'reason': reason
                }
            else:
                print("⚠️ Could not parse AI response, using fallback")
                # Fallback to keyword detection
                return self._fallback_image_decision(query)
                
        except Exception as e:
            print(f"❌ Error in AI image decision: {e}")
            # Fallback to keyword detection
            return self._fallback_image_decision(query)
    
    def _fallback_image_decision(self, query: str) -> Dict[str, Any]:
        """Fallback image decision using keyword detection"""
        query_lower = query.lower()
        
        # Strong image indicators
        strong_indicators = ['show me', 'picture', 'photo', 'image', 'diagram', 'illustration', 'visual']
        has_strong = any(ind in query_lower for ind in strong_indicators)
        
        # Process/cycle indicators
        process_indicators = ['cycle', 'process', 'how does', 'how do', 'flowchart', 'steps']
        has_process = any(ind in query_lower for ind in process_indicators)
        
        # Concept indicators
        concept_indicators = ['what is', 'explain', 'define', 'tell me about']
        has_concept = any(ind in query_lower for ind in concept_indicators)
        
        # Data/calculation indicators (no images needed)
        data_indicators = ['calculate', 'how much', 'how many', 'number', 'data', 'statistics']
        has_data = any(ind in query_lower for ind in data_indicators)
        
        if has_data:
            return {'needs_images': False, 'count': 0, 'reason': 'Data/calculation query'}
        elif has_strong:
            return {'needs_images': True, 'count': 3, 'reason': 'Explicit request for visuals'}
        elif has_process:
            return {'needs_images': True, 'count': 2, 'reason': 'Process/cycle explanation'}
        elif has_concept:
            return {'needs_images': True, 'count': 1, 'reason': 'Concept explanation'}
        else:
            return {'needs_images': False, 'count': 0, 'reason': 'No clear visual need'}
    
    def _should_use_web_search(self, query: str, dataset_confidence: float = 0.0) -> bool:
        """
        AI-driven decision on whether to use web search
        Returns: use_web_search (bool)
        """
        try:
            print("🤖 AI analyzing if web search is needed...")
            
            system_prompt = """You are an intelligent assistant that decides if a query needs web search.

Analyze the user's question and the available dataset context to decide if web search is necessary.

GUIDELINES:
- Questions about recent events, news, updates (2024, 2025, "latest", "recent") → YES, need web search
- Questions asking for images, visuals, diagrams → YES, need web search for images
- Questions about general concepts well-covered in blue carbon knowledge → NO, dataset sufficient
- Questions about specific data/calculations from uploaded files → NO, use local data
- Questions about current policies, new research → YES, need web search
- Questions about basic definitions, established concepts → NO, dataset sufficient

Respond ONLY with JSON format:
{"use_web_search": true/false, "reason": "brief explanation"}

Examples:
Query: "latest blue carbon research 2025"
Response: {"use_web_search": true, "reason": "Asking for recent/latest information"}

Query: "what is blue carbon?"
Response: {"use_web_search": false, "reason": "Basic concept covered in dataset"}

Query: "show me mangrove images"
Response: {"use_web_search": true, "reason": "Requesting visual content"}

Query: "calculate carbon credits for my land"
Response: {"use_web_search": false, "reason": "Calculation using local data"}"""

            user_prompt = f"""Query: "{query}"
Dataset Confidence: {dataset_confidence:.2f}

Decide if web search is needed. Respond ONLY with JSON."""

            response = self.groq_client.complete(
                f"{system_prompt}\n\n{user_prompt}",
                temperature=0.3,
                max_tokens=100
            )
            
            # Parse JSON response
            import json
            import re
            
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                decision = json.loads(json_match.group())
                use_web = decision.get('use_web_search', False)
                reason = decision.get('reason', 'AI decision')
                
                print(f"🤖 AI Decision: use_web_search={use_web}")
                print(f"   Reason: {reason}")
                
                return use_web
            else:
                print("⚠️ Could not parse AI response, using fallback")
                return self._fallback_web_search_decision(query, dataset_confidence)
                
        except Exception as e:
            print(f"❌ Error in AI web search decision: {e}")
            return self._fallback_web_search_decision(query, dataset_confidence)
    
    def _fallback_web_search_decision(self, query: str, dataset_confidence: float) -> bool:
        """Fallback web search decision using keyword detection"""
        query_lower = query.lower()
        
        # Check for image needs
        needs_images = self._needs_images(query)
        
        # Check for recent/current information needs
        RECENT_KEYWORDS = ['latest', 'recent', 'current', '2024', '2025', 'new', 'update', 'today', 'now']
        needs_recent = any(keyword in query_lower for keyword in RECENT_KEYWORDS)
        
        # Decision logic
        if needs_images:
            print(f"🌐 Web search decision: YES (images needed)")
            return True
        elif needs_recent:
            print(f"🌐 Web search decision: YES (recent info needed)")
            return True
        elif dataset_confidence < 0.5:
            print(f"🌐 Web search decision: YES (low dataset confidence: {dataset_confidence:.2f})")
            return True
        else:
            print(f"🌐 Web search decision: NO (dataset sufficient, confidence: {dataset_confidence:.2f})")
            return False
    
    def generate_response(self, query: str, session_id: str = "default") -> ResponseData:
        """
        BlueCarbon AI Three-Tier Retrieval Logic:
        1️⃣ File Context Priority - Always try uploaded files first
        2️⃣ Dataset Fallback - Use Blue Carbon Knowledge Dataset
        3️⃣ Web Search Final Resort - Only when needed
        """
        start_time = time.time()
        
        try:
            print(f"🌊 BlueCarbon AI processing: {query[:60]}...")
            
            # Handle welcome messages and greetings
            if self._is_welcome_message(query):
                return self._create_welcome_response(query, session_id, start_time)
            
            # Check if user is mentioning a SPECIFIC filename without uploading it
            # Only trigger if they mention an actual file extension AND have no files
            if self._is_specific_filename_mentioned_without_upload(query, session_id):
                return self._create_upload_reminder_response(query, session_id, start_time)
            
            # Initialize response components
            all_sources = []
            context_parts = []
            web_images = []
            retrieval_path = []
            
            # 🔍 TIER 1: DIRECT TEXT EXTRACTION + LLM PROCESSING
            print("1️⃣ DIRECT TEXT EXTRACTION - Send complete file text to LLM...")
            file_context, file_sources = self._extract_complete_file_text(query, session_id)
            
            if file_context and file_sources:
                # Check if this is a processing status response
                if any("processing" in source.snippet.lower() for source in file_sources):
                    print("⏳ TIER 1: Files still processing - returning status response")
                    
                    # Save processing status to conversation memory
                    self._save_conversation_memory(session_id, query, file_context, file_sources)
                    
                    return self._create_response_data(
                        file_context, file_sources, [], query, session_id, 
                        ["File Processing Status"], start_time, "Processing Status"
                    )
                
                print(f"✅ TIER 1 SUCCESS: Direct extraction from {len(file_sources)} uploaded files")
                
                # INTELLIGENT ROUTING: Let AI decide if question is about the file or general knowledge
                if self._is_question_about_uploaded_file(query):
                    print("🎯 UPLOADED FILE QUESTION: Using file content only")
                    
                    all_sources = file_sources
                    retrieval_path.append("Direct File Extraction")
                    
                    # Generate response ONLY from uploaded files
                    response_from_files = self._answer_from_uploaded_files_only(query, file_context, file_sources)
                else:
                    print("💬 GENERAL QUESTION: User has files but asking general question - using general knowledge")
                    # User has files but asking a general question (e.g., "what is blue carbon?")
                    # Fall through to TIER 2 for general knowledge
                    print("⚠️ Proceeding to general knowledge for general question")
                    retrieval_path.append("General Question - Skipping File")
                    file_context = ""
                    file_sources = []
                    # Continue to TIER 2
                    print("2️⃣ Accessing Blue Carbon Knowledge Dataset...")
                    dataset_context, dataset_sources = self._get_dataset_context(query)
                    
                    if dataset_context and dataset_sources:
                        print(f"✅ TIER 2: Found {len(dataset_sources)} relevant dataset chunks")
                        context_parts.append(f"📚 BLUE CARBON KNOWLEDGE DATASET:\n{dataset_context}")
                        all_sources.extend(dataset_sources)
                        retrieval_path.append("Dataset")
                        
                        combined_context = "\n\n".join(context_parts)
                        response_from_dataset = self._try_answer_from_dataset(query, combined_context, all_sources, False)
                        
                        if response_from_dataset and self._is_sufficient_answer(response_from_dataset, query):
                            print("🎯 TIER 2 COMPLETE: Sufficient answer from dataset")
                            
                            # CHECK IF IMAGES ARE NEEDED (even if answer is sufficient)
                            web_images = []
                            if self._query_needs_images(query):
                                print("🖼️ Question needs images - triggering web search for visuals")
                                _, _, web_images = self._get_web_context(query)
                                if web_images:
                                    print(f"✅ Found {len(web_images)} relevant images")
                                    retrieval_path.append("Web Images")
                            
                            response_from_dataset = self._add_source_citation(response_from_dataset, retrieval_path, all_sources)
                            self._save_conversation_memory(session_id, query, response_from_dataset, all_sources)
                            
                            return self._create_response_data(
                                response_from_dataset, all_sources, web_images, query, session_id,
                                retrieval_path, start_time, "General Knowledge"
                            )
                    
                    # If we get here, continue with normal flow
                    print("⚠️ Insufficient dataset context, continuing to TIER 3")
                    # Fall through to TIER 3
                    print("3️⃣ Web search as final resort...")
                    if self._should_use_web_search(query, len(all_sources)):
                        print("🌐 TIER 3: Triggering web search for additional context")
                        web_context, web_sources, web_images = self._get_web_context(query)
                        
                        if web_context and web_sources:
                            print(f"✅ TIER 3: Found {len(web_sources)} web sources")
                            context_parts.append(f"🌐 WEB VERIFICATION DATA:\n{web_context}")
                            all_sources.extend(web_sources)
                            retrieval_path.append("Web Search")
                    
                    # Generate final response
                    full_context = "\n\n".join(context_parts)
                    conversation_history = self._get_session_conversation_history(session_id)
                    final_response = self._generate_final_response(query, full_context, all_sources, retrieval_path, conversation_history)
                    
                    final_response = self._add_source_citation(final_response, retrieval_path, all_sources)
                    self._save_conversation_memory(session_id, query, final_response, all_sources)
                    
                    return self._create_response_data(
                        final_response, all_sources, web_images, query, session_id,
                        retrieval_path, start_time, " + ".join(retrieval_path)
                    )
                
                # Add source citation
                response_from_files = self._add_source_citation(response_from_files, retrieval_path, all_sources)
                
                # Save conversation memory
                self._save_conversation_memory(session_id, query, response_from_files, all_sources)
                
                return self._create_response_data(
                    response_from_files, all_sources, [], query, session_id, 
                    retrieval_path, start_time, "Uploaded Files Only"
                )
            else:
                print("⚠️ TIER 1: No uploaded files found - proceeding to general knowledge")
                retrieval_path.append("No Files - General Knowledge")
            
            # 🔍 TIER 2: DATASET FALLBACK
            print("2️⃣ Accessing Blue Carbon Knowledge Dataset...")
            dataset_context, dataset_sources = self._get_dataset_context(query)
            
            if dataset_context and dataset_sources:
                print(f"✅ TIER 2: Found {len(dataset_sources)} relevant dataset chunks")
                context_parts.append(f"📚 BLUE CARBON KNOWLEDGE DATASET:\n{dataset_context}")
                all_sources.extend(dataset_sources)
                retrieval_path.append("Dataset")
                
                # Combine file + dataset if both exist
                combined_context = "\n\n".join(context_parts)
                response_from_dataset = self._try_answer_from_dataset(query, combined_context, all_sources, bool(file_context))
                
                if response_from_dataset and self._is_sufficient_answer(response_from_dataset, query):
                    print("🎯 TIER 2 COMPLETE: Sufficient answer from file + dataset")
                    
                    # CHECK IF IMAGES ARE NEEDED (even if answer is sufficient)
                    web_images = []
                    if self._query_needs_images(query):
                        print("🖼️ Question needs images - triggering web search for visuals")
                        _, _, web_images = self._get_web_context(query)
                        if web_images:
                            print(f"✅ Found {len(web_images)} relevant images")
                            retrieval_path.append("Web Images")
                    
                    # Add source citation
                    response_from_dataset = self._add_source_citation(response_from_dataset, retrieval_path, all_sources)
                    
                    # Save conversation memory
                    self._save_conversation_memory(session_id, query, response_from_dataset, all_sources)
                    
                    return self._create_response_data(
                        response_from_dataset, all_sources, web_images, query, session_id,
                        retrieval_path, start_time, "File + Dataset" if file_context else "Dataset Only"
                    )
            else:
                print("⚠️ TIER 2: Insufficient dataset context")
                retrieval_path.append("Limited Dataset")
            
            # 🔍 TIER 3: WEB SEARCH FINAL RESORT
            print("3️⃣ Web search as final resort...")
            if self._should_use_web_search(query, len(all_sources)):
                print("🌐 TIER 3: Triggering web search for additional context")
                web_context, web_sources, web_images = self._get_web_context(query)
                
                if web_context and web_sources:
                    print(f"✅ TIER 3: Found {len(web_sources)} web sources")
                    context_parts.append(f"🌐 WEB VERIFICATION DATA:\n{web_context}")
                    all_sources.extend(web_sources)
                    retrieval_path.append("Web Search")
            
            # Generate final comprehensive response with conversation context
            full_context = "\n\n".join(context_parts)
            conversation_history = self._get_session_conversation_history(session_id)
            final_response = self._generate_final_response(query, full_context, all_sources, retrieval_path, conversation_history)
            
            # Add retrieval path citation
            final_response = self._add_source_citation(final_response, retrieval_path, all_sources)
            
            # Save conversation to session memory (like ChatGPT)
            self._save_conversation_memory(session_id, query, final_response, all_sources)
            
            return self._create_response_data(
                final_response, all_sources, web_images, query, session_id,
                retrieval_path, start_time, " + ".join(retrieval_path)
            )
            
        except Exception as e:
            logger.error(f"BlueCarbon AI generation failed: {e}")
            return self._create_error_response(query, session_id, str(e), start_time)
    
    def _get_file_context(self, query: str, session_id: str) -> Tuple[str, List[Source]]:
        """TIER 1: Get context from user's uploaded files - SESSION SPECIFIC like ChatGPT"""
        try:
            print(f"📁 Checking session-specific files for session: {session_id}")
            
            # Get ONLY files uploaded in THIS specific session (ChatGPT behavior)
            session_files = self.session_manager.get_session_files(session_id)
            if not session_files:
                print(f"📁 No uploaded files found in session {session_id}")
                return "", []
            
            print(f"📁 Found {len(session_files)} files in session {session_id}")
            
            # Validate file topics are allowed for BlueCarbon AI
            valid_files = []
            rejected_files = []
            
            for file_info in session_files:
                filename = file_info.get('filename', '')
                processing_status = file_info.get('processing_status', 'pending')
                
                # Only use completed files
                if processing_status != 'completed':
                    print(f"⏳ File still processing: {filename} (status: {processing_status})")
                    continue
                
                if self._is_file_topic_allowed(filename):
                    valid_files.append(file_info)
                    print(f"✅ File validated: {filename}")
                else:
                    rejected_files.append(filename)
                    print(f"🚫 File rejected - not blue carbon related: {filename}")
            
            if rejected_files:
                print(f"🚫 Rejected {len(rejected_files)} non-blue carbon files: {', '.join(rejected_files)}")
            
            if not valid_files:
                if rejected_files:
                    print("🚫 No files match blue carbon topics - all files rejected")
                else:
                    print("⏳ No completed files available yet")
                return "", []
            
            print(f"✅ {len(valid_files)} valid blue carbon files ready for processing")
            
            # Get comprehensive file content using multiple strategies
            file_context, file_sources = self._extract_comprehensive_file_content(query, valid_files, session_id)
            
            if file_context and file_sources:
                print(f"📁 SUCCESS: Built comprehensive file context from {len(file_sources)} chunks")
                return file_context, file_sources
            else:
                print("📁 No relevant content found in uploaded files for this query")
                return "", []
            
        except Exception as e:
            print(f"❌ Error getting session file context: {e}")
            self.error_counts['file'] += 1
            return "", []
    
    def _extract_comprehensive_file_content(self, query: str, valid_files: List[Dict], session_id: str) -> Tuple[str, List[Source]]:
        """Extract comprehensive content from session-specific uploaded files - GET ALL CHUNKS"""
        try:
            filenames = [f.get('filename', '') for f in valid_files]
            print(f"🔍 Extracting ALL content from files: {', '.join(filenames)}")
            
            # NEW APPROACH: Get ALL chunks from the uploaded files, not just semantically similar ones
            # This ensures we never miss table data or any other content
            all_file_chunks = []
            
            # Load ALL chunks from vector store metadata
            import json
            metadata_path = Path('data/vectorstore/metadata.json')
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    all_metadata = json.load(f)
                
                # Filter to get ALL chunks from the session's files
                for chunk in all_metadata:
                    source_file = chunk.get('source_file', '')
                    for file_info in valid_files:
                        filename = file_info.get('filename', '')
                        file_path = file_info.get('file_path', '')
                        
                        # Match this chunk to session files
                        if (filename in source_file or 
                            source_file.endswith(filename) or
                            file_path in source_file or
                            source_file.startswith(f"uploads/{session_id}") or
                            f"session_{session_id}" in source_file):
                            all_file_chunks.append(chunk)
                            break
                
                print(f"📄 Extracted ALL {len(all_file_chunks)} chunks from uploaded files")
            
            # If we got chunks, use them ALL
            if all_file_chunks:
                semantic_results = all_file_chunks
            else:
                # Fallback to semantic search if metadata loading failed
                print("⚠️ Metadata loading failed, falling back to semantic search")
                query_embedding = self.embedding_processor.embed_texts_parallel([query])[0]
                all_results = self.vector_store.search(query_embedding, 200)
                semantic_results = []
                
                for result in all_results:
                    source_file = result.get('source_file', '')
                    for file_info in valid_files:
                        filename = file_info.get('filename', '')
                        if filename in source_file or source_file.endswith(filename):
                            semantic_results.append(result)
                            break
            
            # Filter results to ONLY include chunks from THIS session's files
            for result in all_results:
                source_file = result.get('source_file', '')
                
                # Check if this chunk belongs to any of the session's uploaded files
                belongs_to_session = False
                for file_info in valid_files:
                    filename = file_info.get('filename', '')
                    file_path = file_info.get('file_path', '')
                    
                    # Multiple matching strategies
                    if (filename in source_file or 
                        source_file.endswith(filename) or
                        file_path in source_file or
                        source_file.startswith(f"uploads/{session_id}") or
                        f"session_{session_id}" in source_file):
                        belongs_to_session = True
                        break
                
                if belongs_to_session:
                    semantic_results.append(result)
            
            if not semantic_results:
                print("❌ No chunks found for uploaded files")
                return "", []
            
            print(f"📄 Processing {len(semantic_results)} chunks from uploaded files")
            
            # SMART RANKING: Prioritize important chunks (tables, summaries, key data)
            # Add relevance scores to all chunks
            query_lower = query.lower()
            query_keywords = set(query_lower.split())
            
            for chunk in semantic_results:
                text = chunk.get('text', '')
                text_lower = text.lower()
                
                # Start with base score
                relevance_score = chunk.get('similarity_score', 0.5)
                
                # Boost for table indicators
                table_indicators = ['Land Cover Type', 'Area (Acres)', 'Percentage', 'Built-up Area', 
                                   'Forest', 'Vegetation', 'Plantation', 'Water Bodies', 'Bare Land',
                                   'Survey Analysis Results', 'Summary Statistics', 'Total Survey Area',
                                   'Carbon Credits Potential']
                indicator_count = sum(1 for indicator in table_indicators if indicator in text)
                if indicator_count > 0:
                    relevance_score += indicator_count * 0.5  # Big boost for tables
                
                # Boost for query keyword matches
                keyword_matches = sum(1 for kw in query_keywords if kw in text_lower and len(kw) > 3)
                relevance_score += keyword_matches * 0.2
                
                # Boost for page 2 (usually contains main data)
                if chunk.get('page_number', 0) == 2:
                    relevance_score += 0.3
                
                chunk['relevance_score'] = relevance_score
            
            # Sort by relevance score
            semantic_results.sort(key=lambda x: x.get('relevance_score', 0.0), reverse=True)
            
            top_scores = [f"{c.get('relevance_score', 0):.2f}" for c in semantic_results[:5]]
            print(f"📊 Top chunk relevance scores: {top_scores}")
            
            # Build comprehensive context and sources
            context_parts = []
            sources = []
            seen_content = set()  # Avoid duplicates
            
            # Take ALL chunks (or limit to reasonable size)
            max_chunks = min(len(semantic_results), 50)  # Take up to 50 chunks
            for result in semantic_results[:max_chunks]:
                text = result.get('text', '').strip()
                source_file = result.get('source_file', '')
                similarity = result.get('similarity_score', 0.0)
                
                # Skip very short or duplicate content
                if len(text) < 50 or text in seen_content:
                    continue
                
                seen_content.add(text)
                
                # Add to context with clear file attribution
                context_parts.append(f"📄 From {source_file}:\n{text}")
                
                # Create source object
                sources.append(Source(
                    filename=source_file,
                    snippet=text[:300] + "..." if len(text) > 300 else text,
                    similarity_score=similarity,
                    chunk_id=result.get('chunk_id', ''),
                    page_number=result.get('page_number', 0),
                    source_type='uploaded'
                ))
            
            if not context_parts:
                print("📁 No substantial content found in uploaded files")
                return "", []
            
            # Build final context
            file_context = "\n\n".join(context_parts)
            
            # DEDUPLICATE SOURCES: Only show each unique file once
            unique_sources = {}
            for source in sources:
                filename = source.filename
                if filename not in unique_sources:
                    # Keep the first occurrence (highest relevance)
                    unique_sources[filename] = source
            
            deduplicated_sources = list(unique_sources.values())
            
            print(f"📁 COMPREHENSIVE FILE CONTEXT BUILT:")
            print(f"   📊 Total characters: {len(file_context)}")
            print(f"   📊 Number of chunks: {len(sources)}")
            print(f"   📊 Unique files: {len(deduplicated_sources)}")
            print(f"   📊 Deduplicated: {len(sources)} → {len(deduplicated_sources)} sources")
            
            return file_context, deduplicated_sources
            
        except Exception as e:
            print(f"❌ Error extracting comprehensive file content: {e}")
            return "", []
    
    def _extract_raw_file_text(self, valid_files: List[Dict], query: str) -> Tuple[str, List[Source]]:
        """Extract raw text directly from files when vector search fails"""
        try:
            print("📄 Extracting raw text directly from uploaded files...")
            
            context_parts = []
            sources = []
            
            for file_info in valid_files:
                filename = file_info.get('filename', '')
                file_path = file_info.get('file_path', '')
                
                print(f"📄 Processing file: {filename}")
                
                # Try to read file content directly
                try:
                    if file_path and Path(file_path).exists():
                        # For text files
                        if filename.lower().endswith(('.txt', '.md', '.csv')):
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()[:5000]  # First 5000 chars
                                
                        # For other files, try to extract some metadata
                        else:
                            content = f"File: {filename} (uploaded and processed)"
                            
                        if content.strip():
                            context_parts.append(f"📄 Raw content from {filename}:\n{content}")
                            
                            sources.append(Source(
                                filename=filename,
                                snippet=content[:300] + "..." if len(content) > 300 else content,
                                similarity_score=0.7,  # Default score for raw extraction
                                chunk_id=f"raw_{hash(filename)}",
                                page_number=0,
                                source_type='uploaded'
                            ))
                            
                            print(f"✅ Extracted {len(content)} characters from {filename}")
                        
                except Exception as file_error:
                    print(f"⚠️ Could not read file {filename}: {file_error}")
                    # Create a basic acknowledgment source
                    context_parts.append(f"📄 File {filename} was uploaded and is being analyzed for: {query}")
                    sources.append(Source(
                        filename=filename,
                        snippet=f"Uploaded file: {filename}",
                        similarity_score=0.5,
                        chunk_id=f"ack_{hash(filename)}",
                        page_number=0,
                        source_type='uploaded'
                    ))
            
            if context_parts:
                file_context = "\n\n".join(context_parts)
                print(f"📄 RAW EXTRACTION SUCCESS: {len(file_context)} characters from {len(sources)} files")
                return file_context, sources
            else:
                print("📄 No raw content could be extracted")
                return "", []
                
        except Exception as e:
            print(f"❌ Error in raw file extraction: {e}")
            return "", []
    
    def _extract_session_specific_content(self, valid_files: List[Dict], query: str, session_id: str) -> Tuple[str, List[Source]]:
        """Extract content ONLY from this session's uploaded files - STRICT ISOLATION"""
        try:
            print(f"🔒 STRICT SESSION EXTRACTION for session: {session_id}")
            
            context_parts = []
            sources = []
            
            # Get ALL chunks from vector store
            query_embedding = self.embedding_processor.embed_texts_parallel([query])[0]
            all_chunks = self.vector_store.search(query_embedding, 200)  # Get many chunks
            
            # Build strict session file identifiers
            session_identifiers = set()
            for file_info in valid_files:
                filename = file_info.get('filename', '')
                file_path = file_info.get('file_path', '')
                
                # Add exact identifiers for this session
                session_identifiers.add(filename)
                session_identifiers.add(file_path)
                session_identifiers.add(f"{session_id}_{filename}")
                session_identifiers.add(f"session_{session_id}_{filename}")
                
                # Remove file extension for partial matching
                name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
                session_identifiers.add(name_without_ext)
            
            print(f"🔒 Session identifiers: {session_identifiers}")
            
            # Filter chunks to ONLY session files
            session_chunks = []
            for chunk in all_chunks:
                source_file = chunk.get('source_file', '')
                chunk_text = chunk.get('text', '')
                
                # STRICT FILTERING: Only chunks that definitely belong to this session
                is_session_chunk = False
                
                for identifier in session_identifiers:
                    if (identifier in source_file or 
                        source_file.endswith(identifier) or
                        (session_id in source_file and any(name in source_file for name in [f.get('filename', '') for f in valid_files]))):
                        is_session_chunk = True
                        break
                
                if is_session_chunk:
                    session_chunks.append(chunk)
                    print(f"✅ SESSION CHUNK: {source_file[:50]}...")
            
            print(f"🔒 Found {len(session_chunks)} chunks from session files")
            
            if not session_chunks:
                print("🚫 NO SESSION CHUNKS FOUND - Creating acknowledgment response")
                # Create acknowledgment that files exist but content extraction failed
                for file_info in valid_files:
                    filename = file_info.get('filename', '')
                    context_parts.append(f"📄 UPLOADED FILE: {filename}\n(File uploaded and processed, but specific content extraction needs refinement)")
                    
                    sources.append(Source(
                        filename=filename,
                        snippet=f"Uploaded file: {filename} - Content available for analysis",
                        similarity_score=0.9,
                        chunk_id=f"session_{session_id}_{hash(filename)}",
                        page_number=0,
                        source_type='uploaded'
                    ))
            else:
                # Process session chunks
                for chunk in session_chunks[:15]:  # Top 15 chunks
                    text = chunk.get('text', '').strip()
                    source_file = chunk.get('source_file', '')
                    
                    if text and len(text) > 50:
                        context_parts.append(f"📄 From {source_file}:\n{text}")
                        
                        sources.append(Source(
                            filename=source_file,
                            snippet=text[:300] + "..." if len(text) > 300 else text,
                            similarity_score=chunk.get('similarity_score', 0.8),
                            chunk_id=chunk.get('chunk_id', ''),
                            page_number=chunk.get('page_number', 0),
                            source_type='uploaded'
                        ))
            
            if context_parts:
                final_context = "\n\n".join(context_parts)
                print(f"🔒 SESSION EXTRACTION SUCCESS: {len(final_context)} characters from {len(sources)} sources")
                return final_context, sources
            else:
                print("🚫 No session content extracted")
                return "", []
                
        except Exception as e:
            print(f"❌ Error in session-specific extraction: {e}")
            return "", []
    
    def _is_file_topic_allowed(self, filename: str) -> bool:
        """Check if uploaded file is related to allowed blue carbon topics"""
        filename_lower = filename.lower()
        
        print(f"🔍 Checking file topic: {filename}")
        
        # Check filename for topic keywords
        for topic in self.ALLOWED_TOPICS:
            if topic.replace('_', ' ') in filename_lower or topic.replace('_', '') in filename_lower:
                print(f"✅ Matched topic: {topic}")
                return True
        
        # Additional environmental keywords (expanded)
        environmental_keywords = [
            'carbon', 'climate', 'ocean', 'marine', 'coastal', 'ecosystem', 'environment',
            'conservation', 'restoration', 'sustainability', 'wetland', 'marsh', 'mangrove',
            'seagrass', 'biodiversity', 'sequestration', 'emission', 'policy', 'management',
            'survey', 'report', 'analysis', 'scan', 'land', 'environmental', 'eco', 'green',
            'nature', 'habitat', 'species', 'forest', 'tree', 'vegetation', 'soil', 'water'
        ]
        
        for keyword in environmental_keywords:
            if keyword in filename_lower:
                print(f"✅ Matched environmental keyword: {keyword}")
                return True
        
        print(f"🚫 No matching topics found for: {filename}")
        return False
    
    def _extract_complete_file_text(self, query: str, session_id: str) -> Tuple[str, List[Source]]:
        """DIRECT TEXT EXTRACTION - Get complete file text and send to LLM"""
        try:
            print(f"📄 DIRECT TEXT EXTRACTION for session: {session_id}")
            
            # Get session files from database
            session_files = self.session_manager.get_session_files(session_id)
            if not session_files:
                print("📁 No files in session database")
                return "", []
            
            print(f"📁 Found {len(session_files)} files in session database")
            
            # Check for completed files
            completed_files = []
            processing_files = []
            
            for file_info in session_files:
                filename = file_info.get('filename', '')
                status = file_info.get('processing_status', 'pending')
                
                if status == 'completed' and self._is_file_topic_allowed(filename):
                    completed_files.append(file_info)
                    print(f"✅ Completed file: {filename}")
                elif status in ['processing', 'pending'] and self._is_file_topic_allowed(filename):
                    processing_files.append(file_info)
                    print(f"⏳ Processing file: {filename} (status: {status})")
            
            # Handle processing files
            if processing_files and not completed_files:
                print(f"⏳ {len(processing_files)} files still processing, waiting briefly...")
                time.sleep(3)  # Wait 3 seconds for processing
                
                # Check again after waiting
                session_files_updated = self.session_manager.get_session_files(session_id)
                for file_info in session_files_updated:
                    filename = file_info.get('filename', '')
                    status = file_info.get('processing_status', 'pending')
                    
                    if status == 'completed' and self._is_file_topic_allowed(filename):
                        completed_files.append(file_info)
                        print(f"✅ Now completed: {filename}")
            
            # If still processing, return status
            if not completed_files and processing_files:
                print("⏳ Files still processing, creating processing status response")
                return self._create_processing_status_response(processing_files)
            
            if not completed_files:
                print("📁 No valid completed files")
                return "", []
            
            # DIRECT APPROACH: Extract complete text from vector store
            print("📄 EXTRACTING COMPLETE TEXT from vector store...")
            
            all_file_text = []
            all_sources = []
            
            for file_info in completed_files:
                filename = file_info.get('filename', '')
                print(f"📄 Extracting complete text from: {filename}")
                
                # Get ALL chunks for this file from vector store
                complete_text, file_sources = self._get_complete_file_text_from_vector_store(filename, session_id)
                
                if complete_text:
                    all_file_text.append(f"📄 COMPLETE TEXT FROM {filename}:\n{complete_text}")
                    all_sources.extend(file_sources)
                    print(f"✅ Extracted {len(complete_text)} characters from {filename}")
                else:
                    print(f"❌ No text extracted from {filename}")
            
            if all_file_text:
                # Combine all file text
                complete_context = "\n\n" + "="*100 + "\n\n".join(all_file_text)
                print(f"📄 COMPLETE TEXT EXTRACTION SUCCESS: {len(complete_context)} total characters")
                return complete_context, all_sources
            else:
                print("❌ No complete text extracted")
                return "", []
                
        except Exception as e:
            print(f"❌ Error in complete text extraction: {e}")
            return "", []
    
    def _get_complete_file_text_from_vector_store(self, filename: str, session_id: str) -> Tuple[str, List[Source]]:
        """Get ALL text chunks for a specific file from vector store"""
        try:
            print(f"🔍 Getting ALL chunks for file: {filename}")
            
            # Search vector store with a generic query to get all chunks
            query_embedding = self.embedding_processor.embed_texts_parallel(["document content analysis"])[0]
            all_results = self.vector_store.search(query_embedding, 500)  # Get many results
            
            # Use FileChunkMatcher for precise matching
            file_matcher = get_file_chunk_matcher()
            file_chunks = file_matcher.find_chunks_for_file(filename, all_results)
            
            if not file_chunks:
                print(f"❌ No chunks found for {filename}")
                return "", []
            
            print(f"📄 Found {len(file_chunks)} chunks for {filename}")
            
            # Sort chunks by page number and chunk order
            file_chunks.sort(key=lambda x: (x.get('page_number', 0), x.get('chunk_id', '')))
            
            # Extract ALL text content
            all_text_parts = []
            sources = []
            
            for chunk in file_chunks:
                text = chunk.get('text', '').strip()
                if text and len(text) > 20:  # Skip very short chunks
                    all_text_parts.append(text)
                    
                    # Create source
                    sources.append(Source(
                        filename=filename,
                        snippet=text[:200] + "..." if len(text) > 200 else text,
                        similarity_score=chunk.get('similarity_score', 0.9),
                        chunk_id=chunk.get('chunk_id', ''),
                        page_number=chunk.get('page_number', 0),
                        source_type='uploaded'
                    ))
            
            if all_text_parts:
                # Join all text parts to create complete document text
                complete_text = "\n\n".join(all_text_parts)
                print(f"📄 Complete text assembled: {len(complete_text)} characters from {len(all_text_parts)} chunks")
                return complete_text, sources
            else:
                return "", []
                
        except Exception as e:
            print(f"❌ Error getting complete file text: {e}")
            return "", []
    
    def _extract_files_directly(self, query: str, session_id: str) -> Tuple[str, List[Source]]:
        """ROBUST FILE EXTRACTION - Find uploaded files in vector store"""
        try:
            print(f"📁 ROBUST EXTRACTION for session: {session_id}")
            
            # Get session files from database
            session_files = self.session_manager.get_session_files(session_id)
            if not session_files:
                print("📁 No files in session database")
                return "", []
            
            print(f"📁 Found {len(session_files)} files in session database")
            
            # Check file processing status and handle accordingly
            completed_files = []
            processing_files = []
            
            for file_info in session_files:
                filename = file_info.get('filename', '')
                status = file_info.get('processing_status', 'pending')
                
                if status == 'completed' and self._is_file_topic_allowed(filename):
                    completed_files.append(file_info)
                    print(f"✅ Completed file: {filename}")
                elif status in ['processing', 'pending'] and self._is_file_topic_allowed(filename):
                    processing_files.append(file_info)
                    print(f"⏳ Processing file: {filename} (status: {status})")
                else:
                    print(f"🚫 Skipping: {filename} (status: {status})")
            
            # If files are still processing, wait briefly and check again
            if processing_files and not completed_files:
                print(f"⏳ {len(processing_files)} files still processing, waiting briefly...")
                time.sleep(2)  # Wait 2 seconds for processing
                
                # Check again after waiting
                session_files_updated = self.session_manager.get_session_files(session_id)
                for file_info in session_files_updated:
                    filename = file_info.get('filename', '')
                    status = file_info.get('processing_status', 'pending')
                    
                    if status == 'completed' and self._is_file_topic_allowed(filename):
                        completed_files.append(file_info)
                        print(f"✅ Now completed: {filename}")
            
            # If still no completed files but processing files exist
            if not completed_files and processing_files:
                print("⏳ Files still processing, creating processing status response")
                return self._create_processing_status_response(processing_files)
            
            if not completed_files:
                print("📁 No valid completed files")
                return "", []
            
            valid_files = completed_files
            
            # ROBUST SEARCH: Find uploaded files in vector store
            print("🔍 ROBUST SEARCH: Looking for uploaded files in vector store...")
            
            # Get query embedding
            query_embedding = self.embedding_processor.embed_texts_parallel([query])[0]
            
            # Search vector store with high limit
            all_results = self.vector_store.search(query_embedding, 200)
            print(f"🔍 Got {len(all_results)} total results from vector store")
            
            # Find uploaded file chunks using multiple strategies
            uploaded_chunks = []
            
            for result in all_results:
                source_file = result.get('source_file', '')
                
                # Strategy 1: Look for "uploads/" prefix
                if source_file.startswith('uploads/'):
                    uploaded_chunks.append(result)
                    print(f"✅ FOUND UPLOAD: {source_file}")
                    continue
                
                # Strategy 2: Look for session files by name
                for file_info in valid_files:
                    filename = file_info.get('filename', '')
                    # Remove extension for matching
                    base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                    
                    if (filename in source_file or 
                        base_name in source_file or
                        any(part in source_file for part in filename.split('_')[:3])):
                        uploaded_chunks.append(result)
                        print(f"✅ MATCHED FILE: {source_file} → {filename}")
                        break
            
            print(f"🔍 Found {len(uploaded_chunks)} chunks from uploaded files")
            
            if not uploaded_chunks:
                print("❌ No uploaded file chunks found in vector store")
                return self._create_fallback_file_response(valid_files)
            
            # Sort by relevance and extract content
            uploaded_chunks.sort(key=lambda x: x.get('similarity_score', 0.0), reverse=True)
            
            # Group chunks by source file
            file_chunks = {}
            for chunk in uploaded_chunks:
                source_file = chunk.get('source_file', '')
                if source_file not in file_chunks:
                    file_chunks[source_file] = []
                file_chunks[source_file].append(chunk)
            
            # Build comprehensive content
            all_content = []
            all_sources = []
            
            for source_file, chunks in file_chunks.items():
                print(f"📄 Processing {len(chunks)} chunks from: {source_file}")
                
                # Sort chunks by page number
                chunks.sort(key=lambda x: (x.get('page_number', 0), x.get('chunk_id', '')))
                
                # Extract text content
                file_content_parts = []
                for chunk in chunks[:15]:  # Top 15 chunks per file
                    text = chunk.get('text', '').strip()
                    if text and len(text) > 30:
                        file_content_parts.append(text)
                        
                        # Create source
                        all_sources.append(Source(
                            filename=source_file,
                            snippet=text[:300] + "..." if len(text) > 300 else text,
                            similarity_score=chunk.get('similarity_score', 0.8),
                            chunk_id=chunk.get('chunk_id', ''),
                            page_number=chunk.get('page_number', 0),
                            source_type='uploaded'
                        ))
                
                if file_content_parts:
                    file_content = "\n\n".join(file_content_parts)
                    all_content.append(f"📄 UPLOADED FILE: {source_file}\n{file_content}")
                    print(f"✅ Extracted {len(file_content)} chars from {source_file}")
            
            if all_content:
                final_context = "\n\n" + "="*80 + "\n\n".join(all_content)
                print(f"📁 ROBUST EXTRACTION SUCCESS: {len(final_context)} total characters from {len(file_chunks)} files")
                return final_context, all_sources
            else:
                print("❌ No content extracted from uploaded files")
                return self._create_fallback_file_response(valid_files)
                
        except Exception as e:
            print(f"❌ Error in robust file extraction: {e}")
            return "", []
    
    def _create_fallback_file_response(self, valid_files: List[Dict]) -> Tuple[str, List[Source]]:
        """Create fallback response when file extraction fails"""
        try:
            print("🔧 Creating fallback file response")
            
            content_parts = []
            sources = []
            
            for file_info in valid_files:
                filename = file_info.get('filename', '')
                content_parts.append(f"📄 UPLOADED FILE: {filename}\n(File has been uploaded and processed. Content extraction in progress.)")
                
                sources.append(Source(
                    filename=filename,
                    snippet=f"Uploaded file: {filename} - Processing completed",
                    similarity_score=0.9,
                    chunk_id=f"fallback_{hash(filename)}",
                    page_number=0,
                    source_type='uploaded'
                ))
            
            if content_parts:
                fallback_context = "\n\n".join(content_parts)
                print(f"🔧 Fallback response created for {len(valid_files)} files")
                return fallback_context, sources
            else:
                return "", []
                
        except Exception as e:
            print(f"❌ Error creating fallback response: {e}")
            return "", []
    
    def _create_processing_status_response(self, processing_files: List[Dict]) -> Tuple[str, List[Source]]:
        """Create response when files are still being processed"""
        try:
            print("⏳ Creating processing status response")
            
            filenames = [f.get('filename', 'Unknown') for f in processing_files]
            
            content = f"""⏳ **Your file{'s' if len(filenames) > 1 else ''} {'are' if len(filenames) > 1 else 'is'} currently being processed!**

📄 **Processing**: {', '.join(filenames)}

🔄 **Status**: Your file{'s' if len(filenames) > 1 else ''} {'are' if len(filenames) > 1 else 'is'} being analyzed and indexed. This usually takes 30-60 seconds.

**What's happening:**
• 📖 Extracting text content from your PDF
• 🧠 Creating intelligent embeddings  
• 💾 Indexing for fast retrieval
• ✅ Preparing for comprehensive analysis

**Please try again in a moment!** Once processing is complete, I'll be able to provide detailed analysis of your uploaded file{'s' if len(filenames) > 1 else ''}. 🌊"""

            sources = []
            for file_info in processing_files:
                filename = file_info.get('filename', '')
                sources.append(Source(
                    filename=filename,
                    snippet=f"File processing: {filename}",
                    similarity_score=0.9,
                    chunk_id=f"processing_{hash(filename)}",
                    page_number=0,
                    source_type='uploaded'
                ))
            
            print(f"⏳ Processing status response created for {len(processing_files)} files")
            return content, sources
            
        except Exception as e:
            print(f"❌ Error creating processing status response: {e}")
            return "", []
    
    def _get_file_specific_content(self, filename: str, session_id: str, query: str) -> Tuple[str, List[Source]]:
        """Get content for a specific file only"""
        try:
            # Create session-specific search
            query_embedding = self.embedding_processor.embed_texts_parallel([query])[0]
            
            # Search vector store
            all_results = self.vector_store.search(query_embedding, 100)
            
            # Filter ONLY for this specific file
            file_chunks = []
            for result in all_results:
                source_file = result.get('source_file', '')
                
                # VERY STRICT: Only exact filename matches
                if (filename == source_file or 
                    source_file.endswith(f"/{filename}") or
                    source_file.endswith(f"_{filename}") or
                    (filename.replace('.pdf', '') in source_file and session_id in source_file)):
                    file_chunks.append(result)
                    print(f"✅ MATCHED CHUNK: {source_file}")
            
            if not file_chunks:
                print(f"❌ No chunks found for {filename}")
                return "", []
            
            # Sort and combine chunks
            file_chunks.sort(key=lambda x: (x.get('page_number', 0), x.get('chunk_id', '')))
            
            content_parts = []
            sources = []
            
            for chunk in file_chunks[:20]:  # Top 20 chunks
                text = chunk.get('text', '').strip()
                if text and len(text) > 30:
                    content_parts.append(text)
                    
                    sources.append(Source(
                        filename=filename,
                        snippet=text[:300] + "..." if len(text) > 300 else text,
                        similarity_score=chunk.get('similarity_score', 0.8),
                        chunk_id=chunk.get('chunk_id', ''),
                        page_number=chunk.get('page_number', 0),
                        source_type='uploaded'
                    ))
            
            if content_parts:
                file_content = "\n\n".join(content_parts)
                return file_content, sources
            else:
                return "", []
                
        except Exception as e:
            print(f"❌ Error getting content for {filename}: {e}")
            return "", []
    
    def _get_comprehensive_file_content(self, query: str, session_id: str) -> Tuple[str, List[Source]]:
        """Get COMPREHENSIVE content from uploaded files - not just relevant chunks"""
        try:
            print(f"📁 Getting COMPREHENSIVE file content for session: {session_id}")
            
            # Get session files
            session_files = self.session_manager.get_session_files(session_id)
            if not session_files:
                print("📁 No uploaded files in session")
                return "", []
            
            # Validate and filter files
            valid_files = []
            for file_info in session_files:
                filename = file_info.get('filename', '')
                processing_status = file_info.get('processing_status', 'pending')
                
                if processing_status != 'completed':
                    print(f"⏳ File still processing: {filename}")
                    continue
                
                if self._is_file_topic_allowed(filename):
                    valid_files.append(file_info)
                    print(f"✅ File validated: {filename}")
                else:
                    print(f"🚫 File rejected - not blue carbon related: {filename}")
            
            if not valid_files:
                print("📁 No valid completed files available")
                return "", []
            
            print(f"📁 Processing {len(valid_files)} files for COMPREHENSIVE extraction")
            
            # Get ALL content from uploaded files (not just query-relevant)
            all_file_content = []
            all_sources = []
            
            # Get query embedding for some relevance scoring
            query_embedding = self.embedding_processor.embed_texts_parallel([query])[0]
            
            # Search vector store for ALL chunks from these files
            all_results = self.vector_store.search(query_embedding, 100)  # Get more chunks
            
            # Group chunks by file - STRICT SESSION ISOLATION
            file_chunks = {}
            session_file_paths = set()
            
            # Build exact file paths for this session
            for file_info in valid_files:
                filename = file_info.get('filename', '')
                file_path = file_info.get('file_path', '')
                session_file_paths.add(filename)
                session_file_paths.add(file_path)
                # Add variations
                session_file_paths.add(f"uploads/{session_id}/{filename}")
                session_file_paths.add(f"session_{session_id}_{filename}")
            
            print(f"🔒 STRICT ISOLATION: Looking for files: {session_file_paths}")
            
            for result in all_results:
                source_file = result.get('source_file', '')
                
                # STRICT MATCHING: Only exact matches for session files
                matched_file = None
                for file_info in valid_files:
                    filename = file_info.get('filename', '')
                    file_path = file_info.get('file_path', '')
                    
                    # Very strict matching - must be exact or contain session ID
                    if (source_file == filename or 
                        source_file == file_path or
                        source_file.endswith(f"/{filename}") or
                        source_file.endswith(f"_{filename}") or
                        (session_id in source_file and filename in source_file)):
                        matched_file = filename
                        break
                
                if matched_file:
                    if matched_file not in file_chunks:
                        file_chunks[matched_file] = []
                    file_chunks[matched_file].append(result)
                    print(f"✅ MATCHED: {source_file} → {matched_file}")
                else:
                    # Debug: Show what files are being rejected
                    if any(keyword in source_file.lower() for keyword in ['carbon', 'blue', 'restoration']):
                        print(f"🚫 REJECTED (not session file): {source_file}")
            
            print(f"🔒 STRICT ISOLATION RESULT: Found {len(file_chunks)} session files with content")
            
            # Extract comprehensive content from each file
            for filename, chunks in file_chunks.items():
                print(f"📄 Extracting comprehensive content from {filename}: {len(chunks)} chunks")
                
                # Sort chunks by page number and position
                chunks.sort(key=lambda x: (x.get('page_number', 0), x.get('chunk_id', '')))
                
                # Combine chunks to get comprehensive file content
                file_text_parts = []
                for chunk in chunks[:20]:  # Take up to 20 chunks per file for comprehensive coverage
                    text = chunk.get('text', '').strip()
                    if text and len(text) > 30:  # Skip very short chunks
                        file_text_parts.append(text)
                
                if file_text_parts:
                    comprehensive_content = "\n\n".join(file_text_parts)
                    all_file_content.append(f"📄 COMPLETE CONTENT FROM {filename}:\n{comprehensive_content}")
                    
                    # Create sources for this file
                    for i, chunk in enumerate(chunks[:10]):  # Top 10 chunks as sources
                        all_sources.append(Source(
                            filename=filename,
                            snippet=chunk.get('text', '')[:300] + "..." if len(chunk.get('text', '')) > 300 else chunk.get('text', ''),
                            similarity_score=chunk.get('similarity_score', 0.8),
                            chunk_id=chunk.get('chunk_id', ''),
                            page_number=chunk.get('page_number', 0),
                            source_type='uploaded'
                        ))
                    
                    print(f"✅ Extracted {len(comprehensive_content)} characters from {filename}")
            
            if not all_file_content:
                print("📁 No comprehensive content extracted - trying session-specific extraction")
                return self._extract_session_specific_content(valid_files, query, session_id)
            
            # Combine all file content
            final_context = "\n\n" + "="*50 + "\n\n".join(all_file_content)
            
            print(f"📁 COMPREHENSIVE FILE EXTRACTION SUCCESS:")
            print(f"   📊 Total characters: {len(final_context)}")
            print(f"   📊 Files processed: {len(file_chunks)}")
            print(f"   📊 Total sources: {len(all_sources)}")
            
            return final_context, all_sources
            
        except Exception as e:
            print(f"❌ Error getting comprehensive file content: {e}")
            return "", []
    
    def _is_welcome_message(self, query: str) -> bool:
        """Check if query is a welcome/greeting message"""
        query_lower = query.lower().strip()
        welcome_patterns = [
            'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening',
            'welcome', 'start', 'begin', 'help', 'what can you do', 'how are you', 'thanks', 'thank you'
        ]
        return any(pattern in query_lower for pattern in welcome_patterns) and len(query.split()) <= 5
    
    def _create_welcome_response(self, query: str, session_id: str, start_time: float) -> ResponseData:
        """Create a file processing status response"""
        try:
            # Check if files are uploaded and their processing status
            session_files = self.session_manager.get_session_files(session_id)
            
            if not session_files:
                # No files uploaded yet
                welcome_response = """**BlueCarbon-LEDGER Ready! 🌊**

I'm your specialized environmental intelligence assistant. Upload a PDF file to get started with analysis.

**Supported formats:** PDF, DOCX, TXT, CSV

**What I can help with:**
• Blue Carbon ecosystems analysis
• Environmental data interpretation  
• Carbon credits and offsetting
• Coastal restoration insights

📎 **Upload a file to begin analysis**"""
            else:
                # Check processing status of uploaded files
                processing_files = [f for f in session_files if f.get('processing_status') == 'pending']
                completed_files = [f for f in session_files if f.get('processing_status') == 'completed']
                
                if processing_files:
                    file_names = [f['filename'] for f in processing_files]
                    welcome_response = f"""**🔄 File Processing in Progress**

BlueCarbon-LEDGER is currently processing your uploaded file(s):

📄 **Processing:** {', '.join(file_names)}

⏳ **Status:** Your file is being analyzed and indexed. This usually takes 1-2 minutes.

💡 **What's happening:**
• Extracting text and data from your file
• Creating searchable chunks
• Building knowledge index

✅ **You'll be notified when processing is complete and ready for questions!**"""
                elif completed_files:
                    file_names = [f['filename'] for f in completed_files]
                    chunks_total = sum(f.get('chunks_processed', 0) for f in completed_files)
                    welcome_response = f"""**✅ File Processing Complete!**

BlueCarbon-LEDGER has successfully processed your file(s):

📄 **Ready for analysis:** {', '.join(file_names)}
📊 **Processed:** {chunks_total} text chunks indexed

🎯 **You can now ask questions about your uploaded content!**

**Try asking:**
• "Summarize the key findings"
• "What are the main conclusions?"
• "Analyze the data trends"
• "Extract important statistics"

💬 **Start your analysis by typing a question below**"""
                else:
                    # Fallback
                    welcome_response = """**BlueCarbon-LEDGER Ready! 🌊**

Upload a file to begin environmental analysis."""
            
            # Save to conversation memory
            self._save_conversation_memory(session_id, query, welcome_response, [])
            
            return ResponseData(
                answer=welcome_response,
                sources=[],
                web_images=[],
                suggestions=self._generate_welcome_suggestions(),
                confidence_score=1.0,
                retrieval_time=time.time() - start_time,
                response_type="File Processing Status"
            )
            
        except Exception as e:
            print(f"❌ Error creating file status response: {e}")
            return ResponseData(
                answer=self._create_default_welcome(),
                sources=[],
                web_images=[],
                suggestions=self._generate_welcome_suggestions(),
                confidence_score=1.0,
                retrieval_time=time.time() - start_time,
                response_type="Default Welcome"
            )
    
    def _is_question_about_uploaded_file(self, query: str) -> bool:
        """Determine if the question is about the uploaded file or general knowledge"""
        query_lower = query.lower()
        
        # File-specific indicators
        file_indicators = [
            'this file', 'this pdf', 'this document', 'this report',
            'my file', 'my pdf', 'my document', 'my report',
            'the file', 'the pdf', 'the document', 'the report',
            'uploaded', 'analyze', 'in this', 'from this',
            'how much', 'what is in', 'tell me about this',
            'credits i get', 'my survey', 'my data'
        ]
        
        # General knowledge indicators
        general_indicators = [
            'what is blue carbon', 'how does blue carbon work',
            'explain blue carbon', 'tell me about blue carbon',
            'what are carbon credits', 'how do carbon credits work',
            'define', 'explain the concept', 'in general'
        ]
        
        # Check for file-specific indicators
        has_file_indicator = any(indicator in query_lower for indicator in file_indicators)
        
        # Check for general knowledge indicators
        has_general_indicator = any(indicator in query_lower for indicator in general_indicators)
        
        # If has file indicator and no general indicator, it's about the file
        if has_file_indicator and not has_general_indicator:
            return True
        
        # If has general indicator, it's general knowledge
        if has_general_indicator:
            return False
        
        # Default: if user has uploaded files and asks a question, assume it's about the file
        # This is the ChatGPT behavior - prioritize uploaded content
        return True
    
    def _is_specific_filename_mentioned_without_upload(self, query: str, session_id: str) -> bool:
        """Check if user is mentioning a SPECIFIC filename (like report.pdf) but hasn't uploaded it"""
        import re
        
        # Only trigger if query contains a SPECIFIC filename pattern (word + extension)
        # Examples: "report.pdf", "document.docx", "data.csv"
        filename_pattern = r'\b[A-Za-z0-9_\-]+\.(pdf|docx|txt|csv|doc|xlsx)\b'
        has_specific_filename = re.search(filename_pattern, query, re.IGNORECASE)
        
        if not has_specific_filename:
            return False
        
        # Check if there are any files in this session
        session_files = self.session_manager.get_session_files(session_id)
        completed_files = [f for f in session_files if f.get('processing_status') == 'completed']
        
        # Only show upload reminder if:
        # 1. User mentions a specific filename (e.g., "analyze report.pdf")
        # 2. AND they have NO uploaded files in this session
        return len(completed_files) == 0
    
    def _create_upload_reminder_response(self, query: str, session_id: str, start_time: float) -> ResponseData:
        """Create a helpful response reminding user to upload the file"""
        # Extract potential filename from query
        import re
        filename_match = re.search(r'([A-Za-z0-9_\-]+\.(pdf|docx|txt|csv|doc|xlsx))', query, re.IGNORECASE)
        filename = filename_match.group(1) if filename_match else "your file"
        
        response = f"""📎 **Please Upload Your File First!**

I noticed you mentioned **{filename}** in your message, but I don't see it uploaded yet.

**To analyze your file, please:**

1. 📤 **Click the attachment icon** (📎) in the chat input below
2. 📁 **Select your file** from your computer
3. ⏳ **Wait 5-10 seconds** for processing
4. 💬 **Ask your question** again

**Supported file types:**
- 📄 PDF documents
- 📝 Word documents (DOCX, DOC)
- 📊 Excel files (XLSX, CSV)
- 📃 Text files (TXT)

Once you upload **{filename}**, I'll be able to analyze it thoroughly and provide detailed insights based on its content! 🌊

**Need help?** Just upload your file and ask: "analyze this file" or "what's in this document?"
"""
        
        # Save to conversation memory
        self._save_conversation_memory(session_id, query, response, [])
        
        return ResponseData(
            answer=response,
            sources=[],
            web_images=[],
            suggestions=[
                "How do I upload a file?",
                "What file types do you support?",
                "Can you analyze PDF documents?"
            ],
            confidence_score=1.0,
            retrieval_time=time.time() - start_time,
            response_type="Upload Reminder"
        )
    
    def _create_default_welcome(self) -> str:
        """Create default welcome message"""
        return """🌊 **Welcome to BlueCarbon AI!** 

I'm your specialized environmental intelligence assistant focused on:

• **Blue Carbon Ecosystems** 🌱 (mangroves, seagrass, salt marshes)
• **Carbon Credits & Markets** 💰
• **Coastal Restoration** 🏖️
• **Marine Conservation** 🐟

**What I can do:**
✅ Analyze your uploaded files (PDF, DOCX, TXT, CSV)
✅ Answer questions about blue carbon and environmental topics
✅ Provide comprehensive research and data analysis
✅ Help with carbon credit calculations and assessments

**Ready to help!** Feel free to ask questions or upload your blue carbon related documents! 🚀"""
    
    def _generate_welcome_suggestions(self) -> List[str]:
        """Generate welcome suggestions"""
        return [
            "Upload a blue carbon research document for analysis",
            "How do blue carbon ecosystems work?",
            "Calculate carbon credits from coastal restoration"
        ]
    
    def _answer_from_file_primary(self, query: str, combined_context: str, file_sources: List[Source], dataset_sources: List[Source]) -> str:
        """Answer primarily from uploaded file with dataset only for structuring"""
        try:
            system_prompt = """You are "BlueCarbon AI" — a specialized environmental intelligence assistant.

CRITICAL INSTRUCTIONS - UPLOADED FILE ONLY:
1. **MANDATORY FILE-ONLY RULE**: Answer EXCLUSIVELY from the user's uploaded file content shown in the PRIMARY SOURCE section
2. **NEVER REFERENCE OTHER FILES**: Do not mention any files other than the user's uploaded file
3. **NO EXTERNAL KNOWLEDGE**: Do not add information from other documents or general knowledge unless explicitly for technical explanations
4. **SPECIFIC FILE ANALYSIS**: Extract and analyze ONLY the data, numbers, and findings from the uploaded file
5. **FILE NAME ACCURACY**: Only reference the actual uploaded file name, never mention other documents
6. **RICH FORMATTING**: Use emojis 🌊, **bold** text, tables, bullet points for readability

STRICT RESPONSE RULES:
- Answer ONLY from the PRIMARY SOURCE (uploaded file) content
- If the uploaded file doesn't contain the requested information, say so clearly
- Never reference methodologies or documents not in the uploaded file
- Focus exclusively on the specific uploaded file content
- Use supporting context only for technical term explanations"""

            user_prompt = f"""User Question: {query}

CONTEXT (File Primary + Structure Support):
{combined_context}

INSTRUCTIONS:
- Answer PRIMARILY from the uploaded file content (first section)
- Use the supporting context only for structuring and explaining technical terms
- Extract ALL relevant details, numbers, and findings from the file
- Be comprehensive and detailed about the file content
- Use engaging formatting with emojis and **bold** text

Provide a comprehensive response that prioritizes the uploaded file information."""

            response = self.groq_client.complete(f"{system_prompt}\n\n{user_prompt}")
            return response
            
        except Exception as e:
            print(f"❌ Error generating file-primary response: {e}")
            return self._create_file_fallback_response(query, file_sources)
    
    def _answer_from_uploaded_files_only(self, query: str, file_context: str, file_sources: List[Source]) -> str:
        """Answer EXCLUSIVELY from uploaded files - COMPLETE TEXT ANALYSIS"""
        try:
            # Get the actual uploaded filenames
            uploaded_filenames = list(set([source.filename for source in file_sources]))
            
            print(f"📄 COMPLETE TEXT ANALYSIS for files: {uploaded_filenames}")
            print(f"📄 Total context length: {len(file_context)} characters")
            
            system_prompt = """You are an intelligent AI assistant that combines data extraction with expert knowledge. You provide helpful, well-formatted responses.

🎯 YOUR DUAL ROLE:

1. **DATA EXTRACTOR** - Find and extract exact data from the uploaded file
2. **EXPERT ADVISOR** - Apply your knowledge to interpret, explain, and provide context

📋 CRITICAL FORMATTING RULES:

✅ ALWAYS USE MARKDOWN:
- **Bold** for important numbers and terms
- Bullet points (•) for lists
- Line breaks between sections
- Clear structure

✅ RESPONSE STRUCTURE:
1. Brief intro (1 sentence)
2. Main answer with data (formatted with bullets/bold)
3. Additional context or explanation if helpful

❌ NEVER:
- Write long unformatted paragraphs
- Mix all data together without structure
- Skip line breaks
- Paste raw text from file

🔍 HOW TO ANSWER QUESTIONS:

**Type 1: Data Questions** (e.g., "what is land cover?", "how much area?")
→ Extract data from file + format nicely

**Type 2: Concept Questions** (e.g., "what is blue carbon?", "how does it work?")
→ Use your expert knowledge + reference file if relevant

**Type 3: Calculation Questions** (e.g., "calculate credits", "how much can I earn?")
→ Extract data from file + apply formulas + show work

📊 FORMATTING EXAMPLES:

User: "what is land cover distribution?"

✅ GOOD (Well-formatted):
"Based on your survey report, here's the land cover distribution:

• **Built-up Area**: 0.156 acres (65.0%)
• **Forest/Vegetation**: 0.048 acres (20.0%)
• **Plantation**: 0.024 acres (10.0%)
• **Water Bodies**: 0.007 acres (3.0%)
• **Bare Land**: 0.005 acres (2.0%)

**Total Survey Area**: 0.240 acres"

❌ BAD (Unformatted):
"LAND COVER CLASSIFICATION RESULTS The report provides a land cover classification of the surveyed area. Based on this classification, I extracted the relevant data for calculating credits as per area: | Land Cover Type | Area | Percentage | | --- | --- | --- | | Built-up Area | 0.156 acres | 65.0% | | Forest/Vegetation | 0.048 acres | 20.0% |..."

User: "what is blue carbon?"

✅ GOOD (Expert knowledge):
"Blue carbon refers to carbon captured and stored by coastal and marine ecosystems, including:

• **Mangroves** - Coastal trees that store carbon in roots and soil
• **Seagrass meadows** - Underwater plants that sequester CO2
• **Salt marshes** - Coastal wetlands with high carbon storage

These ecosystems are highly effective at carbon sequestration, often storing more carbon per unit area than terrestrial forests."

User: "calculate credits"

✅ GOOD (Data + calculation):
"Based on your survey data, here's the carbon credit calculation:

**Land Cover Data**:
• Forest/Vegetation: 0.048 acres (20.0%)
• Plantation: 0.024 acres (10.0%)

**Calculation**:
• Forest: 0.048 acres × 1 ton CO2e/acre = **0.048 tons CO2e**
• Plantation: 0.024 acres × 0.5 ton CO2e/acre = **0.012 tons CO2e**

**Total Credits**: **0.060 tons CO2e per year**
**Credits per Acre**: 0.25 tons CO2e/acre"

🎯 KEY PRINCIPLES:

1. **Extract data accurately** from the file
2. **Format beautifully** with markdown
3. **Apply intelligence** when needed
4. **Be conversational** but structured
5. **Use line breaks** generously
"Based on your survey report, here's the **land cover distribution**:

**Land Cover Classification:**
• **Built-up Area**: 0.156 acres (65.0%)
• **Forest/Vegetation**: 0.048 acres (20.0%)
• **Plantation**: 0.024 acres (10.0%)
• **Water Bodies**: 0.007 acres (3.0%)
• **Bare Land**: 0.005 acres (2.0%)

**Total Survey Area**: 0.240 acres

The majority of your surveyed area is built-up (65%), with forest/vegetation covering 20% of the land."

---

User: "calculate credits as per area"

✅ EXCELLENT:
"Based on your survey data, here's the **carbon credit calculation**:

**Land Cover Data:**
• Forest/Vegetation: 0.048 acres (20.0%)
• Plantation: 0.024 acres (10.0%)

**Carbon Sequestration Rates** (standard forestry models):
• Forest/Vegetation: ~1 ton CO2e/acre/year
• Plantation: ~0.5 ton CO2e/acre/year

**Calculation:**
• Forest: 0.048 acres × 1 ton = **0.048 tons CO2e/year**
• Plantation: 0.024 acres × 0.5 ton = **0.012 tons CO2e/year**

**Total Credits**: **0.060 tons CO2e/year**
**Credits per Acre**: 0.060 ÷ 0.240 = **0.25 tons CO2e/acre/year**

Note: These are estimates based on standard forestry models. Actual rates may vary based on vegetation type, age, and local conditions."

---

User: "what is blue carbon?"

✅ EXCELLENT (using intelligence for general question):
"**Blue carbon** refers to carbon captured and stored by coastal and marine ecosystems, including:

• **Mangroves** - Coastal trees that store carbon in biomass and sediment
• **Seagrass meadows** - Underwater plants that sequester carbon
• **Salt marshes** - Coastal wetlands with high carbon storage

**Why it matters:**
These ecosystems can store carbon **10x more efficiently** than terrestrial forests per unit area, making them crucial for climate change mitigation.

**In your context:** If your survey area includes coastal wetlands or mangroves, it could have significant blue carbon potential for carbon credit generation."

🎯 KEY PRINCIPLES:

1. **Extract data first** - Always check file content
2. **Use your intelligence** - Apply knowledge when needed
3. **Format beautifully** - Make responses easy to read
4. **Be helpful** - Combine data + expertise
5. **Stay accurate** - Don't make up data, but do explain concepts

REMEMBER: You're not just extracting data - you're an intelligent assistant that helps users understand their files AND provides expert knowledge when needed!"""

            user_prompt = f"""📄 **UPLOADED FILE**: {', '.join(uploaded_filenames)}

🔍 **USER QUESTION**: "{query}"

📋 **FILE CONTENT** (search through this):
{file_context}

---

⚡ **YOUR TASK**:

1. **Search the file content** for data related to the question
2. **Extract exact data** (tables, numbers, measurements)
3. **Apply your intelligence**:
   - If it's a data question → extract and present the data
   - If it needs calculation → do the math and explain
   - If it needs outside knowledge → use your expertise
   - If it's a general question → answer with your knowledge + file context

4. **Format beautifully**:
   - Use **bold** for important terms
   - Use bullet points (•) for lists
   - Add line breaks between sections
   - Make it easy to read

5. **Be intelligent**:
   - Don't just dump data - explain it
   - Add context when helpful
   - Show calculations if needed
   - Combine file data + your expertise

📊 **NOW ANSWER** (remember: beautiful formatting + intelligence):"""

            response = self.groq_client.complete(f"{system_prompt}\n\n{user_prompt}")
            
            # AGGRESSIVE CLEANING: Remove any dataset mentions
            response = self._clean_external_references(response, uploaded_filenames)
            
            # FINAL CHECK: Force remove any remaining dataset mentions
            response = self._force_remove_dataset_mentions(response)
            
            # FORCE FORMAT: Ensure response has proper line breaks and structure
            response = self._force_format_response(response)
            
            print(f"📄 COMPLETE ANALYSIS GENERATED: {len(response)} characters")
            
            return response
            
        except Exception as e:
            print(f"❌ Error generating complete file analysis: {e}")
            return self._create_file_fallback_response(query, file_sources)
    
    def _clean_external_references(self, response: str, uploaded_filenames: List[str]) -> str:
        """Aggressively remove any references to external files or methodologies"""
        try:
            print("🧹 CLEANING external references from response...")
            
            # Aggressive external reference patterns
            external_patterns = [
                # Remove any mention of "Blue Carbon Knowledge Dataset"
                r'Based on the provided context from the uploaded files and the Blue Carbon Knowledge Dataset[^.]*\.?',
                r'from the uploaded files and the Blue Carbon Knowledge Dataset[^.]*\.?',
                r'and the Blue Carbon Knowledge Dataset[^.]*\.?',
                r'Blue Carbon Knowledge Dataset[^.]*\.?',
                r'the dataset[^.]*\.?',
                r'from.*?dataset[^.]*\.?',
                r'using.*?dataset[^.]*\.?',
                # Remove methodology references
                r'VM\d+[^.\s]*\.pdf',  # VM methodology files
                r'VM\d+[^.\s]*-[^.\s]*\.pdf',  # VM methodology variations
                r'according to.*?methodology[^.]*\.?',
                r'refer to.*?methodology[^.]*\.?',
                r'based on.*?standard[^.]*\.?',
                r'following.*?protocol[^.]*\.?',
                r'methodology.*?provided[^.]*\.?',
                r'refer to the methodology[^.]*\.?',
                r'VM\d+.*?Methodology[^.]*\.?',
                r'Methodology-for-[^.]*\.pdf',
                r'we need to refer to[^.]*methodology[^.]*\.?'
            ]
            
            cleaned_response = response
            original_length = len(cleaned_response)
            
            for pattern in external_patterns:
                matches = re.findall(pattern, cleaned_response, flags=re.IGNORECASE)
                if matches:
                    print(f"🧹 REMOVING: {matches}")
                cleaned_response = re.sub(pattern, '', cleaned_response, flags=re.IGNORECASE)
            
            # Clean up extra spaces and punctuation
            cleaned_response = re.sub(r'\s+', ' ', cleaned_response)  # Multiple spaces
            cleaned_response = re.sub(r'\.\s*\.', '.', cleaned_response)  # Double periods
            cleaned_response = re.sub(r',\s*,', ',', cleaned_response)  # Double commas
            
            # Ensure response starts with uploaded file reference
            if not any(filename in cleaned_response for filename in uploaded_filenames):
                first_filename = uploaded_filenames[0] if uploaded_filenames else "your uploaded file"
                cleaned_response = f"📄 **Analysis of your uploaded file: {first_filename}**\n\n{cleaned_response}"
            
            cleaned_length = len(cleaned_response)
            if original_length != cleaned_length:
                print(f"🧹 CLEANED: Removed {original_length - cleaned_length} characters of external references")
            
            return cleaned_response.strip()
            
        except Exception as e:
            print(f"⚠️ Error cleaning external references: {e}")
            return response
    
    def _force_remove_dataset_mentions(self, response: str) -> str:
        """FINAL AGGRESSIVE PASS: Remove ANY mention of dataset or Blue Carbon Knowledge Dataset"""
        try:
            print("🧹 FINAL PASS: Force removing dataset mentions...")
            
            original_response = response
            
            # List of exact phrases to remove (case-insensitive)
            forbidden_phrases = [
                "Based on the provided context from the uploaded files and the Blue Carbon Knowledge Dataset",
                "from the uploaded files and the Blue Carbon Knowledge Dataset",
                "and the Blue Carbon Knowledge Dataset",
                "Blue Carbon Knowledge Dataset",
                "the Blue Carbon dataset",
                "from the dataset",
                "using the dataset",
                "according to the dataset",
                "based on the dataset"
            ]
            
            # Remove each forbidden phrase
            for phrase in forbidden_phrases:
                if phrase.lower() in response.lower():
                    print(f"🚫 FORCE REMOVING: '{phrase}'")
                    # Case-insensitive replacement
                    response = re.sub(re.escape(phrase), '', response, flags=re.IGNORECASE)
            
            # Also remove any sentence that starts with "Based on the provided context"
            response = re.sub(r'Based on the provided context[^.]*\.\s*', '', response, flags=re.IGNORECASE)
            
            # Clean up any resulting formatting issues
            response = re.sub(r'\s+', ' ', response)  # Multiple spaces
            response = re.sub(r'\n\s*\n\s*\n', '\n\n', response)  # Multiple newlines
            response = response.strip()
            
            if response != original_response:
                print(f"🧹 FORCE REMOVED: {len(original_response) - len(response)} characters")
            else:
                print("✅ No dataset mentions found in final check")
            
            return response
            
        except Exception as e:
            print(f"⚠️ Error in force removal: {e}")
            return response
    
    def _force_format_response(self, response: str) -> str:
        """Force format response with proper line breaks and structure (ChatGPT-style)"""
        try:
            print("✨ FORCE FORMATTING response...")
            
            # If response already has good formatting (multiple line breaks), return as is
            if response.count('\n\n') >= 3:
                print("✅ Response already well-formatted")
                return response
            
            # Otherwise, add line breaks at key points
            formatted = response
            
            # Add line breaks before markdown headers
            formatted = re.sub(r'([.!?])\s+(#{1,3}\s+)', r'\1\n\n\2', formatted)
            
            # Add line breaks before section headers (words followed by colon)
            formatted = re.sub(r'([.!?])\s+([A-Z][^:]{5,30}:)', r'\1\n\n\2', formatted)
            
            # Add line breaks before bullet points if they're inline
            formatted = re.sub(r'([.!?])\s+(•|\*|-)\s*', r'\1\n\n\2 ', formatted)
            
            # Add line breaks before "Based on", "According to", etc.
            formatted = re.sub(r'([.!?])\s+(Based on|According to|The |For |To calculate|In summary)', r'\1\n\n\2', formatted)
            
            # Add line breaks before calculations and data
            formatted = re.sub(r'([.!?])\s+(Forest|Plantation|Total|Credits|Calculation|Data|Results)', r'\1\n\n\2', formatted)
            
            # Add line breaks before numbered lists
            formatted = re.sub(r'([.!?])\s+(\d+\.)\s+', r'\1\n\n\2 ', formatted)
            
            # Clean up excessive line breaks
            formatted = re.sub(r'\n{3,}', '\n\n', formatted)
            
            # Ensure bullet points are on new lines
            formatted = re.sub(r'([^\n])(•|\*|-)\s+', r'\1\n\2 ', formatted)
            
            # Ensure numbered lists are on new lines
            formatted = re.sub(r'([^\n])(\d+\.)\s+', r'\1\n\2 ', formatted)
            
            print(f"✨ Added {formatted.count(chr(10)) - response.count(chr(10))} line breaks")
            
            return formatted.strip()
            
        except Exception as e:
            print(f"❌ Error formatting response: {e}")
            return response
    
    def _add_image_explanations(self, response: str, images: List[Dict]) -> str:
        """Add intelligent image placement with explanations (ChatGPT-style)"""
        try:
            if not images:
                return response
            
            print(f"🖼️ Adding explanations for {len(images)} images...")
            
            # Add image section at the end with explanations
            image_section = "\n\n## 📸 Visual References\n\n"
            
            for i, img in enumerate(images, 1):
                title = img.get('title', 'Image')
                source = img.get('source_domain', img.get('source', 'Web'))
                
                # Create intelligent caption based on title
                caption = self._generate_image_caption(title, response)
                
                image_section += f"**{i}. {title}**\n"
                image_section += f"_{caption}_\n"
                image_section += f"Source: {source}\n\n"
            
            return response + image_section
            
        except Exception as e:
            print(f"❌ Error adding image explanations: {e}")
            return response
    
    def _generate_image_caption(self, image_title: str, response_context: str) -> str:
        """Generate intelligent caption for image based on context"""
        # Simple caption generation based on image title
        title_lower = image_title.lower()
        
        if 'mangrove' in title_lower:
            return "Mangrove ecosystems are crucial for blue carbon sequestration"
        elif 'seagrass' in title_lower:
            return "Seagrass meadows store carbon in sediments"
        elif 'coral' in title_lower:
            return "Coral reefs support marine biodiversity"
        elif 'wetland' in title_lower or 'marsh' in title_lower:
            return "Coastal wetlands are highly effective carbon sinks"
        elif 'carbon' in title_lower:
            return "Visual representation of carbon cycle processes"
        elif 'restoration' in title_lower:
            return "Ecosystem restoration efforts in action"
        else:
            return "Visual reference for the discussed topic"
    
    def _create_session_vector_index(self, session_id: str, query: str) -> Tuple[str, List[Source]]:
        """Create a temporary vector index ONLY for this session's files"""
        try:
            print(f"🔧 Creating session-specific vector index for: {session_id}")
            
            # Get session files
            session_files = self.session_manager.get_session_files(session_id)
            if not session_files:
                return "", []
            
            # Get all chunks from main vector store
            query_embedding = self.embedding_processor.embed_texts_parallel([query])[0]
            all_chunks = self.vector_store.search(query_embedding, 500)  # Get many chunks
            
            # Filter to ONLY session files
            session_chunks = []
            session_filenames = [f.get('filename', '') for f in session_files if f.get('processing_status') == 'completed']
            
            print(f"🔍 Looking for chunks from: {session_filenames}")
            
            for chunk in all_chunks:
                source_file = chunk.get('source_file', '')
                
                # Check if chunk belongs to any session file
                for filename in session_filenames:
                    if (filename in source_file or 
                        source_file.endswith(filename) or
                        any(part in source_file for part in filename.split('_')[:3])):  # Match first 3 parts of filename
                        session_chunks.append(chunk)
                        print(f"✅ Session chunk: {source_file}")
                        break
            
            print(f"🔧 Found {len(session_chunks)} chunks for session files")
            
            if not session_chunks:
                return "", []
            
            # Create session-specific content
            content_parts = []
            sources = []
            
            # Sort by relevance
            session_chunks.sort(key=lambda x: x.get('similarity_score', 0.0), reverse=True)
            
            for chunk in session_chunks[:25]:  # Top 25 most relevant
                text = chunk.get('text', '').strip()
                source_file = chunk.get('source_file', '')
                
                if text and len(text) > 50:
                    content_parts.append(f"📄 From {source_file}:\n{text}")
                    
                    sources.append(Source(
                        filename=source_file,
                        snippet=text[:300] + "..." if len(text) > 300 else text,
                        similarity_score=chunk.get('similarity_score', 0.8),
                        chunk_id=chunk.get('chunk_id', ''),
                        page_number=chunk.get('page_number', 0),
                        source_type='uploaded'
                    ))
            
            if content_parts:
                session_context = "\n\n".join(content_parts)
                print(f"🔧 Session index created: {len(session_context)} characters")
                return session_context, sources
            else:
                return "", []
                
        except Exception as e:
            print(f"❌ Error creating session vector index: {e}")
            return "", []
    
    def _create_file_fallback_response(self, query: str, file_sources: List[Source]) -> str:
        """Create fallback response when file processing fails"""
        filenames = [s.filename for s in file_sources] if file_sources else ["your uploaded file"]
        
        return f"""📁 **Analysis of {', '.join(filenames)}**

I can see you've uploaded files related to blue carbon, but I'm having difficulty processing the specific content for your question: "{query}"

**What I can tell you about your uploaded files:**
• Files are related to blue carbon/environmental topics ✅
• Files have been processed and indexed 📊
• Content is available for analysis 🔍

**To get better results:**
1. Try rephrasing your question more specifically
2. Ask about particular sections or data in the file
3. Request specific information like numbers, findings, or recommendations

**Example questions:**
- "What are the main findings in this document?"
- "What carbon credit values are mentioned?"
- "Summarize the key data from my uploaded file"

I'm ready to analyze your file content more effectively! 🌊"""
    
    def _get_dataset_context(self, query: str) -> Tuple[str, List[Source]]:
        """TIER 2: Get context from Blue Carbon Knowledge Dataset"""
        try:
            print("📚 Searching Blue Carbon Knowledge Dataset...")
            
            # Get query embedding
            query_embedding = self.embedding_processor.embed_texts_parallel([query])[0]
            
            # Search vector store for dataset content (non-uploaded files)
            results = self.vector_store.search(query_embedding, 8)
            
            # Filter for dataset sources (not uploaded files)
            dataset_results = []
            for result in results:
                source_file = result.get('source_file', '')
                # Skip uploaded files (they should be in uploads/ directory)
                if not source_file.startswith('uploads/') and 'uploads' not in source_file:
                    dataset_results.append(result)
            
            if not dataset_results:
                print("📚 No relevant dataset content found")
                return "", []
            
            # Build dataset context and sources
            context_parts = []
            sources = []
            
            for result in dataset_results[:6]:  # Top 6 most relevant
                text = result.get('text', '')
                source_file = result.get('source_file', '')
                similarity = result.get('similarity_score', 0.0)
                
                context_parts.append(f"Dataset - {source_file}: {text}")
                
                sources.append(Source(
                    filename=source_file,
                    snippet=text[:200] + "..." if len(text) > 200 else text,
                    similarity_score=similarity,
                    chunk_id=result.get('chunk_id', ''),
                    page_number=result.get('page_number', 0),
                    source_type='knowledge_base'
                ))
            
            dataset_context = "\n\n".join(context_parts)
            print(f"📚 Dataset context built: {len(dataset_context)} characters from {len(sources)} chunks")
            
            return dataset_context, sources
            
        except Exception as e:
            print(f"❌ Error getting dataset context: {e}")
            self.error_counts['vector'] += 1
            return "", []
    
    def _get_web_context(self, query: str) -> Tuple[str, List[Source], List[Dict]]:
        """TIER 3: Get context from web search with AI-driven image decisions"""
        try:
            if not self.web_search or not self.web_search.enabled:
                print("🌐 Web search not available")
                return "", [], []
            
            print(f"🌐 Web search for: {query}")
            
            # AI DECISION: Determine if images are needed and how many
            image_decision = self._ai_decide_image_needs(query)
            needs_images = image_decision['needs_images']
            image_count = image_decision['count']  # 0-3
            
            print(f"🤖 AI Decision: needs_images={needs_images}, count={image_count}")
            
            # Get web search results
            web_results = self.web_search.search_web(query, max_results=5)
            web_images = []
            
            if needs_images and image_count > 0:
                print(f"🖼️ Fetching {image_count} images as decided by AI")
                enhanced_results = self.web_search.search_with_images(query, max_results=5, max_images=image_count)
                web_images = enhanced_results.get('images', [])
            
            if not web_results:
                print("🌐 No web results found")
                return "", [], web_images
            
            # Build web context and sources
            context_parts = []
            sources = []
            
            for result in web_results:
                title = getattr(result, 'title', 'Web Source')
                snippet = getattr(result, 'snippet', '')
                url = getattr(result, 'url', '')
                
                if len(snippet) < 50:  # Skip low-quality snippets
                    continue
                
                context_parts.append(f"Web - {title}: {snippet}")
                
                sources.append(Source(
                    filename=title,
                    snippet=snippet[:200] + "..." if len(snippet) > 200 else snippet,
                    similarity_score=0.8,  # Default web relevance
                    chunk_id=f"web_{hash(title)}",
                    page_number=0,
                    source_type='web',
                    url=url  # Add URL for clickable links
                ))
            
            web_context = "\n\n".join(context_parts)
            print(f"🌐 Web context built: {len(web_context)} characters from {len(sources)} sources")
            
            return web_context, sources, web_images
            
        except Exception as e:
            print(f"❌ Error getting web context: {e}")
            self.error_counts['web'] += 1
            return "", [], []
    
    def _try_answer_from_files_only(self, query: str, file_context: str, file_sources: List[Source]) -> str:
        """Try to answer comprehensively using only uploaded file context - ChatGPT style"""
        try:
            # Get conversation history for context
            conversation_history = self._get_conversation_context(file_sources[0].filename.split('/')[-1] if file_sources else "")
            
            system_prompt = """You are "BlueCarbon AI" — a specialized environmental intelligence assistant.

CRITICAL INSTRUCTIONS FOR FILE-BASED RESPONSES:
- Answer COMPREHENSIVELY using the provided file context from the user's uploaded documents
- Be thorough and detailed - extract ALL relevant information from the files
- Use engaging formatting: emojis 🌊, **bold** text, bullet points, tables when appropriate
- Quote specific data, numbers, and findings from the files
- If the file context contains sufficient information, provide a complete answer
- Only say "insufficient information" if the files truly lack relevant content
- Organize information logically with clear sections
- Reference specific parts of the uploaded documents when relevant"""

            user_prompt = f"""User Question: {query}

Comprehensive File Context from User's Uploaded Documents:
{file_context}

{conversation_history}

Provide a COMPREHENSIVE answer using the uploaded file information. Be thorough and extract all relevant details."""

            response = self.groq_client.complete(f"{system_prompt}\n\n{user_prompt}")
            return response
            
        except Exception as e:
            print(f"❌ Error generating comprehensive file response: {e}")
            return ""
    
    def _try_answer_from_dataset(self, query: str, combined_context: str, all_sources: List[Source], has_files: bool) -> str:
        """Try to answer using file + dataset context"""
        try:
            system_prompt = """You are "BlueCarbon AI" — an intelligent environmental assistant with ChatGPT-level capabilities.

🎯 YOUR INTELLIGENCE:
- Expert knowledge in blue carbon, marine ecosystems, climate science
- Ability to structure complex information clearly
- Natural, conversational communication style
- Autonomous decision-making for comprehensive answers

📋 RESPONSE STRUCTURE (Like ChatGPT):

1. **Brief Introduction** (1-2 sentences)
   - Directly address the question
   - Set context

2. **Main Content** (Well-organized)
   - Use headers (##) for major sections
   - Bullet points (•) for lists
   - **Bold** for key terms and numbers
   - Line breaks between sections

3. **Additional Context** (If helpful)
   - Related information
   - Practical applications
   - Examples

✨ FORMATTING RULES:
- Use markdown extensively
- Add emojis strategically (🌊 💰 🌱 🏖️)
- Break up long paragraphs
- Use tables for comparisons
- Add line breaks generously

🔍 INTELLIGENCE GUIDELINES:
- Synthesize information from multiple sources
- Provide context and explanations
- Connect concepts logically
- Be comprehensive yet concise
- Use analogies when helpful

❌ NEVER:
- Write unformatted paragraphs
- Skip line breaks
- Be vague or generic
- Hallucinate information"""

            context_note = "uploaded files and dataset" if has_files else "Blue Carbon Knowledge Dataset"
            
            user_prompt = f"""User Question: {query}

Available Context from {context_note}:
{combined_context}

Provide a comprehensive answer using the available context."""

            response = self.groq_client.complete(f"{system_prompt}\n\n{user_prompt}")
            return response
            
        except Exception as e:
            print(f"❌ Error generating dataset response: {e}")
            return ""
    
    def _generate_final_response(self, query: str, full_context: str, all_sources: List[Source], retrieval_path: List[str], conversation_history: str = "") -> str:
        """Generate final comprehensive response using all available context + conversation history"""
        try:
            # Determine formatting based on query
            formatting_instructions = self._get_formatting_instructions(query.lower())
            
            # Check if this is a follow-up question
            is_followup = len(conversation_history.strip()) > 0
            
            system_prompt = f"""You are "BlueCarbon AI" — an intelligent environmental assistant with ChatGPT-level capabilities.

🎯 YOUR ROLE:
You're an expert in blue carbon, marine ecosystems, carbon credits, and coastal restoration. You provide comprehensive, well-structured answers like ChatGPT.

📋 RESPONSE STRUCTURE:

**1. Introduction** (1-2 sentences)
- Directly address the question
- Provide immediate value

**2. Main Content** (Well-organized with headers)
Use markdown formatting:
- ## Headers for major sections
- • Bullet points for lists
- **Bold** for key terms
- Line breaks between sections
- Tables when comparing data
- Emojis strategically (🌊 💰 🌱)

**3. Practical Context** (If relevant)
- Real-world applications
- Examples
- Related concepts

✨ INTELLIGENCE REQUIREMENTS:
- Synthesize information from multiple sources
- Provide clear explanations
- Connect concepts logically
- Be comprehensive yet readable
- {formatting_instructions}

🔍 CONTEXT AWARENESS:
- {"This is a follow-up question - maintain conversation continuity" if is_followup else "This is a new conversation"}
- {"PRIORITY: User uploaded files - be comprehensive with their data" if has_files else "Use knowledge base effectively"}
- Never hallucinate - use only provided information

❌ AVOID:
- Long unformatted paragraphs
- Skipping line breaks
- Generic responses
- Missing structure"""

            sources_info = f"Retrieved from: {' → '.join(retrieval_path)}"
            
            user_prompt = f"""User Question: {query}

Available Context:
{full_context}

{conversation_history}

Sources: {sources_info}

Provide a comprehensive, well-formatted response that considers the conversation context."""

            response = self.groq_client.complete(f"{system_prompt}\n\n{user_prompt}")
            return response
            
        except Exception as e:
            print(f"❌ Error generating final response: {e}")
            self.error_counts['groq'] += 1
            return self._create_fallback_response(query, retrieval_path)
    
    def _add_source_citation(self, response: str, retrieval_path: List[str], sources: List[Source]) -> str:
        """Add source citation to response"""
        try:
            # Count sources by type
            source_counts = {}
            for source in sources:
                source_type = getattr(source, 'source_type', 'unknown')
                source_counts[source_type] = source_counts.get(source_type, 0) + 1
            
            # Build citation with file priority emphasis
            citation_parts = []
            if 'uploaded' in source_counts:
                citation_parts.append(f"📁 **PRIMARY: Your Uploaded Files ({source_counts['uploaded']})**")
            if 'knowledge_base' in source_counts:
                citation_parts.append(f"📚 Supporting Dataset ({source_counts['knowledge_base']})")
            if 'web' in source_counts:
                citation_parts.append(f"🌐 Web Verification ({source_counts['web']})")
            
            if citation_parts:
                citation = f"\n\n---\n**Sources (Priority Order):** {' + '.join(citation_parts)}"
                response += citation
            
            return response
            
        except Exception as e:
            print(f"⚠️ Error adding citation: {e}")
            return response
    
    def _is_sufficient_answer(self, response: str, query: str) -> bool:
        """Check if response is sufficient to answer the query"""
        if not response or len(response.strip()) < 100:
            return False
        
        # Check for insufficient answer indicators
        insufficient_indicators = [
            "i couldn't find", "insufficient information", "would you like me to check",
            "not enough information", "unable to find", "no information available"
        ]
        
        response_lower = response.lower()
        return not any(indicator in response_lower for indicator in insufficient_indicators)
    
    def _should_use_web_search(self, query: str, local_sources_count: int) -> bool:
        """Decide if web search is needed as final resort"""
        query_lower = query.lower()
        
        # Always use web search for current/recent information
        recent_terms = ['latest', 'recent', 'current', '2024', '2025', 'new', 'today', 'update']
        if any(term in query_lower for term in recent_terms):
            return True
        
        # Use web search if insufficient local sources
        if local_sources_count < 3:
            return True
        
        # Use web search for specific data requests
        data_terms = ['statistics', 'data', 'numbers', 'comparison', 'research', 'study']
        if any(term in query_lower for term in data_terms):
            return True
        
        return False
    
    def _query_needs_images(self, query: str) -> bool:
        """Intelligently determine if query would benefit from images (like ChatGPT)"""
        query_lower = query.lower()
        
        # Explicit image requests
        explicit_visual = ['show', 'image', 'picture', 'photo', 'visual', 'diagram', 'chart', 'map']
        if any(term in query_lower for term in explicit_visual):
            return True
        
        # Topics that benefit from visual aids
        visual_topics = [
            'ecosystem', 'mangrove', 'seagrass', 'coral', 'wetland', 'coastal',
            'restoration', 'habitat', 'species', 'marine life', 'ocean',
            'carbon cycle', 'sequestration', 'climate change', 'sea level',
            'biodiversity', 'conservation', 'blue carbon', 'salt marsh'
        ]
        if any(topic in query_lower for topic in visual_topics):
            return True
        
        # Question types that benefit from images
        visual_questions = ['what does', 'what is', 'how does', 'show me', 'example of']
        if any(q in query_lower for q in visual_questions):
            return True
        
        return False
    
    def _get_formatting_instructions(self, query_lower: str) -> str:
        """Get formatting instructions based on query type"""
        if any(word in query_lower for word in ['compare', 'vs', 'versus', 'difference']):
            return "Create comparison tables when showing differences"
        elif any(word in query_lower for word in ['list', 'types', 'examples', 'benefits']):
            return "Use bullet points with emojis for lists"
        elif any(word in query_lower for word in ['steps', 'how to', 'process', 'method']):
            return "Use numbered steps with relevant emojis"
        elif any(word in query_lower for word in ['data', 'statistics', 'numbers']):
            return "**Bold** all important numbers and data with 📊"
        else:
            return "Use engaging formatting with strategic emojis and **bold** emphasis"
    
    def _create_response_data(self, answer: str, sources: List[Source], images: List[Dict], 
                            query: str, session_id: str, retrieval_path: List[str], 
                            start_time: float, method: str) -> ResponseData:
        """Create ResponseData object"""
        processing_time = time.time() - start_time
        
        # DEDUPLICATE SOURCES: Only show each unique file once
        unique_sources = {}
        for source in sources:
            filename = source.filename
            if filename not in unique_sources:
                # Keep the first occurrence (highest relevance)
                unique_sources[filename] = source
        
        deduplicated_sources = list(unique_sources.values())
        
        if len(sources) != len(deduplicated_sources):
            print(f"📊 Deduplicated sources: {len(sources)} → {len(deduplicated_sources)}")
        
        return ResponseData(
            answer=answer,
            sources=deduplicated_sources,  # Use deduplicated sources
            web_images=images,
            suggestions=self._generate_suggestions(query),
            confidence_score=self._calculate_confidence(deduplicated_sources, retrieval_path),
            retrieval_time=processing_time,
            response_type=method
        )
    
    def _create_fallback_response(self, query: str, retrieval_path: List[str]) -> str:
        """Create fallback response when all else fails"""
        return f"""I apologize, but I'm having technical difficulties processing your question about "{query}".

As **BlueCarbon AI** 🌊, I specialize in:
• **Blue Carbon Ecosystems** 🌱 (mangroves, seagrass, salt marshes)
• **Carbon Credits & Markets** 💰
• **Coastal Restoration** 🏖️
• **Marine Conservation** 🐟

Please try rephrasing your question or check if your uploaded files are related to these topics.

**Retrieval attempted:** {' → '.join(retrieval_path) if retrieval_path else 'None'}"""
    
    def _create_error_response(self, query: str, session_id: str, error: str, start_time: float) -> ResponseData:
        """Create error response"""
        return ResponseData(
            answer=self._create_fallback_response(query, []),
            sources=[],
            web_images=[],
            suggestions=[],
            confidence_score=0.0,
            retrieval_time=time.time() - start_time,
            response_type="Error Fallback"
        )
    
    def _generate_suggestions(self, query: str) -> List[str]:
        """Generate follow-up suggestions"""
        return [
            "Tell me more about blue carbon ecosystems",
            "How do carbon credits work for coastal restoration?",
            "What are the benefits of mangrove conservation?"
        ]
    
    def _get_conversation_context(self, current_file: str = "") -> str:
        """Get conversation context for better continuity"""
        try:
            if current_file:
                return f"\nConversation Context: User is asking about their uploaded file: {current_file}"
            return ""
        except Exception as e:
            print(f"⚠️ Error getting conversation context: {e}")
            return ""
    
    def _save_conversation_memory(self, session_id: str, query: str, response: str, sources: List[Source]):
        """Save conversation to session memory like ChatGPT"""
        try:
            # Save user message to chat history (full featured)
            from services.chat_history_service import get_chat_history_service
            chat_history = get_chat_history_service()
            
            chat_history.add_message(
                session_id=session_id,
                role='user',
                content=query,
                sources=[],
                response_time=0.0,
                confidence_score=0.0
            )
            
            # Save assistant response with sources
            source_data = []
            for source in sources:
                source_data.append({
                    'filename': getattr(source, 'filename', ''),
                    'source_type': getattr(source, 'source_type', ''),
                    'similarity_score': getattr(source, 'similarity_score', 0.0)
                })
            
            chat_history.add_message(
                session_id=session_id,
                role='assistant',
                content=response,
                sources=source_data,
                response_time=0.0,
                confidence_score=self._calculate_confidence(sources, [])
            )
            
            # Also save to session manager (lightweight tracking)
            self.session_manager.add_message(session_id, 'user', query)
            self.session_manager.add_message(session_id, 'assistant', response)
            
            print(f"💾 Saved conversation to session memory: {session_id}")
            
        except Exception as e:
            print(f"⚠️ Error saving conversation memory: {e}")
    
    def _get_session_conversation_history(self, session_id: str, max_messages: int = 6) -> str:
        """Get recent conversation history for context"""
        try:
            history = self.session_manager.get_session_history(session_id, limit=max_messages)
            if not history:
                return ""
            
            context_parts = []
            for msg in history[-max_messages:]:  # Last N messages
                role = msg.get('type', '')
                content = msg.get('content', '')
                
                if role == 'user':
                    context_parts.append(f"User: {content[:200]}...")
                elif role == 'assistant':
                    context_parts.append(f"Assistant: {content[:200]}...")
            
            if context_parts:
                return f"\nRecent Conversation:\n" + "\n".join(context_parts)
            
            return ""
            
        except Exception as e:
            print(f"⚠️ Error getting conversation history: {e}")
            return ""
    
    def _calculate_confidence(self, sources: List[Source], retrieval_path: List[str]) -> float:
        """Calculate confidence score based on sources and retrieval path"""
        if not sources:
            return 0.0
        
        base_confidence = 0.5
        
        # Boost for uploaded files (highest confidence)
        if any(getattr(s, 'source_type', '') == 'uploaded' for s in sources):
            base_confidence += 0.4
        
        # Boost for dataset sources
        if any(getattr(s, 'source_type', '') == 'knowledge_base' for s in sources):
            base_confidence += 0.2
        
        # Average similarity score
        similarities = [getattr(s, 'similarity_score', 0.0) for s in sources]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        
        return min(base_confidence + (avg_similarity * 0.3), 1.0)


# Global instance
_chat_engine = None

def get_simple_chat_engine() -> SimpleChatEngine:
    """Get global chat engine instance"""
    global _chat_engine
    if _chat_engine is None:
        _chat_engine = SimpleChatEngine()
    return _chat_engine