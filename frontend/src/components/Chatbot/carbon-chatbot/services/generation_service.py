import json
import time
import re
from typing import List, Dict, Any, Optional
from models.response_models import PlanningData, ChartSpec, ResponseData, Chunk, Source
from services.groq_service import get_groq_client, get_fallback_service
from services.cache_service import get_specialized_caches
from config import Config

class MultiPassGenerationService:
    """Professional multi-pass generation system (outline → expand → polish)"""
    
    def __init__(self):
        self.groq_client = get_groq_client()
        self.fallback_service = get_fallback_service()
        self.cache = get_specialized_caches()
        
        # Professional prompts for different phases
        self.system_prompts = {
            'planning': """You are a senior technical writer and domain expert specializing in blue carbon ecosystems. 
Your task is to create a structured plan for generating professional responses. Always produce valid JSON for machine parsing.
Analyze the query and context to determine the optimal response structure, whether charts are needed, and what follow-up questions would be valuable.""",
            
            'execution': """You are a senior technical writer and domain expert specializing in blue carbon ecosystems.
Generate professional, human-grade content with proper citations. Use [UPLOADED: filename.pdf] for document sources and [WEB: url] for web sources.
Write in a professional tone suitable for academic or business contexts. Include technical detail and actionable insights.""",
            
            'polishing': """You are an expert editor specializing in professional and technical writing.
Review and enhance the provided content for clarity, professionalism, and completeness. Ensure proper formatting, 
consistent tone, and comprehensive coverage of the topic. Maintain all citations and technical accuracy."""
        }
        
        print("🚀 MultiPassGenerationService initialized")
    
    def _detect_numeric_data(self, chunks: List[Chunk]) -> bool:
        """Detect if chunks contain numeric data suitable for charts"""
        numeric_patterns = [
            r'\d+\.?\d*\s*%',  # Percentages
            r'\d+\.?\d*\s*(tons?|tonnes?|kg|g)',  # Weights
            r'\d+\.?\d*\s*(years?|months?|days?)',  # Time periods
            r'\d+\.?\d*\s*(hectares?|km²|m²)',  # Areas
            r'\$\d+\.?\d*',  # Currency
            r'\d+\.?\d*\s*(million|billion|thousand)',  # Large numbers
        ]
        
        text_content = " ".join([chunk.text for chunk in chunks[:3]])  # Check first 3 chunks
        
        numeric_count = 0
        for pattern in numeric_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            numeric_count += len(matches)
        
        return numeric_count >= 3  # Need at least 3 numeric values for charts
    
    def _determine_response_type(self, query: str) -> str:
        """Determine appropriate response type based on query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['report', 'comprehensive', 'detailed analysis']):
            return 'report'
        elif any(word in query_lower for word in ['analyze', 'analysis', 'examine']):
            return 'analysis'
        elif any(word in query_lower for word in ['summarize', 'summary', 'overview']):
            return 'summary'
        else:
            return 'general'
    
    def create_plan(self, query: str, chunks: List[Chunk]) -> PlanningData:
        """Phase 1: Create structured response plan"""
        try:
            response_type = self._determine_response_type(query)
            need_charts = self._detect_numeric_data(chunks)
            
            # Build context for planning
            context_summary = []
            for i, chunk in enumerate(chunks[:3]):
                context_summary.append(f"Source {i+1} [{chunk.source_file}]: {chunk.text[:200]}...")
            
            context_text = "\n".join(context_summary)
            
            planning_prompt = f"""
Analyze this query and context to create a structured response plan.

Query: {query}
Response Type: {response_type}
Context: {context_text}

Return a JSON object with this exact structure:
{{
    "outline": ["section1", "section2", "section3"],
    "need_charts": {str(need_charts).lower()},
    "chart_specs": [
        {{"type": "bar", "title": "Chart Title", "x_label": "X Axis", "y_label": "Y Axis", "description": "What this chart shows"}}
    ],
    "response_type": "{response_type}",
    "suggested_questions": ["Question 1?", "Question 2?", "Question 3?"],
    "estimated_length": "medium"
}}

