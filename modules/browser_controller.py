"""
Browser automation using Playwright
"""

import logging
from typing import Optional, Dict, Any
import time

logger = logging.getLogger(__name__)

# Try to import playwright, handle case when not installed
try:
    from playwright.sync_api import sync_playwright, Browser, Page, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("Playwright not installed. Install with: pip install playwright && playwright install chromium")
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Page = None
    Playwright = None


class BrowserController:
    """Browser automation controller"""
    
    def __init__(self, headless: bool = False):
        """
        Initialize browser controller
        
        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_running = False
        
    def start(self) -> Dict[str, Any]:
        """Start browser instance"""
        if self.is_running:
            return {"success": True, "message": "Browser already running"}
        
        if not PLAYWRIGHT_AVAILABLE:
            return {"success": False, "message": "Playwright not installed"}
        
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            self.page = self.browser.new_page()
            self.is_running = True
            logger.info("Browser started successfully")
            return {"success": True, "message": "Browser started"}
        except Exception as e:
            logger.error(f"Failed to start browser: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def stop(self) -> Dict[str, Any]:
        """Stop browser instance"""
        if not self.is_running:
            return {"success": True, "message": "Browser not running"}
        
        try:
            if self.page:
                self.page.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            
            self.page = None
            self.browser = None
            self.playwright = None
            self.is_running = False
            logger.info("Browser stopped")
            return {"success": True, "message": "Browser stopped"}
        except Exception as e:
            logger.error(f"Error stopping browser: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigate to URL
        
        Args:
            url: URL to navigate to
            
        Returns:
            {"success": bool, "url": str, "title": str, "error": str}
        """
        try:
            # Ensure browser is running
            if not self.is_running:
                start_result = self.start()
                if not start_result["success"]:
                    return start_result
            
            # Add https:// if missing
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            
            # Navigate
            self.page.goto(url, wait_until='domcontentloaded', timeout=15000)
            
            # Wait a moment for page to settle
            time.sleep(0.5)
            
            title = self.page.title()
            final_url = self.page.url
            
            logger.info(f"Navigated to {final_url} - Title: {title}")
            
            return {
                "success": True,
                "url": final_url,
                "title": title,
                "error": ""
            }
        
        except Exception as e:
            logger.error(f"Navigation error: {str(e)}")
            return {
                "success": False,
                "url": url,
                "title": "",
                "error": str(e)
            }
    
    def execute(self, instruction: str) -> str:
        """
        Execute browser automation task
        
        Args:
            instruction: Natural language instruction
            
        Returns:
            Result of the operation
        """
        try:
            instruction_lower = instruction.lower()
            
            # Ensure browser is running
            if not self.is_running:
                self.start()
            
            # Navigation
            if any(kw in instruction_lower for kw in ['navigate', 'go to', 'open', 'visit']):
                url = self._extract_url(instruction)
                if url:
                    result = self.navigate(url)
                    if result['success']:
                        return f"✓ Navigated to {result['url']}\nPage title: {result['title']}"
                    else:
                        return f"✗ Navigation failed: {result['error']}"
                else:
                    return "Could not extract URL from instruction"
            
            # Click element
            if 'click' in instruction_lower:
                selector = self._extract_selector(instruction)
                if selector:
                    self.page.click(selector)
                    time.sleep(0.3)
                    return f"✓ Clicked element: {selector}"
                else:
                    return "Could not identify element to click"
            
            # Type text
            if 'type' in instruction_lower or 'fill' in instruction_lower:
                text = self._extract_text_to_type(instruction)
                if text:
                    # Try to type into first input field
                    try:
                        self.page.fill('input, textarea', text)
                        return f"✓ Typed: {text}"
                    except:
                        return "Could not find input field to fill"
            
            # Screenshot
            if 'screenshot' in instruction_lower:
                path = f"/tmp/browser_screenshot_{int(time.time())}.png"
                self.page.screenshot(path=path)
                return f"✓ Screenshot saved: {path}"
            
            # Get page info
            if 'info' in instruction_lower or 'current' in instruction_lower:
                info = self.get_page_info()
                return f"Current page: {info.get('url', 'N/A')}\nTitle: {info.get('title', 'N/A')}"
            
            return "Browser operation completed (instruction not fully recognized)"
        
        except Exception as e:
            logger.error(f"Browser execution error: {str(e)}")
            return f"Error: {str(e)}"
    
    def _extract_url(self, text: str) -> Optional[str]:
        """Extract URL from natural language text - IMPROVED"""
        import re
        
        # Remove common navigation words
        text_cleaned = text.lower()
        for word in ['navigate to', 'go to', 'open', 'visit', 'browse to', 'navigate', 'to']:
            text_cleaned = text_cleaned.replace(word, '')
        
        text_cleaned = text_cleaned.strip()
        
        # 1. Look for explicit URLs
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        
        # 2. Check for common domains (even without TLD)
        common_sites = {
            'youtube': 'youtube.com',
            'google': 'google.com',
            'github': 'github.com',
            'reddit': 'reddit.com',
            'twitter': 'twitter.com',
            'facebook': 'facebook.com',
            'instagram': 'instagram.com',
            'linkedin': 'linkedin.com',
            'amazon': 'amazon.com',
            'netflix': 'netflix.com',
            'wikipedia': 'wikipedia.org',
            'stackoverflow': 'stackoverflow.com',
            'stack overflow': 'stackoverflow.com',
        }
        
        for keyword, full_domain in common_sites.items():
            if keyword in text_cleaned:
                return full_domain
        
        # 3. Look for anything with a TLD
        words = text_cleaned.split()
        for word in words:
            word = word.strip('.,!?;:')
            if '.' in word and any(tld in word for tld in ['.com', '.org', '.net', '.io', '.dev', '.ai']):
                return word
        
        # 4. Single word - assume .com
        if len(words) == 1 and words[0]:
            word = words[0]
            if ' ' not in word and '.' not in word:
                return f"{word}.com"
        
        return None
    
    def _extract_selector(self, instruction: str) -> Optional[str]:
        """Extract CSS selector from instruction"""
        instruction_lower = instruction.lower()
        
        # Common selectors
        if 'button' in instruction_lower:
            return 'button'
        if 'link' in instruction_lower:
            return 'a'
        if 'search' in instruction_lower:
            return 'input[type="search"], input[name="q"]'
        if 'login' in instruction_lower:
            return 'button[type="submit"], input[type="submit"]'
        
        # Look for text in quotes
        import re
        pattern = r'["\'](.+?)["\']'
        match = re.search(pattern, instruction)
        if match:
            # Try to find element with this text
            return f'text={match.group(1)}'
        
        return None
    
    def _extract_text_to_type(self, instruction: str) -> Optional[str]:
        """Extract text to type from instruction"""
        import re
        
        # Look for text in quotes
        pattern = r'["\'](.+?)["\']'
        match = re.search(pattern, instruction)
        if match:
            return match.group(1)
        
        # Try to extract text after "type" or "fill"
        for kw in ['type', 'fill']:
            if kw in instruction.lower():
                idx = instruction.lower().find(kw)
                text = instruction[idx + len(kw):].strip()
                # Remove common words
                for word in ['the', 'into', 'in', 'text', 'box', 'field']:
                    text = text.replace(word, '').strip()
                return text.strip() if text else None
        
        return None
    
    def get_page_info(self) -> Dict[str, Any]:
        """Get current page information"""
        if not self.is_running or not self.page:
            return {"error": "Browser not running", "url": "", "title": ""}
        
        return {
            "url": self.page.url,
            "title": self.page.title(),
            "is_running": self.is_running
        }
    
    def click(self, selector: str) -> Dict[str, Any]:
        """Click an element by selector"""
        try:
            if not self.is_running:
                return {"success": False, "error": "Browser not running"}
            
            self.page.click(selector)
            time.sleep(0.3)
            return {"success": True, "message": f"Clicked: {selector}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def fill(self, selector: str, text: str) -> Dict[str, Any]:
        """Fill an input field"""
        try:
            if not self.is_running:
                return {"success": False, "error": "Browser not running"}
            
            self.page.fill(selector, text)
            return {"success": True, "message": f"Filled {selector} with: {text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def screenshot(self, path: str = None) -> Dict[str, Any]:
        """Take a screenshot"""
        try:
            if not self.is_running:
                return {"success": False, "error": "Browser not running"}
            
            if not path:
                path = f"/tmp/browser_screenshot_{int(time.time())}.png"
            
            self.page.screenshot(path=path)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}
