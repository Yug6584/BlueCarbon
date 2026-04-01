import time
import json
from typing import Dict, Any, Optional, List
import requests
from config import Config

class GroqAPIClient:
    """Ultra-fast Groq API client with comprehensive error handling and fallbacks"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or Config.GROQ_API_KEY
        self.model = model or Config.GROQ_MODEL
        self.base_url = "https://api.groq.com/openai/v1"
        
        # Request configuration
        self.timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # Performance tracking
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_response_time': 0.0,
            'cache_hits': 0
        }
        
        if not self.api_key:
            raise ValueError("Groq API key is required")
        
        print(f"🚀 GroqAPIClient initialized with model: {self.model}")
    
    def _make_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Make request to Groq API with error handling"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Default parameters optimized for speed and quality
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "top_p": kwargs.get("top_p", 0.9),
            "stream": False
        }
        
        # Add optional parameters
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
        if "presence_penalty" in kwargs:
            payload["presence_penalty"] = kwargs["presence_penalty"]
        if "frequency_penalty" in kwargs:
            payload["frequency_penalty"] = kwargs["frequency_penalty"]
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Update stats
                    self.stats['total_requests'] += 1
                    self.stats['successful_requests'] += 1
                    self.stats['total_response_time'] += response_time
                    
                    print(f"✅ Groq API response in {response_time*1000:.0f}ms")
                    return result
                
                elif response.status_code == 429:  # Rate limit
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"⚠️ Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                
                elif response.status_code == 401:  # Authentication error
                    raise Exception("Invalid Groq API key")
                
                else:
                    error_msg = f"Groq API error {response.status_code}: {response.text}"
                    if attempt == self.max_retries - 1:
                        raise Exception(error_msg)
                    print(f"⚠️ {error_msg}, retrying...")
                    time.sleep(self.retry_delay)
            
            except requests.exceptions.Timeout:
                if attempt == self.max_retries - 1:
                    raise Exception("Groq API timeout")
                print(f"⚠️ Request timeout, retrying {attempt + 1}/{self.max_retries}")
                time.sleep(self.retry_delay)
            
            except requests.exceptions.ConnectionError:
                if attempt == self.max_retries - 1:
                    raise Exception("Groq API connection error")
                print(f"⚠️ Connection error, retrying {attempt + 1}/{self.max_retries}")
                time.sleep(self.retry_delay)
            
            except Exception as e:
                if attempt == self.max_retries - 1:
                    self.stats['total_requests'] += 1
                    self.stats['failed_requests'] += 1
                    raise e
                print(f"⚠️ Unexpected error: {e}, retrying...")
                time.sleep(self.retry_delay)
        
        # Should not reach here
        raise Exception("Max retries exceeded")
    
    def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion for a single prompt"""
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = self._make_request(messages, **kwargs)
            
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                return content.strip()
            else:
                raise Exception("No completion generated")
        
        except Exception as e:
            print(f"❌ Groq completion error: {e}")
            raise
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate chat completion for conversation"""
        try:
            response = self._make_request(messages, **kwargs)
            
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                return content.strip()
            else:
                raise Exception("No chat completion generated")
        
        except Exception as e:
            print(f"❌ Groq chat error: {e}")
            raise
    
    def generate_structured_response(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Generate structured response with system and user prompts"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return self.chat(messages, **kwargs)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get API performance statistics"""
        avg_response_time = (
            self.stats['total_response_time'] / self.stats['successful_requests']
            if self.stats['successful_requests'] > 0 else 0
        )
        
        success_rate = (
            self.stats['successful_requests'] / self.stats['total_requests'] * 100
            if self.stats['total_requests'] > 0 else 0
        )
        
        return {
            'total_requests': self.stats['total_requests'],
            'successful_requests': self.stats['successful_requests'],
            'failed_requests': self.stats['failed_requests'],
            'success_rate': round(success_rate, 2),
            'average_response_time': round(avg_response_time * 1000, 0),  # ms
            'model': self.model,
            'cache_hits': self.stats['cache_hits']
        }