Guidelines:
- For 'report': Include Executive Summary, Methodology, Findings, Recommendations
- For 'analysis': Include Overview, Key Findings, Implications, Next Steps  
- For 'summary': Include Main Points, Key Takeaways, Conclusions
- For 'general': Include Direct Answer, Context, Additional Information
- Only suggest charts if numeric data is present
- Provide 3 relevant follow-up questions
"""
            
            # Try Groq API first
            try:
                response = self.groq_client.generate_structured_response(
                    self.system_prompts['planning'],
                    planning_prompt,
                    temperature=0.3,
                    max_tokens=800
                )
                
                # Extract JSON from response (handle cases where model adds extra text)
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                else:
                    json_str = response.strip()
                
                # Parse JSON response
                plan_data = json.loads(json_str)
                
                # Convert to PlanningData object
                chart_specs = []
                for spec in plan_data.get('chart_specs', []):
                    chart_specs.append(ChartSpec(
                        type=spec.get('type', 'bar'),
                        title=spec.get('title', ''),
                        x_label=spec.get('x_label', ''),
                        y_label=spec.get('y_label', ''),
                        description=spec.get('description', '')
                    ))
                
                return PlanningData(
                    outline=plan_data.get('outline', []),
                    need_charts=plan_data.get('need_charts', False),
                    chart_specs=chart_specs,
                    response_type=plan_data.get('response_type', response_type),
                    suggested_questions=plan_data.get('suggested_questions', []),
                    estimated_length=plan_data.get('estimated_length', 'medium')
                )
                
            except Exception as e:
                print(f"⚠️ Planning phase error: {e}, using fallback")
                
        except Exception as e:
            print(f"⚠️ Planning error: {e}")
        
        # Fallback planning
        return self._create_fallback_plan(query, response_type, need_charts)
    
    def _create_fallback_plan(self, query: str, response_type: str, need_charts: bool) -> PlanningData:
        """Create fallback plan when API fails"""
        outlines = {
            'report': ['Executive Summary', 'Methodology', 'Key Findings', 'Analysis', 'Recommendations', 'Conclusion'],
            'analysis': ['Overview', 'Key Findings', 'Detailed Analysis', 'Implications', 'Next Steps'],
            'summary': ['Main Points', 'Key Takeaways', 'Supporting Evidence', 'Conclusions'],
            'general': ['Direct Answer', 'Context and Background', 'Additional Information', 'Related Topics']
        }
        
        suggestions = [
            f"Can you provide more details about {query.split()[-1] if query.split() else 'this topic'}?",
            "What are the latest developments in this area?",
            "How does this relate to climate change mitigation?"
        ]
        
        chart_specs = []
        if need_charts:
            chart_specs.append(ChartSpec(
                type='bar',
                title='Key Metrics Overview',
                x_label='Categories',
                y_label='Values',
                description='Overview of key quantitative findings'
            ))
        
        return PlanningData(
            outline=outlines.get(response_type, outlines['general']),
            need_charts=need_charts,
            chart_specs=chart_specs,
            response_type=response_type,
            suggested_questions=suggestions,
            estimated_length='medium'
        )
    
    def execute_plan(self, plan: PlanningData, query: str, chunks: List[Chunk]) -> str:
        """Phase 2: Execute the plan and generate content"""
        try:
            # Build comprehensive context
            context_parts = []
            sources = []
            
            for i, chunk in enumerate(chunks):
                source_file = chunk.source_file
                text = chunk.text
                
                context_parts.append(f"SOURCE {i+1} [{source_file}]: {text}")
                sources.append(f"[UPLOADED: {source_file}]")
            
            context = "\n\n".join(context_parts)
            
            # Create execution prompt based on response type
            execution_prompt = self._create_execution_prompt(plan, query, context)
            
            # Try Groq API
            try:
                response = self.groq_client.generate_structured_response(
                    self.system_prompts['execution'],
                    execution_prompt,
                    temperature=0.7,
                    max_tokens=2000
                )
                
                # Ensure minimum length for professional responses
                if len(response.strip()) < 200 and plan.response_type in ['report', 'analysis']:
                    # Auto-expand brief responses
                    expansion_prompt = f"""
