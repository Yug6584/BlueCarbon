import requests
import time
from typing import List, Dict, Any, Optional
from models.response_models import WebResult
from config import Config

class WebSearchService:
    """Web search service using SerpApi for comprehensive answers"""
    
    def __init__(self):
        # Force use the correct API key
        self.api_key = "e89e63271e1ae3de7152caa418ac59ac9dd6b4b798410f9cdedf58fb40687442"
        self.base_url = "https://serpapi.com/search.json"
        
        # Option to manually disable web search (set to False if SerpAPI is down)
        self.force_disable = False  # Set to True to disable web search completely
        
        self.enabled = bool(self.api_key) and not self.force_disable
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3  # Temporarily disable after 3 failures
        
        print(f"🌐 WebSearchService initialized (Enabled: {self.enabled})")
        if self.force_disable:
            print("⚠️ Web search manually disabled (force_disable=True)")
        elif self.enabled:
            print(f"🔑 Using API key: {self.api_key[:20]}...")
            print("💡 Tip: If SerpAPI is down, set force_disable=True in web_search_service.py")
        else:
            print("⚠️ Web search disabled - no API key configured")
    
    def should_search(self, query: str, retrieval_confidence: float, similarity_threshold: float = 0.3) -> bool:
        """Determine if web search should be triggered"""
        if not self.enabled:
            return False
        
        # Trigger web search if:
        # 1. Low retrieval confidence
        # 2. Query contains recent/current terms
        # 3. Query asks for latest information
        
        recent_terms = ['latest', 'recent', 'current', '2024', '2025', 'new', 'update', 'today']
        has_recent_terms = any(term in query.lower() for term in recent_terms)
        
        return retrieval_confidence < similarity_threshold or has_recent_terms
    
    def search_web(self, query: str, max_results: int = 5) -> List[WebResult]:
        """Search web using SerpApi with retry logic"""
        if not self.enabled:
            print("⚠️ Web search disabled - no API key configured")
            return []
        
        # Temporarily disable if too many consecutive failures
        if self.consecutive_failures >= self.max_consecutive_failures:
            print(f"⚠️ Web search temporarily disabled due to {self.consecutive_failures} consecutive failures")
            return []
        
        max_retries = 2
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Enhance query for blue carbon context
                enhanced_query = f"{query} blue carbon coastal ecosystems"
                
                params = {
                    "q": enhanced_query,
                    "api_key": self.api_key,
                    "engine": "google",
                    "num": max_results,
                    "gl": "us",
                    "hl": "en"
                }
                
                print(f"🌐 Web search attempt {attempt + 1}/{max_retries} for: {query}")
                response = requests.get(self.base_url, params=params, timeout=20)
                
                if response.status_code == 200:
                    data = response.json()
                    results = self._parse_search_results(data, query)
                    print(f"✅ Web search successful: {len(results)} results")
                    self.consecutive_failures = 0  # Reset on success
                    return results
                elif response.status_code == 503:
                    print(f"⚠️ SerpApi temporarily unavailable (503) - attempt {attempt + 1}/{max_retries}")
                    print("   SerpAPI servers are experiencing issues. Your API key is valid.")
                    print("   The chatbot will continue working without web search results.")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                elif response.status_code == 429:
                    print(f"⚠️ SerpApi rate limit exceeded (429) - skipping web search")
                    self.consecutive_failures += 1
                    return []
                else:
                    print(f"⚠️ SerpApi error: {response.status_code} - {response.text[:200]}")
                    self.consecutive_failures += 1
                    return []
                    
            except requests.exceptions.Timeout:
                print(f"⚠️ Web search timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    print("❌ Web search failed after all retries - continuing without web results")
                    self.consecutive_failures += 1
                    return []
            except requests.exceptions.ConnectionError as e:
                print(f"⚠️ Connection error: {e}")
                self.consecutive_failures += 1
                return []
            except Exception as e:
                print(f"❌ Web search error: {e}")
                self.consecutive_failures += 1
                return []
        
        print("⚠️ Web search unavailable - continuing without web results")
        self.consecutive_failures += 1
        return []
    
    def _parse_search_results(self, data: Dict[str, Any], original_query: str) -> List[WebResult]:
        """Parse SerpApi response into WebResult objects with image support"""
        results = []
        
        # Parse organic results
        organic_results = data.get("organic_results", [])
        
        for result in organic_results:
            try:
                # Extract thumbnail/image if available
                thumbnail = None
                if "thumbnail" in result:
                    thumbnail = result["thumbnail"]
                elif "rich_snippet" in result and "top" in result["rich_snippet"]:
                    # Check for images in rich snippets
                    rich_snippet = result["rich_snippet"]["top"]
                    if "images" in rich_snippet:
                        thumbnail = rich_snippet["images"][0] if rich_snippet["images"] else None
                
                web_result = WebResult(
                    title=result.get("title", ""),
                    url=result.get("link", ""),
                    snippet=result.get("snippet", ""),
                    relevance_score=0.8,  # Default high relevance from search
                    source_type="web",
                    published_date=result.get("date"),
                    thumbnail_url=thumbnail
                )
                results.append(web_result)
                
            except Exception as e:
                print(f"⚠️ Error parsing search result: {e}")
                continue
        
        # Parse news results if available
        news_results = data.get("news_results", [])
        
        for result in news_results[:2]:  # Limit news results
            try:
                thumbnail = result.get("thumbnail")
                
                web_result = WebResult(
                    title=result.get("title", ""),
                    url=result.get("link", ""),
                    snippet=result.get("snippet", ""),
                    relevance_score=0.9,  # Higher relevance for news
                    source_type="news",
                    published_date=result.get("date"),
                    thumbnail_url=thumbnail
                )
                results.append(web_result)
                
            except Exception as e:
                print(f"⚠️ Error parsing news result: {e}")
                continue
        
        # Parse image results for visual content
        images_results = data.get("images_results", [])
        
        for result in images_results[:3]:  # Limit to 3 most relevant images
            try:
                web_result = WebResult(
                    title=result.get("title", "Image"),
                    url=result.get("link", ""),
                    snippet=f"Image: {result.get('title', 'Blue carbon related image')}",
                    relevance_score=0.7,
                    source_type="image",
                    thumbnail_url=result.get("thumbnail"),
                    image_url=result.get("original")
                )
                results.append(web_result)
                
            except Exception as e:
                print(f"⚠️ Error parsing image result: {e}")
                continue
        
        print(f"🔍 Web search found {len(results)} results for: {original_query}")
        return results
    
    def integrate_web_results(self, local_chunks: List[Dict], web_results: List[WebResult]) -> List[Dict]:
        """Integrate web search results with local chunks including images"""
        integrated_chunks = local_chunks.copy()
        
        for web_result in web_results:
            # Convert web result to chunk format
            web_chunk = {
                "text": f"{web_result.title}. {web_result.snippet}",
                "source_file": web_result.url,
                "source_type": web_result.source_type,
                "similarity_score": web_result.relevance_score,
                "chunk_id": f"web_{hash(web_result.url)}",
                "page_number": 0,
                "metadata": {
                    "title": web_result.title,
                    "url": web_result.url,
                    "source_type": web_result.source_type,
                    "published_date": web_result.published_date,
                    "thumbnail_url": web_result.thumbnail_url,
                    "image_url": web_result.image_url,
                    "has_visual_content": bool(web_result.thumbnail_url or web_result.image_url)
                }
            }
            integrated_chunks.append(web_chunk)
        
        return integrated_chunks
    
    def search_with_images(self, query: str, max_results: int = 3, max_images: int = 3) -> Dict[str, Any]:
        """Enhanced search that includes images for comprehensive responses"""
        if not self.enabled:
            return {"results": [], "images": []}
        
        try:
            print(f"🌐 Enhanced search with images for: {query} (max_images: {max_images})")
            
            # First get regular web results
            web_results = self.search_web(query, max_results)
            
            # Get comprehensive image results with multiple calls if needed
            images = self.get_high_quality_images(query, max_images)
            
            result = {
                "results": web_results,
                "images": images,
                "total_results": len(web_results),
                "total_images": len(images)
            }
            
            print(f"✅ Enhanced search completed: {len(web_results)} web results, {len(images)} images")
            return result
            
        except Exception as e:
            print(f"❌ Enhanced web search error: {e}")
            import traceback
            traceback.print_exc()
            return {"results": [], "images": []}
    
    def get_high_quality_images(self, query: str, max_images: int = 3) -> List[Dict[str, Any]]:
        """Get high-quality images with OPTIMIZED single search strategy"""
        if not self.enabled:
            return []
        
        try:
            # ULTRA-FAST single search strategy
            enhanced_query = f"{query} blue carbon"
            all_images = self._search_images_batch(enhanced_query, min(max_images * 2, 10))  # Get more to account for duplicates
            
            # Remove duplicates based on URL (check both original and thumbnail)
            unique_images = []
            seen_urls = set()
            
            for img in all_images:
                # Try both original and thumbnail URLs for deduplication
                original_url = img.get('original', '')
                thumbnail_url = img.get('thumbnail', '')
                
                # Create a unique key from both URLs
                url_key = f"{original_url}|{thumbnail_url}"
                
                # Only add if we haven't seen this combination and at least one URL exists
                if (original_url or thumbnail_url) and url_key not in seen_urls:
                    seen_urls.add(url_key)
                    unique_images.append(img)
                    
                    # Debug: print what we're adding
                    if len(unique_images) <= 3:
                        print(f"  ✓ Image {len(unique_images)}: {img.get('title', 'No title')[:50]}")
            
            # Apply quality filtering
            quality_filtered = self.filter_image_quality(unique_images)
            
            print(f"🖼️ OPTIMIZED Image search: {len(all_images)} found → {len(unique_images)} unique → {len(quality_filtered)} quality filtered")
            
            return quality_filtered[:max_images]
            
        except Exception as e:
            print(f"❌ High-quality image search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _search_images_batch(self, query: str, num_images: int) -> List[Dict[str, Any]]:
        """Search for a batch of images with specific query and retry logic"""
        if num_images <= 0:
            return []
        
        max_retries = 2
        
        try:
            image_params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google",
                "tbm": "isch",  # Image search
                "num": min(num_images, 20),  # Google Images API limit per request
                "gl": "us",
                "hl": "en",
                "safe": "active",
                "ijn": 0  # Page number (can be used for pagination)
            }
            
            images = []
            
            # Make multiple requests if we need more than 20 images
            pages_needed = (num_images + 19) // 20  # Ceiling division
            
            for page in range(min(pages_needed, 1)):  # OPTIMIZED: Limit to 1 page only for performance
                image_params["ijn"] = page
                
                for attempt in range(max_retries):
                    try:
                        image_response = requests.get(self.base_url, params=image_params, timeout=20)
                        
                        if image_response.status_code == 200:
                            image_data = image_response.json()
                            images_results = image_data.get("images_results", [])
                            
                            print(f"  📸 Found {len(images_results)} raw image results from SerpAPI")
                            
                            for result in images_results:
                                if len(images) >= num_images:
                                    break
                                    
                                try:
                                    image_info = {
                                        "title": result.get("title", "Blue carbon related image"),
                                        "thumbnail": result.get("thumbnail"),
                                        "original": result.get("original"),
                                        "source": result.get("source"),
                                        "link": result.get("link"),
                                        "position": result.get("position", len(images)),
                                        "search_query": query,
                                        "page": page
                                    }
                                    
                                    # Only add if we have at least a thumbnail or original
                                    if image_info["thumbnail"] or image_info["original"]:
                                        images.append(image_info)
                                        
                                except Exception as e:
                                    print(f"⚠️ Error parsing image result: {e}")
                                    continue
                            
                            break  # Success, exit retry loop
                        
                        elif image_response.status_code == 503:
                            print(f"⚠️ Image search temporarily unavailable (503) - attempt {attempt + 1}/{max_retries}")
                            if attempt < max_retries - 1:
                                time.sleep(2)
                                continue
                            else:
                                print("⚠️ Image search failed after retries - skipping images")
                                break
                        elif image_response.status_code == 429:
                            print(f"⚠️ Image search rate limit exceeded (429) - skipping images")
                            break
                        else:
                            print(f"⚠️ Image search failed with status: {image_response.status_code}")
                            break
                            
                    except requests.exceptions.Timeout:
                        print(f"⚠️ Image search timeout on attempt {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            time.sleep(2)
                            continue
                        else:
                            print("⚠️ Image search timed out - skipping images")
                            break
                    except Exception as img_error:
                        print(f"⚠️ Image search request failed for page {page}: {img_error}")
                        break
                
                # Small delay between requests to be respectful
                if page < pages_needed - 1:
                    time.sleep(0.5)
            
            print(f"🔍 Batch search for '{query}': {len(images)} images found")
            return images
            
        except Exception as e:
            print(f"❌ Image batch search error: {e}")
            return []
    
    def filter_image_quality(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter images by quality criteria - RELAXED for better results"""
        if not images:
            return images
        
        filtered = []
        
        for img in images:
            try:
                # Check if we have valid URLs
                thumbnail = img.get('thumbnail', '')
                original = img.get('original', '')
                
                if not thumbnail and not original:
                    continue
                
                # RELAXED: Accept all images with valid URLs
                # Just add quality scoring for sorting
                
                title = img.get('title', '').lower()
                
                # Prefer images with blue carbon related terms in title
                blue_carbon_terms = [
                    'blue carbon', 'mangrove', 'seagrass', 'salt marsh', 'kelp',
                    'coastal', 'marine', 'carbon', 'ecosystem', 'restoration',
                    'conservation', 'wetland', 'sequestration', 'cycle', 'diagram',
                    'process', 'chart', 'illustration'
                ]
                
                title_relevance = sum(1 for term in blue_carbon_terms if term in title)
                img['title_relevance'] = title_relevance
                
                # Check source quality
                source = img.get('source', '').lower()
                trusted_sources = [
                    'nature', 'science', 'noaa', 'epa', 'unep', 'worldbank',
                    'ipcc', 'iucn', 'wikipedia', 'britannica', 'nationalgeographic',
                    'smithsonian', 'nasa', 'usgs', 'edu', 'gov'
                ]
                
                source_quality = 1 if any(trusted in source for trusted in trusted_sources) else 0.5
                img['source_quality'] = source_quality
                
                # Calculate overall quality score (but don't filter out)
                quality_score = (title_relevance * 0.6) + (source_quality * 0.4)
                img['quality_score'] = quality_score
                
                # ACCEPT ALL IMAGES - just score them for sorting
                filtered.append(img)
                
            except Exception as e:
                print(f"⚠️ Error filtering image: {e}")
                continue
        
        # Sort by quality score and title relevance
        filtered.sort(key=lambda x: (x.get('quality_score', 0), x.get('title_relevance', 0)), reverse=True)
        
        print(f"🔍 Quality filtering: {len(filtered)} images passed quality checks (relaxed filter)")
        
        return filtered

# Global instance
_web_search_service = None

def get_web_search_service() -> WebSearchService:
    """Get global web search service instance"""
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service