class GroqFallbackService:
    """Fallback service when Groq API is unavailable"""
    
    def __init__(self):
        self.fallback_responses = {
            'analysis': self._generate_analysis_fallback,
            'summary': self._generate_summary_fallback,
            'report': self._generate_report_fallback,
            'general': self._generate_general_fallback
        }
    
    def _generate_analysis_fallback(self, query: str, context: str) -> str:
        """Generate analysis fallback response"""
        return f"""**📊 ANALYSIS REPORT**

**Executive Summary:**
Analysis of "{query}" based on available blue carbon research data.

**Key Findings:**
• Blue carbon ecosystems are critical for climate change mitigation
• Coastal restoration projects show significant carbon sequestration potential
• Integrated management approaches yield optimal conservation outcomes
• Economic benefits through carbon credit mechanisms are substantial

**Implications:**
• Strategic importance for national climate commitments
• Requires coordinated stakeholder engagement
• Long-term monitoring and verification essential

**Recommendations:**
• Implement standardized monitoring protocols
• Develop comprehensive management frameworks
• Establish sustainable financing mechanisms
• Create stakeholder engagement strategies

*Note: This analysis is generated using fallback mode. For detailed insights, please ensure API connectivity.*"""
    
    def _generate_summary_fallback(self, query: str, context: str) -> str:
        """Generate summary fallback response"""
        return f"""**📄 SUMMARY**

**Overview:**
Summary addressing: {query}

**Main Points:**
• Blue carbon refers to carbon captured by coastal ecosystems
• Mangroves, seagrass beds, and salt marshes are key blue carbon habitats
• These ecosystems sequester carbon at rates higher than terrestrial forests
• Restoration and conservation are critical for climate goals

**Key Takeaways:**
• Blue carbon ecosystems provide multiple co-benefits
• Integrated management approaches are most effective
• Monitoring and verification systems are essential
• Economic incentives can drive conservation efforts

**Conclusions:**
Effective blue carbon management requires coordinated efforts across scientific, policy, and economic domains.

*Note: This summary is generated using fallback mode. For detailed insights, please ensure API connectivity.*"""
    
    def _generate_report_fallback(self, query: str, context: str) -> str:
        """Generate report fallback response"""
        return f"""**📈 PROFESSIONAL REPORT**

**1. INTRODUCTION**
This report addresses: {query}

**2. METHODOLOGY**
Analysis based on comprehensive blue carbon research database and established scientific literature.

**3. FINDINGS**
3.1 Blue carbon ecosystems demonstrate exceptional carbon sequestration capacity
3.2 Coastal restoration projects yield measurable climate benefits
3.3 Integrated management approaches optimize conservation outcomes
3.4 Economic mechanisms can incentivize conservation efforts

**4. IMPLICATIONS**
• Critical role in national climate strategies
• Significant potential for carbon offset markets
• Biodiversity conservation co-benefits
• Coastal protection and resilience enhancement

**5. RECOMMENDATIONS**
• Develop standardized monitoring protocols
• Establish comprehensive management frameworks
• Create sustainable financing mechanisms
• Implement stakeholder engagement strategies

**6. CONCLUSION**
Blue carbon ecosystems represent vital natural climate solutions requiring immediate and sustained conservation action.

**Report Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}

*Note: This report is generated using fallback mode. For detailed insights, please ensure API connectivity.*"""
    
    def _generate_general_fallback(self, query: str, context: str) -> str:
        """Generate general fallback response"""
        return f"""Based on the blue carbon research database:

**Response to:** {query}

**Key Information:**
• Blue carbon ecosystems include mangroves, seagrass beds, and salt marshes
• These habitats sequester carbon at exceptionally high rates
• Restoration and conservation are critical for climate change mitigation
• Economic benefits are available through carbon credit mechanisms

**Context:**
Blue carbon refers to carbon captured and stored by coastal and marine ecosystems. These environments are among the most effective carbon sinks on Earth but face significant threats from human activities and climate change.

**Suggestions for Further Information:**
• Ask for specific analysis of restoration methods
• Request detailed information about carbon sequestration rates
• Inquire about policy frameworks and governance approaches
• Explore economic mechanisms and financing options

*Note: This response is generated using fallback mode. For detailed insights, please ensure API connectivity.*"""
    
    def generate_fallback_response(self, query: str, context: str, response_type: str = "general") -> str:
        """Generate appropriate fallback response"""
        generator = self.fallback_responses.get(response_type, self.fallback_responses['general'])
        return generator(query, context)

# Global instances
_groq_client = None
_fallback_service = None

def get_groq_client() -> GroqAPIClient:
    """Get global Groq client instance"""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqAPIClient()
    return _groq_client

def get_fallback_service() -> GroqFallbackService:
    """Get fallback service instance"""
    global _fallback_service
    if _fallback_service is None:
        _fallback_service = GroqFallbackService()
    return _fallback_service