The following response is too brief for a professional {plan.response_type}. 
Expand it with more technical detail, specific examples, and comprehensive analysis while maintaining accuracy.

Original response: {response}

Context: {context[:1000]}

Provide a more detailed and professional response:"""
                    
                    expanded_response = self.groq_client.generate_structured_response(
                        self.system_prompts['execution'],
                        expansion_prompt,
                        temperature=0.6,
                        max_tokens=2500
                    )
                    
                    return expanded_response.strip()
                
                return response.strip()
                
            except Exception as e:
                print(f"⚠️ Execution phase error: {e}, using fallback")
                return self.fallback_service.generate_fallback_response(query, context, plan.response_type)
        
        except Exception as e:
            print(f"⚠️ Execution error: {e}")
            return self.fallback_service.generate_fallback_response(query, "", plan.response_type)
    
    def _create_execution_prompt(self, plan: PlanningData, query: str, context: str) -> str:
        """Create execution prompt based on plan"""
        outline_text = "\n".join([f"{i+1}. {section}" for i, section in enumerate(plan.outline)])
        
        base_prompt = f"""
Generate a professional {plan.response_type} addressing this query using the provided context.

Query: {query}

Required Structure:
{outline_text}

Context from Documents:
{context[:2000]}

Requirements:
- Use professional, human-grade writing suitable for business/academic contexts
- Include specific citations using [UPLOADED: filename.pdf] format
- Provide technical detail and actionable insights
- Follow the outlined structure exactly
- Ensure comprehensive coverage of the topic
- Include quantitative data where available
"""
        
        if plan.response_type == 'report':
            base_prompt += """
- Include methodology section explaining data sources and analysis approach
- Provide executive summary with key findings
- Include detailed recommendations with implementation steps
- Use professional report formatting with clear sections
"""
        elif plan.response_type == 'analysis':
            base_prompt += """
- Provide in-depth analytical insights
- Include implications and significance of findings
- Suggest next steps or areas for further investigation
- Use analytical language and evidence-based conclusions
"""
        
        return base_prompt
    
    def polish_response(self, content: str, plan: PlanningData) -> str:
        """Phase 3: Polish and enhance the response"""
        try:
            polishing_prompt = f"""
Review and enhance this {plan.response_type} for maximum professionalism and clarity.

Original Content:
{content}

Enhancement Requirements:
- Ensure professional tone throughout
- Improve clarity and readability
- Verify proper formatting and structure
- Enhance technical accuracy where possible
- Maintain all citations and sources
- Ensure comprehensive coverage
- Add transitional phrases for better flow

