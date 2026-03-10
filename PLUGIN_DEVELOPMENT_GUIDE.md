# JARVIS Plugin Development Guide

## Complete Guide to Creating Plugins for JARVIS

**Version:** 1.0  
**Last Updated:** March 2026  
**Author:** JARVIS Development Team

---

## Table of Contents

1. [Introduction](#introduction)
2. [Plugin Architecture](#plugin-architecture)
3. [Getting Started](#getting-started)
4. [Plugin Structure](#plugin-structure)
5. [Step-by-Step Tutorial](#step-by-step-tutorial)
6. [Advanced Features](#advanced-features)
7. [Best Practices](#best-practices)
8. [Example Plugins](#example-plugins)
9. [Testing & Debugging](#testing--debugging)
10. [Publishing Plugins](#publishing-plugins)
11. [Troubleshooting](#troubleshooting)
12. [API Reference](#api-reference)

---

## Introduction

### What is a JARVIS Plugin?

A JARVIS plugin is a Python module that extends JARVIS's capabilities by adding new tools and functionality. Plugins allow you to:

- **Add new services** (Spotify, Email, Calendar, etc.)
- **Integrate APIs** (Twitter, GitHub, Slack, etc.)
- **Automate tasks** (File operations, System commands, etc.)
- **Extend functionality** (Custom workflows, Integrations, etc.)

### Why Create Plugins?

✅ **Modular** - Add/remove features without modifying core code  
✅ **Shareable** - Distribute plugins to other JARVIS users  
✅ **Maintainable** - Isolated code, easier to debug  
✅ **Extensible** - Unlimited possibilities for new features  

### Plugin Examples

| Plugin | Purpose | Complexity |
|--------|---------|------------|
| **Weather** | Get weather information | Beginner |
| **Spotify** | Control music playback | Intermediate |
| **Email** | Send/read emails | Intermediate |
| **GitHub** | Manage repositories | Advanced |
| **Home Assistant** | Smart home control | Advanced |

---

## Plugin Architecture

### Overview

```
┌─────────────────────────────────────────────────────────┐
│                    JARVIS CORE                           │
│  - LLM Tool Router                                       │
│  - Plugin Manager                                        │
│  - Voice Assistant                                       │
└─────────────────────────────────────────────────────────┘
                         │
                         ↓ Auto-discovers
┌─────────────────────────────────────────────────────────┐
│                  ~/jarvis/plugins/                       │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Weather    │  │   Spotify    │  │   Your       │  │
│  │   Plugin     │  │   Plugin     │  │   Plugin     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Plugin Lifecycle

```
1. Discovery
   ↓
   JARVIS scans ~/jarvis/plugins/*.py
   
2. Loading
   ↓
   Imports plugin module
   Finds JARVISPlugin subclass
   
3. Initialization
   ↓
   Checks dependencies
   Calls initialize()
   
4. Registration
   ↓
   Registers tools with Plugin Manager
   Adds to system prompt
   
5. Execution
   ↓
   LLM routes commands to plugin tools
   Tools execute and return results
   
6. Cleanup
   ↓
   Called on JARVIS shutdown
   Release resources
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- JARVIS installed and working
- Basic Python knowledge
- Text editor (VS Code recommended)

### Setup Development Environment

```bash
# Navigate to JARVIS directory
cd ~/jarvis

# Activate virtual environment
source venv/bin/activate  # or: conda activate jarvis

# Create plugins directory (if not exists)
mkdir -p ~/jarvis/plugins

# Create your plugin file
touch ~/jarvis/plugins/my_plugin.py
```

### Plugin Directory Structure

```
~/jarvis/
├── plugins/
│   ├── __init__.py              # Required (can be empty)
│   ├── my_plugin.py             # Your plugin
│   ├── weather_plugin.py        # Example plugin
│   └── spotify_plugin.py        # Example plugin
├── config/
│   └── my_plugin_config.json    # Plugin configuration (optional)
└── modules/
    └── plugin_system.py         # Plugin manager (don't modify)
```

---

## Plugin Structure

### Basic Plugin Template

```python
"""
My Plugin Name
Brief description of what your plugin does
"""

import logging
from typing import Dict, Callable
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.plugin_system import JARVISPlugin

logger = logging.getLogger(__name__)


class MyPlugin(JARVISPlugin):
    """
    Your plugin class
    
    This class must inherit from JARVISPlugin
    """
    
    # ========== REQUIRED METADATA ==========
    
    name = "my_plugin"
    version = "1.0.0"
    description = "What your plugin does"
    author = "Your Name"
    
    # Dependencies (Python package names)
    required_packages = ["requests"]  # Optional: []
    
    # ========== INITIALIZATION ==========
    
    def __init__(self):
        """Initialize plugin"""
        super().__init__()
        # Your initialization code here
        self.api_key = None
        self.base_url = None
    
    def check_dependencies(self) -> bool:
        """
        Check if all required packages are installed
        
        Returns:
            True if all dependencies are met
        """
        # You can override this for custom checks
        return super().check_dependencies()
    
    def initialize(self) -> bool:
        """
        Setup plugin (called after __init__)
        
        Load config, connect to APIs, etc.
        
        Returns:
            True if successful
        """
        try:
            # Load configuration
            config_file = Path.home() / "jarvis" / "config" / "my_plugin_config.json"
            
            if config_file.exists():
                import json
                with open(config_file) as f:
                    config = json.load(f)
                self.api_key = config.get("api_key")
                self.base_url = config.get("base_url")
            
            logger.info(f"{self.name} plugin initialized")
            return True
            
        except Exception as e:
            logger.error(f"{self.name} initialization failed: {str(e)}")
            return False
    
    # ========== TOOLS ==========
    
    def get_tools(self) -> Dict[str, Callable]:
        """
        Return dictionary of tool functions
        
        Returns:
            {
                "tool_name": function,
                "another_tool": another_function
            }
        """
        return {
            "do_something": self.do_something,
            "get_info": self.get_info
        }
    
    def do_something(self, param1: str, param2: int = 10) -> Dict:
        """
        Tool function 1
        
        Args:
            param1: Description of param1
            param2: Description of param2 (optional)
            
        Returns:
            {
                "success": bool,
                "message": str,
                "data": any (optional)
            }
        """
        try:
            # Your tool logic here
            result = f"Processed {param1} with value {param2}"
            
            return {
                "success": True,
                "message": result,
                "data": {"processed": True}
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_info(self) -> Dict:
        """
        Tool function 2
        
        Returns:
            Tool result dictionary
        """
        try:
            # Your logic here
            return {
                "success": True,
                "message": "Information retrieved"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========== SYSTEM PROMPT ==========
    
    def get_system_prompt_addition(self) -> str:
        """
        Text to add to JARVIS system prompt
        
        Describe what your plugin can do and how to use it.
        This helps the LLM understand when to use your tools.
        
        Returns:
            Markdown-formatted text
        """
        return """**My Plugin Tools:**

- `my_plugin.do_something(param1, param2)` - Does something useful
  - param1: What to process
  - param2: How to process it (default: 10)
- `my_plugin.get_info()` - Gets information

Examples:
- "Use my plugin to process data"
- "Get information from my plugin"
- "Do something with this file"
"""
    
    # ========== CLEANUP ==========
    
    def cleanup(self):
        """
        Cleanup resources (called on shutdown)
        
        Close connections, save state, etc.
        """
        logger.info(f"{self.name} plugin cleanup")
        # Your cleanup code here


# Optional: Create config template
def create_config_template():
    """Create a config template for this plugin"""
    config = {
        "api_key": "your_api_key_here",
        "base_url": "https://api.example.com",
        "settings": {
            "timeout": 30,
            "retries": 3
        }
    }
    
    config_path = Path.home() / "jarvis" / "config" / "my_plugin_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Config template created: {config_path}")


if __name__ == "__main__":
    # Run this to create config template
    create_config_template()
```

---

## Step-by-Step Tutorial

### Creating Your First Plugin: "Hello World"

Let's create a simple plugin that greets users.

#### Step 1: Create Plugin File

```bash
cd ~/jarvis/plugins
nano hello_plugin.py
```

#### Step 2: Add Basic Structure

```python
"""
Hello Plugin
Greets users and demonstrates plugin basics
"""

import logging
from typing import Dict, Callable
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.plugin_system import JARVISPlugin

logger = logging.getLogger(__name__)


class HelloPlugin(JARVISPlugin):
    name = "hello"
    version = "1.0.0"
    description = "Greets users and says hello"
    author = "Your Name"
    required_packages = []
    
    def get_tools(self) -> Dict[str, Callable]:
        return {
            "greet": self.greet,
            "hello": self.hello
        }
    
    def greet(self, name: str = "World") -> Dict:
        """
        Greet someone by name
        
        Args:
            name: Name to greet
            
        Returns:
            Greeting message
        """
        message = f"Hello, {name}! Welcome to JARVIS!"
        
        logger.info(f"Greeting: {name}")
        
        return {
            "success": True,
            "message": message
        }
    
    def hello(self) -> Dict:
        """
        Say hello
        
        Returns:
            Hello message
        """
        return {
            "success": True,
            "message": "Hello! How can I help you today?"
        }
    
    def get_system_prompt_addition(self) -> str:
        return """**Hello Plugin:**

- `hello.greet(name)` - Greet someone by name
- `hello.hello()` - Say hello

Examples:
- "Say hello"
- "Greet Austin"
- "Welcome me"
"""
    
    def cleanup(self):
        logger.info("Hello plugin cleanup")
```

#### Step 3: Test Your Plugin

```bash
# Restart JARVIS
python jarvis.py

# In JARVIS, try:
You: say hello
JARVIS: [Uses hello.hello()]
Hello! How can I help you today?

You: greet Austin
JARVIS: [Uses hello.greet(name="Austin")]
Hello, Austin! Welcome to JARVIS!
```

---

## Advanced Features

### 1. API Integration

Example: Integrating with a REST API

```python
import requests

class APIPlugin(JARVISPlugin):
    name = "api_plugin"
    version = "1.0.0"
    description = "Integrates with external API"
    required_packages = ["requests"]
    
    def initialize(self) -> bool:
        try:
            config_file = Path.home() / "jarvis" / "config" / "api_plugin_config.json"
            
            if config_file.exists():
                import json
                with open(config_file) as f:
                    config = json.load(f)
                self.api_key = config.get("api_key")
                self.base_url = config.get("base_url", "https://api.example.com")
            
            # Test connection
            response = requests.get(f"{self.base_url}/health")
            if response.status_code != 200:
                logger.warning("API health check failed")
            
            return True
        except Exception as e:
            logger.error(f"API plugin init failed: {str(e)}")
            return False
    
    def get_tools(self) -> Dict[str, Callable]:
        return {
            "fetch_data": self.fetch_data,
            "post_data": self.post_data
        }
    
    def fetch_data(self, endpoint: str) -> Dict:
        """
        Fetch data from API endpoint
        
        Args:
            endpoint: API endpoint path
            
        Returns:
            API response data
        """
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "data": response.json()
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"API request failed: {str(e)}"
            }
    
    def post_data(self, endpoint: str, data: Dict) -> Dict:
        """
        Post data to API endpoint
        
        Args:
            endpoint: API endpoint path
            data: Data to post
            
        Returns:
            API response
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            response = requests.post(
                f"{self.base_url}/{endpoint}",
                json=data,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "data": response.json()
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"API post failed: {str(e)}"
            }
```

### 2. Database Integration

Example: SQLite database for persistent storage

```python
import sqlite3

class DatabasePlugin(JARVISPlugin):
    name = "database"
    version = "1.0.0"
    description = "Persistent data storage"
    required_packages = []
    
    def initialize(self) -> bool:
        try:
            db_path = Path.home() / "jarvis" / "data" / "plugin_data.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
            self._create_tables()
            
            logger.info("Database plugin initialized")
            return True
        except Exception as e:
            logger.error(f"Database init failed: {str(e)}")
            return False
    
    def _create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def get_tools(self) -> Dict[str, Callable]:
        return {
            "store": self.store_data,
            "retrieve": self.retrieve_data,
            "delete": self.delete_data
        }
    
    def store_data(self, key: str, value: str) -> Dict:
        """Store data in database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO user_data (key, value) VALUES (?, ?)",
                (key, value)
            )
            self.conn.commit()
            
            return {
                "success": True,
                "message": f"Stored: {key}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def retrieve_data(self, key: str) -> Dict:
        """Retrieve data from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT value FROM user_data WHERE key = ?", (key,))
            result = cursor.fetchone()
            
            if result:
                return {
                    "success": True,
                    "value": result[0]
                }
            else:
                return {
                    "success": False,
                    "error": f"Key not found: {key}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_data(self, key: str) -> Dict:
        """Delete data from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM user_data WHERE key = ?", (key,))
            self.conn.commit()
            
            return {
                "success": True,
                "message": f"Deleted: {key}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup(self):
        if hasattr(self, 'conn'):
            self.conn.close()
        logger.info("Database plugin cleanup")
```

### 3. Async Operations

Example: Async HTTP requests

```python
import asyncio
import aiohttp

class AsyncPlugin(JARVISPlugin):
    name = "async_plugin"
    version = "1.0.0"
    description = "Async operations example"
    required_packages = ["aiohttp"]
    
    def get_tools(self) -> Dict[str, Callable]:
        return {
            "fetch_multiple": self.fetch_multiple_urls
        }
    
    def fetch_multiple_urls(self, urls: list) -> Dict:
        """
        Fetch multiple URLs concurrently
        
        Args:
            urls: List of URLs to fetch
            
        Returns:
            Results from all URLs
        """
        async def fetch(session, url):
            try:
                async with session.get(url, timeout=30) as response:
                    return {
                        "url": url,
                        "status": response.status,
                        "content": await response.text()
                    }
            except Exception as e:
                return {
                    "url": url,
                    "error": str(e)
                }
        
        async def fetch_all(urls):
            async with aiohttp.ClientSession() as session:
                tasks = [fetch(session, url) for url in urls]
                return await asyncio.gather(*tasks)
        
        try:
            results = asyncio.run(fetch_all(urls))
            
            return {
                "success": True,
                "results": results
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
```

---

## Best Practices

### 1. Error Handling

✅ **DO:**
```python
def my_tool(self, param: str) -> Dict:
    try:
        # Your logic
        result = do_something(param)
        
        return {
            "success": True,
            "message": "Operation completed",
            "data": result
        }
    except SpecificError as e:
        logger.error(f"Specific error: {str(e)}")
        return {
            "success": False,
            "error": f"Specific error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
```

❌ **DON'T:**
```python
def my_tool(self, param: str) -> Dict:
    # No error handling!
    result = do_something(param)
    return result  # Might crash JARVIS
```

### 2. Logging

✅ **DO:**
```python
logger = logging.getLogger(__name__)

def my_tool(self, param: str) -> Dict:
    logger.info(f"my_tool called with param: {param}")
    
    try:
        result = do_something(param)
        logger.info(f"my_tool completed successfully")
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"my_tool failed: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}
```

### 3. Configuration

✅ **DO:**
```python
def initialize(self) -> bool:
    config_file = Path.home() / "jarvis" / "config" / "my_plugin_config.json"
    
    if config_file.exists():
        import json
        with open(config_file) as f:
            config = json.load(f)
        self.api_key = config.get("api_key")
    else:
        logger.warning("Config file not found, using defaults")
        self.api_key = None
    
    return True
```

### 4. System Prompt

✅ **DO:**
```python
def get_system_prompt_addition(self) -> str:
    return """**My Plugin Tools:**

- `my_plugin.tool_name(param1, param2)` - Clear description
  - param1: What it does
  - param2: What it does (optional, default: value)

Examples:
- "Natural language example 1"
- "Natural language example 2"
"""
```

❌ **DON'T:**
```python
def get_system_prompt_addition(self) -> str:
    return "I have tools"  # Too vague!
```

### 5. Resource Management

✅ **DO:**
```python
def cleanup(self):
    """Cleanup all resources"""
    if hasattr(self, 'conn'):
        self.conn.close()
    if hasattr(self, 'session'):
        self.session.close()
    logger.info(f"{self.name} plugin cleanup complete")
```

---

## Example Plugins

### Beginner: Quote of the Day

```python
"""
Quote Plugin
Provides inspirational quotes
"""

import logging
import random
from typing import Dict, Callable
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.plugin_system import JARVISPlugin

logger = logging.getLogger(__name__)


class QuotePlugin(JARVISPlugin):
    name = "quote"
    version = "1.0.0"
    description = "Provides inspirational quotes"
    author = "JARVIS Team"
    required_packages = []
    
    QUOTES = [
        {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
        {"text": "Innovation distinguishes between a leader and a follower.", "author": "Steve Jobs"},
        {"text": "Life is what happens when you're busy making other plans.", "author": "John Lennon"},
        {"text": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt"},
    ]
    
    def get_tools(self) -> Dict[str, Callable]:
        return {
            "daily_quote": self.daily_quote,
            "quote_by_author": self.quote_by_author
        }
    
    def daily_quote(self) -> Dict:
        """
        Get a random inspirational quote
        
        Returns:
            Quote with author
        """
        quote = random.choice(self.QUOTES)
        
        return {
            "success": True,
            "quote": quote["text"],
            "author": quote["author"]
        }
    
    def quote_by_author(self, author: str) -> Dict:
        """
        Get quote by specific author
        
        Args:
            author: Author name
            
        Returns:
            Quote if found
        """
        matches = [q for q in self.QUOTES if author.lower() in q["author"].lower()]
        
        if matches:
            quote = random.choice(matches)
            return {
                "success": True,
                "quote": quote["text"],
                "author": quote["author"]
            }
        else:
            return {
                "success": False,
                "error": f"No quotes found for: {author}"
            }
    
    def get_system_prompt_addition(self) -> str:
        return """**Quote Plugin:**

- `quote.daily_quote()` - Get random inspirational quote
- `quote.quote_by_author(author)` - Get quote by specific author

Examples:
- "Give me a quote"
- "Daily quote"
- "Quote by Steve Jobs"
"""
    
    def cleanup(self):
        logger.info("Quote plugin cleanup")
```

### Intermediate: News Headlines

```python
"""
News Plugin
Fetches latest news headlines
"""

import logging
import requests
from typing import Dict, Callable
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.plugin_system import JARVISPlugin

logger = logging.getLogger(__name__)


class NewsPlugin(JARVISPlugin):
    name = "news"
    version = "1.0.0"
    description = "Fetches latest news headlines"
    author = "JARVIS Team"
    required_packages = ["requests"]
    
    def initialize(self) -> bool:
        try:
            self.api_url = "https://newsapi.org/v2/top-headlines"
            self.country = "us"
            
            logger.info("News plugin initialized")
            return True
        except Exception as e:
            logger.error(f"News plugin init failed: {str(e)}")
            return False
    
    def get_tools(self) -> Dict[str, Callable]:
        return {
            "headlines": self.get_headlines,
            "search_news": self.search_news
        }
    
    def get_headlines(self, category: str = "general", count: int = 5) -> Dict:
        """
        Get top news headlines
        
        Args:
            category: News category (general, business, tech, etc.)
            count: Number of headlines (default: 5)
            
        Returns:
            List of headlines
        """
        try:
            params = {
                "country": self.country,
                "category": category,
                "pageSize": count
            }
            
            # Note: In production, add API key
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get("articles", [])
            
            headlines = []
            for article in articles[:count]:
                headlines.append({
                    "title": article.get("title", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "url": article.get("url", "")
                })
            
            return {
                "success": True,
                "headlines": headlines,
                "category": category
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to fetch news: {str(e)}"
            }
    
    def search_news(self, query: str, count: int = 5) -> Dict:
        """
        Search news by query
        
        Args:
            query: Search query
            count: Number of results
            
        Returns:
            Search results
        """
        try:
            params = {
                "q": query,
                "pageSize": count,
                "sortBy": "publishedAt"
            }
            
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            articles = data.get("articles", [])
            
            results = []
            for article in articles[:count]:
                results.append({
                    "title": article.get("title", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "published": article.get("publishedAt", ""),
                    "url": article.get("url", "")
                })
            
            return {
                "success": True,
                "results": results,
                "query": query
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"News search failed: {str(e)}"
            }
    
    def get_system_prompt_addition(self) -> str:
        return """**News Plugin:**

- `news.headlines(category, count)` - Get top headlines
  - category: general, business, tech, sports, etc.
  - count: Number of headlines (default: 5)
- `news.search_news(query, count)` - Search news
  - query: Search term
  - count: Number of results (default: 5)

Examples:
- "What's the news?"
- "Get tech headlines"
- "Search news about AI"
- "Latest business news"
"""
    
    def cleanup(self):
        logger.info("News plugin cleanup")
```

---

## Testing & Debugging

### Manual Testing

```bash
# 1. Restart JARVIS to load new plugin
python jarvis.py

# 2. Check if plugin loaded
You: plugins
JARVIS: Should list your plugin

# 3. Test each tool
You: [Use your plugin's natural language commands]

# 4. Check logs
tail -f ~/jarvis/logs/audit.log
```

### Unit Testing

Create `tests/test_my_plugin.py`:

```python
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from plugins.my_plugin import MyPlugin


class TestMyPlugin(unittest.TestCase):
    
    def setUp(self):
        self.plugin = MyPlugin()
        self.plugin.initialize()
    
    def test_greet(self):
        result = self.plugin.greet("Test")
        self.assertTrue(result["success"])
        self.assertIn("Test", result["message"])
    
    def test_hello(self):
        result = self.plugin.hello()
        self.assertTrue(result["success"])
        self.assertIn("Hello", result["message"])
    
    def tearDown(self):
        self.plugin.cleanup()


if __name__ == "__main__":
    unittest.main()
```

Run tests:
```bash
python -m pytest tests/test_my_plugin.py -v
```

### Debug Mode

Add debug logging to your plugin:

```python
def my_tool(self, param: str) -> Dict:
    logger.debug(f"my_tool called with: {param}")
    
    try:
        # Your logic
        logger.debug(f"Processing...")
        
        result = do_something(param)
        logger.debug(f"Result: {result}")
        
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}
```

Enable debug logging in JARVIS:
```python
# In jarvis.py, change logging level
logging.basicConfig(level=logging.DEBUG, ...)
```

---

## Publishing Plugins

### Prepare for Publishing

1. **Add Metadata:**
```python
name = "my_awesome_plugin"
version = "1.0.0"
description = "Does awesome things"
author = "Your Name"
author_email = "your@email.com"
license = "MIT"
repository = "https://github.com/yourusername/jarvis-my-plugin"
```

2. **Create README:**
```markdown
# My Awesome Plugin

## Features
- Feature 1
- Feature 2

## Installation
1. Copy to ~/jarvis/plugins/
2. Install dependencies: pip install -r requirements.txt
3. Configure: Create config file

## Usage
Examples of how to use...

## Configuration
Config options...

## License
MIT License
```

3. **Create requirements.txt:**
```
requests>=2.28.0
aiohttp>=3.8.0
```

### Share Your Plugin

**Option 1: GitHub**
```bash
# Create repository
mkdir jarvis-my-plugin
cd jarvis-my-plugin
git init

# Add your plugin
cp ~/jarvis/plugins/my_plugin.py .
cp README.md .
cp requirements.txt .

# Commit and push
git add .
git commit -m "Initial release"
git remote add origin https://github.com/yourusername/jarvis-my-plugin.git
git push -u origin main
```

**Option 2: JARVIS Plugin Registry** (Future)
```bash
# Submit to central registry
jarvis plugin publish my_plugin.py
```

### Installation Instructions for Users

```markdown
## Installation

1. Download plugin:
   ```bash
   cd ~/jarvis/plugins
   wget https://github.com/yourusername/jarvis-my-plugin/raw/main/my_plugin.py
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure:
   ```bash
   python my_plugin.py  # Creates config template
   # Edit ~/jarvis/config/my_plugin_config.json
   ```

4. Restart JARVIS:
   ```bash
   python jarvis.py
   ```

5. Verify:
   ```
   You: plugins
   JARVIS: Should list my_plugin
   ```
```

---

## Troubleshooting

### Plugin Not Loading

**Problem:** Plugin doesn't appear in `plugins` list

**Solutions:**
1. Check file location: `ls ~/jarvis/plugins/my_plugin.py`
2. Check class name: Must inherit from `JARVISPlugin`
3. Check for syntax errors: `python -m py_compile my_plugin.py`
4. Check logs: `tail -f ~/jarvis/logs/audit.log`

### Tool Not Executing

**Problem:** LLM doesn't use your tool

**Solutions:**
1. Improve system prompt - be more specific
2. Add more examples
3. Check tool is in `get_tools()` return
4. Test with explicit command: "Use my_plugin.tool_name"

### Import Errors

**Problem:** `ModuleNotFoundError`

**Solutions:**
1. Install dependencies: `pip install -r requirements.txt`
2. Check `required_packages` list
3. Verify virtual environment is activated

### Configuration Issues

**Problem:** Plugin can't find config

**Solutions:**
1. Create config manually
2. Use plugin's config template: `python my_plugin.py`
3. Check file permissions: `chmod 644 config.json`

---

## API Reference

### JARVISPlugin Base Class

#### Required Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | str | Plugin identifier (lowercase, no spaces) |
| `version` | str | Semantic version (e.g., "1.0.0") |
| `description` | str | Brief description |
| `author` | str | Your name |
| `required_packages` | List[str] | Python package dependencies |

#### Required Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `get_tools()` | Dict[str, Callable] | Return tool functions |
| `get_system_prompt_addition()` | str | Add to system prompt |
| `cleanup()` | None | Cleanup on shutdown |

#### Optional Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `check_dependencies()` | bool | Custom dependency check |
| `initialize()` | bool | Setup after instantiation |

### Tool Function Signature

```python
def my_tool(self, param1: type, param2: type = default) -> Dict:
    """
    Tool description (used by LLM)
    
    Args:
        param1: Description
        param2: Description (optional)
    
    Returns:
        {
            "success": bool,
            "message": str (optional),
            "data": any (optional),
            "error": str (if success=False)
        }
    """
```

### Return Value Format

**Success:**
```python
{
    "success": True,
    "message": "Operation completed",
    "data": {...}  # Optional
}
```

**Error:**
```python
{
    "success": False,
    "error": "Error description"
}
```

---

## Quick Reference

### Plugin Checklist

- [ ] Inherits from `JARVISPlugin`
- [ ] Has all required metadata (name, version, etc.)
- [ ] Implements `get_tools()`
- [ ] Implements `get_system_prompt_addition()`
- [ ] Implements `cleanup()`
- [ ] Error handling in all tools
- [ ] Logging added
- [ ] Configuration handled
- [ ] Dependencies listed
- [ ] Tested with JARVIS

### Common Patterns

**API Call:**
```python
import requests

def api_tool(self, endpoint: str) -> Dict:
    try:
        response = requests.get(f"{self.base_url}/{endpoint}")
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**File Operation:**
```python
from pathlib import Path

def file_tool(self, filename: str) -> Dict:
    try:
        path = Path.home() / "jarvis" / "data" / filename
        content = path.read_text()
        return {"success": True, "content": content}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Database Query:**
```python
def db_tool(self, query: str) -> Dict:
    try:
        cursor = self.conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## Resources

- **JARVIS Core:** `~/jarvis/modules/plugin_system.py`
- **Example Plugins:** `~/jarvis/plugins/`
- **Logs:** `~/jarvis/logs/audit.log`
- **Config:** `~/jarvis/config/`

---

**Happy Plugin Development! 🚀**

For questions or support, check the JARVIS documentation or community forums.
