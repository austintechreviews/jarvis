"""
Headless web search module using SearXNG
"""

import logging
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class WebSearcher:
    """Headless web search engine using SearXNG"""
    
    def __init__(self, searxng_url: str = "http://192.168.1.248:8090"):
        """
        Initialize web searcher
        
        Args:
            searxng_url: URL of your SearXNG instance
        """
        self.searxng_url = searxng_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        
    def search(self, query: str, max_results: int = 5, categories: str = "general") -> List[Dict[str, Any]]:
        """
        Perform web search using SearXNG
        
        Args:
            query: Search query
            max_results: Maximum number of results
            categories: Search categories (general, news, images, videos, etc.)
            
        Returns:
            List of search results with title, snippet, and link
        """
        try:
            logger.info(f"Searching SearXNG: {query}")
            
            # Build URL
            encoded_query = quote(query)
            url = f"{self.searxng_url}/search?q={encoded_query}&categories={categories}&format=json"
            
            # Make request
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract results
            results = []
            for result in data.get('results', [])[:max_results]:
                results.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("content", ""),
                    "link": result.get("url", ""),
                    "engine": result.get("engine", ""),
                })
            
            logger.info(f"Found {len(results)} results from SearXNG")
            return results
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to SearXNG at {self.searxng_url}")
            return [{
                "title": "Search Error",
                "snippet": f"Cannot connect to SearXNG server at {self.searxng_url}. Please check the server is running.",
                "link": "",
                "engine": "error"
            }]
        
        except requests.exceptions.Timeout:
            logger.error("SearXNG request timed out")
            return [{
                "title": "Search Error",
                "snippet": "Search request timed out. Please try again.",
                "link": "",
                "engine": "error"
            }]
        
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return [{
                "title": "Search Error",
                "snippet": f"Search failed: {str(e)}",
                "link": "",
                "engine": "error"
            }]
    
    def search_news(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for news articles"""
        return self.search(query, max_results=max_results, categories="news")
    
    def search_images(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for images"""
        return self.search(query, max_results=max_results, categories="images")
    
    def instant_answer(self, query: str) -> Optional[str]:
        """Get instant answer from SearXNG (like Wikipedia summary)"""
        try:
            encoded_query = quote(query)
            url = f"{self.searxng_url}/search?q={encoded_query}&categories=general&format=json"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for infobox (instant answer)
            infobox = data.get('infobox')
            if infobox:
                return infobox.get('content', '')
            
            # Check for answers
            answers = data.get('answers', [])
            if answers:
                return str(answers[0])
            
            return None
        
        except Exception as e:
            logger.error(f"Instant answer error: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """Test connection to SearXNG server"""
        try:
            response = self.session.get(f"{self.searxng_url}/healthz", timeout=5)
            return response.status_code == 200
        except:
            # Try main page as fallback
            try:
                response = self.session.get(self.searxng_url, timeout=5)
                return response.status_code == 200
            except:
                return False