Return the enhanced version:"""
            
            try:
                polished = self.groq_client.generate_structured_response(
                    self.system_prompts['polishing'],
                    polishing_prompt,
                    temperature=0.3,
                    max_tokens=2500
                )
                
                # Verify polished version is actually better (not truncated)
                if len(polished.strip()) >= len(content.strip()) * 0.8:
                    return polished.strip()
                else:
                    print("⚠️ Polished version too short, using original")
                    return content
                
            except Exception as e:
                print(f"⚠️ Polishing error: {e}, using original content")
                return content
        
        except Exception as e:
            print(f"⚠️ Polishing phase error: {e}")
            return content
    
    def generate_professional_response(self, query: str, chunks: List[Chunk], 
                                     context_type: str = "general", session_id: str = "default") -> ResponseData:
        """Generate professional response using direct Groq API calls"""
        start_time = time.time()
        
        try:
            # Build context from chunks
            context_parts = []
            sources = []
            
            has_no_file_match = False
            has_uploaded_files = False
            
            for i, chunk in enumerate(chunks):
                # Handle both Chunk objects and dictionaries
                if hasattr(chunk, 'text'):
                    text = chunk.text
                    source_file = chunk.source_file
                    similarity_score = chunk.similarity_score or 0.0
                    chunk_id = chunk.id
                    page_number = chunk.page_number
                    source_type = getattr(chunk, 'source_type', 'unknown')
                elif isinstance(chunk, dict):
                    text = chunk.get('text', '')
                    source_file = chunk.get('source_file', 'unknown')
                    similarity_score = chunk.get('similarity_score', 0.0)
                    chunk_id = chunk.get('chunk_id', '')
                    page_number = chunk.get('page_number', 0)
                    source_type = chunk.get('source_type', 'unknown')
                    
                    # Check for special messages
                    if chunk.get('no_file_match', False):
                        has_no_file_match = True
                    if chunk.get('source_type') == 'uploaded_file':
                        has_uploaded_files = True
                else:
                    continue
                
                # Add source type indicator to context
                type_indicator = ""
                if source_type == 'uploaded_file':
                    type_indicator = "[UPLOADED FILE] "
                elif source_type == 'system_notice':
                    type_indicator = "[NOTICE] "
                elif source_type == 'general_knowledge':
                    type_indicator = "[KNOWLEDGE BASE] "
                
                context_parts.append(f"SOURCE {i+1} {type_indicator}[{source_file}]: {text}")
                
                sources.append(Source(
                    filename=source_file,
                    snippet=text[:150] + "..." if len(text) > 150 else text,
                    similarity_score=similarity_score,
                    chunk_id=chunk_id,
                    page_number=page_number,
                    source_type=source_type
                ))
            
            context = "\n\n".join(context_parts[:5])  # Limit context size
            
            # ENHANCED file priority handling with better context
            file_priority_context = ""
            file_priority_prefix = ""
            uploaded_file_names = []
            
            # Check for special file messages in chunks and collect file names
            for chunk in chunks:
                if isinstance(chunk, dict):
                    if 'file_priority_message' in chunk:
                        file_priority_prefix = chunk['file_priority_message'] + "\n\n"
                    if 'file_not_found_message' in chunk:
                        file_priority_prefix = chunk['file_not_found_message'] + "\n\n"
                    if chunk.get('source_type') == 'uploaded_file':
                        filename = chunk.get('source_file', '').split('/')[-1]
                        if filename and filename not in uploaded_file_names:
                            uploaded_file_names.append(filename)
            
            if has_uploaded_files:
                file_list = ', '.join(uploaded_file_names) if uploaded_file_names else 'uploaded document'
                file_priority_context = f"\n\nCRITICAL INSTRUCTION: The user has uploaded files: {file_list}. You MUST prioritize information from these files. Start your response by clearly stating you're analyzing their uploaded document(s). Provide detailed, comprehensive answers based on the file content. You may supplement with general knowledge if needed, but the uploaded file content should be the primary focus. Be specific and detailed in your analysis."
            elif has_no_file_match:
                file_priority_context = f"\n\nCRITICAL INSTRUCTION: The user uploaded files but they don't contain information about this query. You MUST start by clearly stating: 'I searched through your uploaded file(s) but couldn't find specific information about {query}. Here's what I can tell you from my knowledge base:' Then provide a comprehensive answer from general sources."
            
            # AI decides the best response structure and style
            structure_decision_prompt = f"""
Analyze this query and decide the best response approach:
Query: "{query}"
{file_priority_context}
Context Type: {context_type}
Available Context: {"Yes" if context else "No"}

Decide:
1. Response style (conversational, professional, educational, engaging)
2. Structure (bullet points, paragraphs, sections, Q&A format)
3. Tone (friendly, authoritative, enthusiastic, explanatory)
4. Length (brief, moderate, comprehensive)
5. Special elements (examples, analogies, comparisons, stories)

Return JSON: {{"style": "...", "structure": "...", "tone": "...", "length": "...", "elements": ["..."]}}
"""
            
            try:
                structure_response = self.groq_client.complete(structure_decision_prompt)
                # Extract decision (fallback to defaults if parsing fails)
                import json
                import re
                json_match = re.search(r'\{.*\}', structure_response, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                else:
                    decision = {"style": "engaging", "structure": "sections", "tone": "friendly", "length": "comprehensive", "elements": ["examples"]}
            except:
                decision = {"style": "engaging", "structure": "sections", "tone": "friendly", "length": "comprehensive", "elements": ["examples"]}
            
            # Create enhanced system prompt for better responses
            system_prompt = f"""You are an expert blue carbon researcher and analyst with deep knowledge of coastal ecosystems, carbon sequestration, and marine conservation.

RESPONSE STYLE: {decision.get('style', 'professional')} and {decision.get('tone', 'authoritative')}
STRUCTURE: Use {decision.get('structure', 'detailed sections')} format
LENGTH: {decision.get('length', 'comprehensive')} response
SPECIAL ELEMENTS: Include {', '.join(decision.get('elements', ['data analysis', 'specific examples']))}

CRITICAL GUIDELINES:
- When analyzing uploaded documents, provide detailed, specific insights from the content
- Quote relevant sections and page numbers when available
- Explain technical concepts clearly with examples
- Connect document findings to broader blue carbon knowledge
- Use scientific terminology appropriately
- Provide actionable insights and recommendations
- Structure responses with clear headings and bullet points
- Include quantitative data and statistics when available
- Reference specific methodologies, studies, or frameworks mentioned in documents
- Be thorough and comprehensive in your analysis

CITATION FORMAT: Use [Document: filename, Page X] for specific references"""

            # Create engaging user prompt
            if context_type == "analysis":
                user_prompt = f"""🔍 **ANALYSIS REQUEST**

I need you to analyze: "{query}"

📊 **Available Research Data:**
{context}

Please provide an engaging, comprehensive analysis that includes:
- 🎯 Key insights and findings
- 📈 Implications and significance  
- 💡 Recommendations and next steps
- 🌍 Real-world applications

Make it conversational and easy to understand while being thorough and professional."""

            elif context_type == "summary":
                user_prompt = f"""📋 **SUMMARY REQUEST**

Please summarize: "{query}"

📚 **Source Information:**
{context}

Create an engaging summary that:
- 🎯 Captures the main points clearly
- 💡 Highlights key takeaways
- 🔗 Shows connections and relationships
- ✨ Makes it interesting and memorable

Use a conversational tone that makes complex topics accessible."""

            else:
                user_prompt = f"""💬 **QUESTION**

"{query}"

📚 **Knowledge Base:**
{context}

Please provide an engaging, helpful response that:
- 🎯 Directly answers the question
- 💡 Provides valuable insights
- 🌟 Includes interesting details
- 🔗 Makes connections to broader topics

Be conversational, enthusiastic, and make blue carbon topics fascinating!"""
            
            # AI decides if web search is needed
            search_decision_prompt = f"""
Analyze if web search is needed for this query:
Query: "{query}"
Available context quality: {"Good" if len(context) > 500 else "Limited" if context else "None"}
Context relevance: {"High" if any(word in context.lower() for word in query.lower().split()) else "Low"}

Should I search the web for additional information? Consider:
- Is the query about recent developments, current events, or latest research?
- Is the available context insufficient or outdated?
- Would web search provide valuable additional insights?

Answer: YES or NO
Reason: Brief explanation
"""
            
            try:
                search_decision = self.groq_client.complete(search_decision_prompt)
                needs_web_search = "YES" in search_decision.upper()
                print(f"🤖 AI Decision: {'Web search needed' if needs_web_search else 'Local knowledge sufficient'}")
            except:
                needs_web_search = len(context) < 300  # Fallback logic
            
            # Enhanced web search with images if AI decides it's needed
            web_context = ""
            web_images = []
            if needs_web_search:
                try:
                    from services.web_search_service import get_web_search_service
                    web_search = get_web_search_service()
                    if web_search.enabled:
                        print("🌐 AI triggered enhanced web search for additional information and images...")
                        
                        # Use enhanced search with images (REDUCED for performance)
                        search_result = web_search.search_with_images(f"blue carbon {query}", max_results=2)
                        web_results = search_result.get('results', [])
                        web_images = search_result.get('images', [])
                        
                        if web_results or web_images:
                            web_context = "\n\n🌐 **LATEST WEB INFORMATION:**\n"
                            
                            for result in web_results:
                                web_context += f"- **{result.title}**: {result.snippet}\n"
                                # Add image indicator if available
                                if hasattr(result, 'thumbnail_url') and result.thumbnail_url:
                                    web_context += f"  📸 [Visual content available]\n"
                            
                            # Add image information to context
                            if web_images:
                                web_context += f"\n📸 **VISUAL CONTENT FOUND:**\n"
                                for img in web_images[:3]:  # Show first 3 images
                                    web_context += f"- {img.get('title', 'Image')}: {img.get('source', 'Unknown source')}\n"
                            
                            print(f"✅ Found {len(web_results)} web sources and {len(web_images)} images")
                        else:
                            print("⚠️ No web results or images found")
                            
                except Exception as e:
                    print(f"⚠️ Enhanced web search failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Combine local and web context
            full_context = context + web_context
            
            # Update user prompt with combined context
            if web_context:
                user_prompt = user_prompt.replace(context, full_context)
            
            # Add conversation memory to prompt for context awareness
            memory_context = ""
            if session_id != "default":
                try:
                    from services.session_manager import get_session_manager
                    session_manager = get_session_manager()
                    recent_context = session_manager.get_conversation_context(session_id, max_messages=6)
                    if recent_context:
                        memory_context = f"\n\n🧠 **CONVERSATION MEMORY:**\n{recent_context}\n"
                        user_prompt = user_prompt.replace("📚 **Knowledge Base:**", f"📚 **Knowledge Base:**{memory_context}")
                        print("🧠 Added conversation memory to context")
                except Exception as e:
                    print(f"⚠️ Memory integration failed: {e}")
            
            # Generate response using Groq
            print(f"🚀 Generating {context_type} response with Groq...")
            response_content = self.groq_client.generate_structured_response(
                system_prompt,
                user_prompt,
                temperature=0.7,
                max_tokens=2500
            )
            
            # Add file priority prefix if exists
            if file_priority_prefix:
                response_content = file_priority_prefix + response_content
            
            generation_time = time.time() - start_time
            
            # Generate suggestions
            suggestions = [
                f"Can you provide more details about {query.split()[-1] if query.split() else 'this topic'}?",
                "What are the latest developments in this area?",
                "How does this relate to climate change mitigation?"
            ]
            
            # Ensure web_images is always defined
            if 'web_images' not in locals():
                web_images = []
            
            response_data = ResponseData(
                answer=response_content,
                sources=sources,
                suggestions=suggestions,
                generation_time=generation_time,
                response_type=context_type,
                confidence_score=0.8 if chunks else 0.5,
                web_images=web_images
            )
            
            print(f"📊 Response includes {len(web_images)} web images")
            
            print(f"✅ Direct Groq response generated in {generation_time:.2f}s")
            return response_data
            
        except Exception as e:
            print(f"❌ Direct generation error: {e}")
            import traceback
            traceback.print_exc()
            
            # Try simple fallback with Groq
            try:
                simple_response = self.groq_client.complete(f"Answer this blue carbon question: {query}")
                return ResponseData(
                    answer=simple_response,
                    sources=[],
                    suggestions=["Can you provide more details?", "What specific aspect interests you?"],
                    generation_time=time.time() - start_time,
                    response_type=context_type,
                    confidence_score=0.4
                )
            except Exception as groq_error:
                print(f"❌ Simple Groq call failed: {groq_error}")
                # Only use fallback as absolute last resort
                fallback_content = self.fallback_service.generate_fallback_response(query, "", context_type)
                
                return ResponseData(
                    answer=fallback_content,
                    sources=[],
                    suggestions=["Can you provide more specific information?", "What aspects interest you most?"],
                    generation_time=time.time() - start_time,
                    response_type=context_type,
                    confidence_score=0.2
                )

# Global instance
_generation_service = None

def get_generation_service() -> MultiPassGenerationService:
    """Get global generation service instance"""
    global _generation_service
    if _generation_service is None:
        _generation_service = MultiPassGenerationService()
    return _generation_service