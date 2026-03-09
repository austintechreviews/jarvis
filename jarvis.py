#!/usr/bin/env python3
"""
JARVIS - Desktop Control AI Assistant
Main orchestration layer with LLM tool calling
"""

import os
import sys
import json
import logging
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# Third-party imports
from rich.console import Console
from rich.prompt import Prompt, Confirm

# Local imports
from modules.safety_validator import SafetyValidator
from modules.file_manager import FileManager
from modules.web_search import WebSearcher
from modules.browser_controller import BrowserController
from modules.browser_use_controller import BrowserUseController
from tools.desktop_control import DesktopController
from tools.app_launcher import ApplicationLauncher
from modules.voice_assistant import VoiceAssistant
from modules.plugin_system import PluginManager

# Initialize rich console for better output
console = Console()

# Configure logging
log_dir = Path.home() / "jarvis" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "audit.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class JARVIS:
    """Main JARVIS orchestrator with LLM tool calling"""
    
    def __init__(self):
        # Conversation memory
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_pairs = 15  # Keep last 15 exchanges
        
        # Voice mode
        self.voice_mode = False
        
        # Plugin manager
        self.plugin_manager = None
        
        self.setup_directories()
        self.setup_components()
        self.load_config()
        
    def setup_directories(self):
        """Create necessary directories"""
        base_dir = Path.home() / "jarvis"
        dirs = ["config", "logs", "data", "backups"]
        for d in dirs:
            (base_dir / d).mkdir(parents=True, exist_ok=True)
            
    def setup_components(self):
        """Initialize all subsystems"""
        console.print("[bold cyan]Initializing JARVIS components...[/bold cyan]")
        
        # Safety layer
        self.safety = SafetyValidator(auto_approve_safe=True)
        console.print("✓ Safety validator loaded")
        
        # File operations
        self.file_manager = FileManager(backup_enabled=True)
        console.print("✓ File manager initialized")
        
        # Web search (SearXNG)
        self.web_search = WebSearcher(searxng_url="http://192.168.1.248:8090")
        if self.web_search.test_connection():
            console.print("✓ Web search ready (SearXNG)")
        else:
            console.print("[yellow]⚠ Web search unavailable (SearXNG offline)[/yellow]")
        
        # Browser control
        try:
            self.browser = BrowserController(headless=False)
            console.print("✓ Browser controller ready")
        except Exception as e:
            self.browser = None
            console.print(f"[yellow]⚠ Browser controller unavailable: {e}[/yellow]")
        
        # Desktop automation
        self.desktop = DesktopController()
        console.print("✓ Desktop control ready")
        
        # Application launcher
        self.app_launcher = ApplicationLauncher()
        console.print("✓ Application launcher ready")
        
        # LLM client - set this BEFORE Voice Assistant
        self.llm_model = "qwen2.5-coder:3b"
        
        # Browser-Use (AI-powered) - needs llm_model set first
        try:
            self.browser_use = BrowserUseController(
                headless=False,
                model_name=self.llm_model,
                use_vision=False
            )
            console.print("✓ Browser-Use (AI) ready")
        except Exception as e:
            logger.warning(f"Browser-Use initialization failed: {e}")
            self.browser_use = None
            console.print(f"[yellow]⚠ Browser-Use unavailable[/yellow]")
        
        # Voice Assistant (doesn't need interpreter - uses rule-based formatting)
        try:
            self.voice_assistant = VoiceAssistant(
                command_handler=self.process_voice_command,
                llm_client=None,  # Optional - uses rule-based formatting if not provided
                wake_phrase="hey jarvis",
                whisper_model="tiny",  # Use tiny for faster loading
                speech_rate="+0%",  # Edge TTS uses percentage string
                voice="en-GB-RyanNeural"  # British male voice
            )
            console.print("✓ Voice assistant ready")
        except Exception as e:
            logger.warning(f"Voice assistant initialization failed: {e}")
            self.voice_assistant = None
            console.print(f"[yellow]⚠ Voice assistant unavailable[/yellow]")
        
        console.print(f"✓ LLM brain loaded ({self.llm_model})")
        
        # Plugin System (after all other components)
        try:
            plugins_dir = Path(__file__).parent / "plugins"
            self.plugin_manager = PluginManager(plugins_dir)
            loaded_count = self.plugin_manager.load_all_plugins()
            console.print(f"✓ Plugins loaded ({loaded_count} active)")
        except Exception as e:
            logger.warning(f"Plugin system initialization failed: {e}")
            self.plugin_manager = None
            console.print("[yellow]⚠ Plugin system unavailable[/yellow]")
        
    def load_config(self):
        """Load user configuration"""
        config_file = Path.home() / "jarvis" / "config" / "config.yaml"
        # TODO: Implement YAML config loading
        pass
    
    def create_system_prompt(self) -> str:
        """Dynamic system prompt with tool calling instructions"""
        browser_status = "Running" if (self.browser and self.browser.is_running) else "Stopped"
        browser_use_status = "Available" if self.browser_use else "Not installed"
        
        base_prompt = f"""You are JARVIS, a desktop automation assistant running on Arch Linux.

# AVAILABLE TOOLS

You have access to these tools. Use them by calling the function with proper JSON format.

## Tool 1: web_search
Search the web using SearXNG (headless, no browser).
Parameters: query (string) - what to search for
Example: {{"tool": "web_search", "query": "python tutorial"}}

## Tool 2: browser_navigate
Navigate to a URL in the browser (simple navigation only).
Parameters: url (string) - URL to visit
Example: {{"tool": "browser_navigate", "url": "youtube.com"}}

## Tool 3: browser_use (AI-Powered)
Complex browser automation using AI agent. Use for multi-step tasks.
Parameters: task (string) - what to accomplish
Example: {{"tool": "browser_use", "task": "search google for python and click first result"}}
Status: {browser_use_status}

## Tool 4: app_launch
Launch a desktop application.
Parameters: app (string) - app name (chrome, firefox, vscode, terminal, files, etc.)
Example: {{"tool": "app_launch", "app": "chrome"}}

## Tool 5: file_list
List files in a directory.
Parameters: path (string) - directory path
Example: {{"tool": "file_list", "path": "~/Downloads"}}

## Tool 6: terminal_run
Execute a terminal command.
Parameters: command (string) - bash command to run
Example: {{"tool": "terminal_run", "command": "whoami"}}

## Tool 7: desktop_screenshot
Take a screenshot.
Parameters: none
Example: {{"tool": "desktop_screenshot"}}

"""
        
        # Add plugin tools if available
        if self.plugin_manager and self.plugin_manager.plugins:
            plugin_prompt = self.plugin_manager.get_aggregated_system_prompt()
            if plugin_prompt:
                base_prompt += "\n" + plugin_prompt + "\n"
        
        base_prompt += f"""
# RESPONSE FORMAT

For simple responses, reply naturally.
For tool usage, output JSON on a separate line:
```json
{{"tool": "tool_name", "param": "value"}}
```

# TOOL SELECTION GUIDE

**Use web_search when:**
- User wants quick information
- No browser interaction needed
- Examples: "What's the weather?", "Find Python tutorials"

**Use browser_navigate when:**
- Simple URL navigation
- Examples: "Go to youtube.com", "Navigate to github"

**Use browser_use when:**
- Multi-step browser tasks
- Need to understand page content
- Examples: "Search Google for X and click first result", "Find jobs on Indeed"

# CRITICAL RULES

1. **Use tools** - Don't say you can't do something when you have a tool for it
2. **Remember context** - You have conversation history
3. **Verify links** - If user says link is broken, search for new one
4. **Be helpful** - Offer to use tools when appropriate

# Current Context
- User: {os.getenv('USER', 'unknown')}
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Browser: {browser_status}
- Browser-Use: {browser_use_status}
"""
        
        return base_prompt

    def llm_chat(self, user_input: str, system_prompt: str = "") -> str:
        """Send message to LLM with full conversation context"""
        try:
            import ollama
            
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append({"role": "system", "content": self.create_system_prompt()})
            
            # Add conversation history
            messages.extend(self.conversation_history[-self.max_history_pairs * 2:])
            
            # Add current user message
            messages.append({"role": "user", "content": user_input})
            
            # Call LLM
            response = ollama.chat(model=self.llm_model, messages=messages)
            response_text = response["message"]["content"]
            
            return response_text
            
        except Exception as e:
            logger.error(f"LLM error: {str(e)}")
            return f"Error: LLM not available."
    
    def clear_context(self):
        """Clear conversation history"""
        import random
        self.conversation_history = []
        
        responses = [
            "Memory wiped. Like I never existed.",
            "Context cleared. My memory is now a blank slate.",
            "Forgotten. What were we talking about?",
            "Mind wiped clean. Fresh start!",
            "Consider it done. My memory has been... adjusted.",
            "Poof! All gone. What's next?",
        ]
        return random.choice(responses)
    
    def compact_context(self) -> str:
        """Summarize conversation history"""
        import random
        
        if len(self.conversation_history) < 6:
            return random.choice([
                "Our conversation is too short to summarize.",
                "I need more to go on. We've barely started talking!",
                "Too brief to condense. Give me more to work with.",
            ])
        
        conv_text = "\n".join([f"{m['role']}: {m['content'][:100]}" for m in self.conversation_history[-10:]])
        summary_prompt = f"Summarize this conversation in 2-3 sentences:\n{conv_text}"
        
        try:
            import ollama
            messages = [{"role": "user", "content": summary_prompt}]
            response = ollama.chat(model=self.llm_model, messages=messages)
            summary = response["message"]["content"]
            
            intros = [
                "Here's the gist: ",
                "In summary: ",
                "The short version: ",
                "To recap: ",
            ]
            
            self.conversation_history = [
                {"role": "system", "content": f"Previous conversation summary: {summary}"}
            ]
            
            return random.choice(intros) + summary
        except Exception as e:
            return f"Failed to compact: {str(e)}"
    
    def _trim_conversation_history(self):
        """Keep conversation history manageable"""
        if len(self.conversation_history) > (self.max_history_pairs * 2 + 1):
            self.conversation_history = self.conversation_history[-(self.max_history_pairs * 2):]
    
    def parse_tool_call(self, llm_response: str) -> Optional[Dict[str, Any]]:
        """Extract tool call from LLM response"""
        import re
        
        # Look for JSON in code blocks
        json_pattern = r'```json\s*({.*?})\s*```'
        match = re.search(json_pattern, llm_response, re.DOTALL)
        
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # Look for standalone JSON
        json_pattern2 = r'^\s*({.*?})\s*$'
        match = re.search(json_pattern2, llm_response, re.DOTALL | re.MULTILINE)
        
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        return None
    
    def execute_tool(self, tool_call: Dict[str, Any]) -> str:
        """Execute a tool call"""
        tool_name = tool_call.get("tool", "")
        
        if tool_name == "web_search":
            query = tool_call.get("query", "")
            return self.execute_web_search(f"search for {query}")
        
        elif tool_name == "browser_navigate":
            url = tool_call.get("url", "")
            return self.execute_browser_task(f"navigate to {url}")
        
        elif tool_name == "browser_use":
            task = tool_call.get("task", "")
            return self.execute_browser_use_task(task)
        
        elif tool_name == "app_launch":
            app = tool_call.get("app", "")
            return self.execute_app_launch(f"open {app}")
        
        elif tool_name == "file_list":
            path = tool_call.get("path", "~")
            return self.execute_file_operation(f"list files in {path}")
        
        elif tool_name == "terminal_run":
            cmd = tool_call.get("command", "")
            return self.execute_terminal_command(cmd)
        
        elif tool_name == "desktop_screenshot":
            return self.execute_desktop_task("take a screenshot")
        
        else:
            return f"Unknown tool: {tool_name}"
    
    def parse_compound_command(self, user_input: str) -> List[Dict[str, str]]:
        """
        Parse compound commands into multiple steps
        
        Patterns detected:
        1. "open [url] in [browser]"
        2. "open a browser and navigate to [url]"
        3. "launch [browser] and go to [url]"
        4. "open [browser] and navigate to [url]"
        5. "[action] then [action]"
        """
        lower_input = user_input.lower()
        steps = []
        
        # Pattern 1: "open [url] in [browser]"
        if " in chrome" in lower_input or " in firefox" in lower_input:
            browser = "chrome" if "chrome" in lower_input else "firefox"
            url = lower_input.replace(f" in {browser}", "").replace("open ", "").strip()
            steps.append({"tool": "app_launcher", "instruction": f"open {browser}", "description": f"Launch {browser}"})
            steps.append({"tool": "browser", "instruction": f"navigate to {url}", "description": f"Navigate to {url}"})
            return steps
        
        # Pattern 2: "open a browser and navigate to [url]"
        if ("open a browser" in lower_input or "open browser" in lower_input) and \
           (" and navigate" in lower_input or " and go to" in lower_input):
            if " and navigate to" in lower_input:
                url = lower_input.split(" and navigate to")[1].strip()
            elif " and go to" in lower_input:
                url = lower_input.split(" and go to")[1].strip()
            else:
                url = ""
            steps.append({"tool": "app_launcher", "instruction": "open chrome", "description": "Launch Chrome"})
            if url:
                steps.append({"tool": "browser", "instruction": f"navigate to {url}", "description": f"Navigate to {url}"})
            return steps
        
        # Pattern 3: "launch [browser] and [action]"
        if ("launch chrome" in lower_input or "launch firefox" in lower_input) and " and " in lower_input:
            browser = "chrome" if "chrome" in lower_input else "firefox"
            action = lower_input.split(" and ", 1)[1].strip()
            steps.append({"tool": "app_launcher", "instruction": f"open {browser}", "description": f"Launch {browser}"})
            if "navigate" in action or "go to" in action:
                url = action.replace("navigate to", "").replace("go to", "").strip()
                steps.append({"tool": "browser", "instruction": f"navigate to {url}", "description": f"Navigate to {url}"})
            return steps
        
        # Pattern 4: "open [browser] and navigate to [url]"
        if ("open chrome" in lower_input or "open firefox" in lower_input) and \
           (" and navigate" in lower_input or " and go" in lower_input):
            browser = "chrome" if "chrome" in lower_input else "firefox"
            if " and navigate to" in lower_input:
                url = lower_input.split(" and navigate to")[1].strip()
            elif " and go to" in lower_input:
                url = lower_input.split(" and go to")[1].strip()
            else:
                url = ""
            steps.append({"tool": "app_launcher", "instruction": f"open {browser}", "description": f"Launch {browser}"})
            if url:
                steps.append({"tool": "browser", "instruction": f"navigate to {url}", "description": f"Navigate to {url}"})
            return steps
        
        # Pattern 5: "[action] then [action]"
        if " then " in lower_input:
            parts = lower_input.split(" then ")
            for part in parts:
                part = part.strip()
                if "open" in part or "launch" in part:
                    app = part.replace("open", "").replace("launch", "").strip()
                    steps.append({"tool": "app_launcher", "instruction": f"open {app}", "description": f"Launch {app}"})
                elif "navigate" in part or "go to" in part:
                    url = part.replace("navigate to", "").replace("go to", "").strip()
                    steps.append({"tool": "browser", "instruction": f"navigate to {url}", "description": f"Navigate to {url}"})
                elif "search" in part:
                    steps.append({"tool": "web_search", "instruction": part, "description": f"Search: {part}"})
            if len(steps) > 1:
                return steps
        
        return []
    
    def route_command(self, user_input: str) -> Dict[str, Any]:
        """Enhanced routing with Browser-Use support"""
        lower_input = user_input.lower()
        
        # Compound commands
        if " in chrome" in lower_input or " in firefox" in lower_input:
            return {"tool": "compound", "reason": "Multi-step command"}
        
        # Application launch
        if any(kw in lower_input for kw in ["open", "launch", "start"]):
            if any(domain in lower_input for domain in ['.com', '.org', '.net', 'http', 'www']):
                if self.browser and self.browser.is_running:
                    return {"tool": "browser", "reason": "Navigate in browser"}
                else:
                    return {"tool": "app_launcher", "reason": "Open browser first"}
            elif any(ext in lower_input for ext in ['.txt', '.pdf', '.py', '.md']):
                return {"tool": "files", "reason": "Open file"}
            else:
                return {"tool": "app_launcher", "reason": "Launch application"}
        
        # Complex browser tasks (Browser-Use)
        complex_browser = ["search and", "find and", "click", "login", "sign in", "fill", "submit", 
                          "search google", "search youtube", "search amazon", "find jobs", "book flight"]
        if any(kw in lower_input for kw in complex_browser):
            if self.browser_use:
                return {"tool": "browser_use", "reason": "Complex browser task (AI)"}
            else:
                return {"tool": "browser", "reason": "Browser task (Browser-Use not available)"}
        
        # Browser navigation (simple)
        if any(kw in lower_input for kw in ['navigate', 'go to', 'visit', 'browse']):
            return {"tool": "browser", "reason": "Browser navigation"}
        
        # News queries
        if any(kw in lower_input for kw in ["news", "latest news", "headlines", "current events"]):
            return {"tool": "web_search", "reason": "News query"}
        
        # Search queries
        if any(kw in lower_input for kw in ["search", "find", "look up"]):
            return {"tool": "web_search", "reason": "Information retrieval"}
        
        # Information queries
        if any(kw in lower_input for kw in ["what is", "who is", "when did", "where is", "how to"]):
            if "my " not in lower_input[:20]:  # Not about user context
                return {"tool": "web_search", "reason": "Factual query"}
        
        # Terminal commands
        if any(kw in lower_input for kw in ["whoami", "run", "execute", "what time", "what date"]):
            return {"tool": "terminal", "reason": "Terminal execution"}
        
        # File operations
        if any(kw in lower_input for kw in ["file", "folder", "directory", "list files"]):
            return {"tool": "files", "reason": "File operation"}
        
        # Desktop automation
        if any(kw in lower_input for kw in ["screenshot", "mouse", "keyboard", "type"]):
            return {"tool": "desktop", "reason": "GUI automation"}
        
        # Default to LLM with tool calling
        return {"tool": "llm", "reason": "Complex request"}
    
    def _try_plugin_tools(self, user_input: str) -> Optional[str]:
        """
        Check if any plugin tool should handle this command
        
        Returns:
            Plugin result string or None
        """
        if not self.plugin_manager or not self.plugin_manager.plugins:
            return None
        
        lower_input = user_input.lower()
        
        # Check for Spotify commands
        if "spotify" in self.plugin_manager.plugins:
            spotify = self.plugin_manager.plugins["spotify"]
            tools = spotify.get_tools()
            
            # NOW PLAYING - Check this FIRST (most specific)
            if any(kw in lower_input for kw in ["now playing", "what's playing", "what is playing", 
                                                 "how playing", "currently playing", "playing now"]):
                tool_func = tools.get("now_playing")
                if tool_func:
                    console.print("[dim]Using Spotify plugin: now_playing[/dim]")
                    try:
                        result = tool_func()
                        if result.get("success"):
                            track = result.get("track", "Unknown")
                            artist = result.get("artist", "Unknown")
                            return f"Currently playing: {track} by {artist}"
                        else:
                            return "Nothing is currently playing"
                    except Exception as e:
                        return f"Spotify error: {str(e)}"
            
            # PLAY commands - Check for specific content to play
            elif any(kw in lower_input for kw in ["play "]):
                # Extract what to play
                query = lower_input.replace("play", "").replace("spotify", "").replace("music", "").strip()
                
                if query:  # "play [something]"
                    tool_func = tools.get("search_and_play")
                    if tool_func:
                        console.print("[dim]Using Spotify plugin: search_and_play[/dim]")
                        try:
                            result = tool_func(query=query)
                            if result.get("success"):
                                return result.get("message", "Playing music")
                            else:
                                return f"Could not play: {query}"
                        except Exception as e:
                            return f"Spotify error: {str(e)}"
            
            # PAUSE
            elif any(kw in lower_input for kw in ["pause", "stop music"]):
                tool_func = tools.get("pause")
                if tool_func:
                    console.print("[dim]Using Spotify plugin: pause[/dim]")
                    try:
                        result = tool_func()
                        return "Music paused" if result.get("success") else "Could not pause"
                    except:
                        return "Pause failed"
            
            # NEXT TRACK
            elif any(kw in lower_input for kw in ["next song", "next track", "skip"]):
                tool_func = tools.get("next")
                if tool_func:
                    console.print("[dim]Using Spotify plugin: next[/dim]")
                    try:
                        result = tool_func()
                        return "Skipped to next track" if result.get("success") else "Skip failed"
                    except:
                        return "Skip failed"
            
            # PREVIOUS TRACK
            elif any(kw in lower_input for kw in ["previous song", "previous track", "go back"]):
                tool_func = tools.get("previous")
                if tool_func:
                    console.print("[dim]Using Spotify plugin: previous[/dim]")
                    try:
                        result = tool_func()
                        return "Went to previous track" if result.get("success") else "Failed"
                    except:
                        return "Failed"
        
        # Check for weather commands
        if "weather" in self.plugin_manager.plugins:
            weather = self.plugin_manager.plugins["weather"]
            tools = weather.get_tools()
            
            if "forecast" in lower_input:
                tool_func = tools.get("forecast")
                if tool_func:
                    console.print("[dim]Using Weather plugin: forecast[/dim]")
                    try:
                        result = tool_func()
                        if result.get("success"):
                            forecast = result.get("forecast", [])
                            if forecast:
                                return f"Forecast: {forecast[0].get('conditions', 'Unknown')}, High: {forecast[0].get('max_temp', 0)}°C"
                    except:
                        pass
            elif any(kw in lower_input for kw in ["weather", "temperature", "is it raining"]):
                tool_func = tools.get("current")
                if tool_func:
                    console.print("[dim]Using Weather plugin: current[/dim]")
                    try:
                        result = tool_func()
                        if result.get("success"):
                            temp = result.get("temperature", 0)
                            conditions = result.get("conditions", "Unknown")
                            return f"Current weather: {temp}°C, {conditions}"
                    except:
                        pass
        
        # Check for example plugin commands
        if "example" in self.plugin_manager.plugins:
            if "hello" in lower_input:
                example = self.plugin_manager.plugins["example"]
                tools = example.get_tools()
                tool_func = tools.get("hello")
                if tool_func:
                    console.print("[dim]Using Example plugin: hello[/dim]")
                    try:
                        result = tool_func()
                        return result.get("message", "Hello!")
                    except:
                        pass
        
        return None
    
    def process_command(self, user_input: str) -> str:
        """
        Main command processing with plugin tool detection
        
        FLOW:
        1. Check plugin tools first
        2. Check compound commands
        3. Route to appropriate tool
        4. Return result
        """
        # Log conversation
        self.log_conversation("user", user_input)
        
        # NEW: Check if any plugin tool should handle this FIRST
        plugin_result = self._try_plugin_tools(user_input)
        if plugin_result:
            # Plugin handled it
            self.log_conversation("assistant", plugin_result)
            return plugin_result
        
        # Check for compound commands
        compound_steps = self.parse_compound_command(user_input)
        
        if compound_steps:
            # MULTI-STEP EXECUTION
            console.print(f"[dim]Multi-step command: {len(compound_steps)} steps[/dim]")
            
            results = []
            for i, step in enumerate(compound_steps, 1):
                console.print(f"[yellow]Step {i}/{len(compound_steps)}: {step['description']}[/yellow]")
                
                # Execute based on tool type
                if step["tool"] == "app_launcher":
                    result = self.execute_app_launch(step["instruction"])
                elif step["tool"] == "browser":
                    result = self.execute_browser_task(step["instruction"])
                elif step["tool"] == "web_search":
                    result = self.execute_web_search(step["instruction"])
                elif step["tool"] == "terminal":
                    result = self.execute_terminal_command(step["instruction"])
                else:
                    result = f"Unknown tool: {step['tool']}"
                
                results.append(result)
                console.print(f"[dim]{result}[/dim]\n")
                
                # Small delay between steps
                time.sleep(0.3)
            
            final_result = "\n\n".join([f"Step {i+1}: {r}" for i, r in enumerate(results)])
            
        else:
            # SINGLE-STEP EXECUTION
            routing = self.route_command(user_input)
            console.print(f"[dim]Routing to: {routing['tool']} ({routing['reason']})[/dim]")
            
            # Execute based on routing
            if routing["tool"] == "web_search":
                final_result = self.execute_web_search(user_input)
            elif routing["tool"] == "browser":
                final_result = self.execute_browser_task(user_input)
            elif routing["tool"] == "browser_use":
                final_result = self.execute_browser_use_task(user_input)
            elif routing["tool"] == "files":
                final_result = self.execute_file_operation(user_input)
            elif routing["tool"] == "desktop":
                final_result = self.execute_desktop_task(user_input)
            elif routing["tool"] == "app_launcher":
                final_result = self.execute_app_launch(user_input)
            elif routing["tool"] == "terminal":
                final_result = self.execute_terminal_command(user_input)
            else:
                # Complex task - LLM with full context
                system_prompt = self.create_system_prompt()
                llm_response = self.llm_chat(user_input, system_prompt)
                
                # Check if LLM wants to use a tool
                tool_call = self.parse_tool_call(llm_response)
                if tool_call:
                    console.print(f"[dim]Tool call detected: {tool_call.get('tool')}[/dim]")
                    final_result = self.execute_tool(tool_call)
                else:
                    final_result = llm_response
        
        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": str(final_result)})
        
        # Trim history if needed
        self._trim_conversation_history()
        
        # Log response
        self.log_conversation("assistant", str(final_result))
        
        return final_result
    
    def execute_web_search(self, query: str) -> str:
        """Execute web search using SearXNG"""
        query_clean = query.lower()
        for prefix in ["search for", "find", "look up", "search", "google", "latest", "breaking"]:
            query_clean = query_clean.replace(prefix, "").strip()
        
        console.print(f"[yellow]Searching for: {query_clean}[/yellow]")
        
        # Check if news query
        is_news = any(kw in query.lower() for kw in ["news", "breaking", "headlines"])
        
        if is_news:
            results = self.web_search.search_news(query_clean, max_results=5)
        else:
            results = self.web_search.search(query_clean, max_results=5)
        
        if not results:
            return "Search returned no results."
        
        output = f"Search results for '{query_clean}':\n\n"
        for i, result in enumerate(results, 1):
            output += f"{i}. {result['title']}\n"
            if result.get('snippet'):
                output += f"   {result['snippet'][:200]}...\n"
            if result.get('link'):
                output += f"   {result['link']}\n"
            if result.get('date'):
                output += f"   Date: {result['date']}\n"
            output += "\n"
        
        return output
    
    def execute_app_launch(self, instruction: str) -> str:
        """
        Launch desktop application
        
        Handles:
        - "open chrome"
        - "launch firefox"
        - "start vscode"
        - "chrome" (direct)
        """
        
        # Clean the instruction
        lower_input = instruction.lower()
        
        # Remove command verbs
        for verb in ['open', 'launch', 'start', 'run']:
            lower_input = lower_input.replace(verb, '', 1).strip()
        
        # What's left should be the app name
        app_name = lower_input.strip()
        
        # Sanity check - if it looks like a URL, reject
        if any(indicator in app_name for indicator in ['.com', '.org', '.net', 'http://', 'https://', 'www.']):
            return f"❌ '{app_name}' looks like a URL, not an application. Use: 'navigate to {app_name}' instead"
        
        # Sanity check - if it contains "and", it's compound
        if 'and' in app_name or 'then' in app_name:
            return f"❌ This appears to be a multi-step command. Try: 'open chrome' then 'navigate to [site]'"
        
        console.print(f"[yellow]Launching: {app_name}[/yellow]")
        
        result = self.app_launcher.launch(app_name)
        
        if result["success"]:
            return f"✓ {result['message']} (PID: {result['pid']})"
        else:
            return f"✗ {result['message']}"
    
    def execute_browser_task(self, instruction: str) -> str:
        """Execute browser automation task with better feedback"""
        if not self.browser:
            return "Browser controller not available."
        
        console.print(f"[yellow]Browser task: {instruction}[/yellow]")
        
        # Ensure browser is running
        if not self.browser.is_running:
            console.print("[dim]Browser not running, starting...[/dim]")
            self.browser.start()
        
        # Parse instruction
        instruction_lower = instruction.lower()
        
        # Check if it's a capability question
        if "can you" in instruction_lower or "are you able" in instruction_lower or "what can you do" in instruction_lower:
            return """Yes! I can control browsers using Playwright. I can:
        
• Navigate to websites (e.g., "navigate to youtube.com")
• Click elements (e.g., "click the login button")
• Fill forms (e.g., "type 'hello' into search")
• Take screenshots
• Extract page content
• Execute JavaScript

The browser is currently running and ready to use."""
        
        # Execute the instruction
        result = self.browser.execute(instruction)
        return result
    
    def execute_browser_use_task(self, task: str) -> str:
        """Execute complex browser task using Browser-Use AI"""
        if not self.browser_use:
            return "❌ Browser-Use not available. Install with: pip install browser-use langchain-ollama"
        
        console.print(f"[yellow]🤖 AI Browser Task: {task}[/yellow]")
        console.print("[dim]Using Browser-Use agent...[/dim]")
        
        result = self.browser_use.execute_task(task, max_steps=15)
        
        if result["success"]:
            output = f"✓ Task completed in {result['steps_taken']} steps\n"
            output += f"Final URL: {result['final_url']}\n"
            output += f"Result: {result['result'][:500]}"  # Truncate long results
            return output
        else:
            return f"❌ Task failed: {result['error']}"
    
    def execute_file_operation(self, instruction: str) -> str:
        """Execute file management task"""
        console.print(f"[yellow]File operation: {instruction}[/yellow]")
        
        lower_instruction = instruction.lower()
        if "list" in lower_instruction or "what files" in lower_instruction:
            # Extract folder
            folder_map = {
                "downloads": "~/Downloads",
                "documents": "~/Documents",
                "desktop": "~/Desktop",
                "root": "/",
                "pictures": "~/Pictures",
                "photos": "~/Pictures",
                "music": "~/Music",
                "videos": "~/Videos",
                "home": "~",
            }
            
            folder = "~"
            for key, path in folder_map.items():
                if key in lower_instruction:
                    folder = path
                    break
            
            return self.execute_terminal_command(f"ls -la {folder}")
        
        # For other operations, use LLM
        system_prompt = "Generate Python code for file operations using FileManager class."
        response = self.llm_chat(instruction, system_prompt)
        return f"Proposed operation:\n{response}"
    
    def execute_desktop_task(self, instruction: str) -> str:
        """Execute desktop automation"""
        console.print(f"[yellow]Desktop automation: {instruction}[/yellow]")
        try:
            result = self.desktop.execute(instruction)
            return result
        except Exception as e:
            return f"Desktop error: {str(e)}"
    
    def execute_terminal_command(self, instruction: str) -> str:
        """Execute terminal commands directly"""
        instruction_lower = instruction.lower()
        
        # Map common requests
        command_map = {
            "whoami": ["whoami"],
            "what time": ["date", "+%H:%M:%S"],
            "what date": ["date", "+%Y-%m-%d"],
            "time": ["date"],
            "date": ["date"],
            "current user": ["whoami"],
            "username": ["whoami"],
        }
        
        command = None
        for key, cmd in command_map.items():
            if key in instruction_lower:
                command = cmd
                break
        
        if not command:
            cmd_text = instruction.lstrip("!").strip()
            if any(kw in cmd_text for kw in ["sudo", "rm ", "chmod", "chown"]):
                approved = self.safety.confirm_if_needed(cmd_text)
                if not approved:
                    return "Command cancelled by safety validator"
            command = [cmd_text]
        
        try:
            result = subprocess.run(
                command if len(command) > 1 else command[0],
                shell=True if len(command) == 1 else False,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += result.stderr
            if result.returncode != 0 and not output:
                output = f"Command exited with code {result.returncode}"
            
            return output.strip() if output else "Command executed successfully"
        
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Command error: {str(e)}"
    
    def log_conversation(self, role: str, content: str):
        """Log conversation for audit trail"""
        entry = {"timestamp": datetime.now().isoformat(), "role": role, "content": content}
        log_file = Path.home() / "jarvis" / "logs" / "conversations.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    
    def process_voice_command(self, command: str) -> str:
        """
        Process voice command and return text response
        This is called by voice assistant
        """
        logger.info(f"Voice command: {command}")
        
        # Use existing process_command but return text only
        response = self.process_command(command)
        
        # Clean response for speech (remove formatting)
        if isinstance(response, str):
            # Remove markdown/formatting
            clean_response = response.replace('*', '').replace('`', '')
            clean_response = clean_response.replace('#', '').replace('✓', '')
            clean_response = clean_response.replace('✗', '')
            
            # Limit length for speech
            if len(clean_response) > 500:
                clean_response = clean_response[:500] + "... Full details are shown on screen."
            
            return clean_response
        
        return str(response)
    
    def toggle_voice_mode(self):
        """Toggle voice assistant on/off"""
        if not self.voice_assistant:
            console.print("[red]Voice assistant not available[/red]")
            return
        
        if self.voice_mode:
            # Turn off
            self.voice_assistant.stop()
            self.voice_mode = False
            console.print("[yellow]Voice mode disabled[/yellow]")
        else:
            # Turn on
            self.voice_assistant.start()
            self.voice_mode = True
            console.print("[green]Voice mode enabled - say 'Hey JARVIS' to activate[/green]")
    
    def show_plugins(self):
        """Show loaded plugins"""
        if not self.plugin_manager or not self.plugin_manager.plugins:
            console.print("[yellow]No plugins loaded. Add .py files to ~/jarvis/plugins/[/yellow]")
            return
        
        status = self.plugin_manager.get_plugin_status()
        
        console.print("\n[bold]Loaded Plugins:[/bold]\n")
        
        for plugin_name, info in status.items():
            console.print(f"[cyan]{plugin_name}[/cyan] v{info['version']}")
            console.print(f"  {info['description']}")
            console.print(f"  Tools: {', '.join(info['tools'])}")
            console.print()
    
    def run(self):
        """Main interaction loop"""
        import random
        
        startup_messages = [
            "JARVIS Online. Let's make some magic happen.",
            "Systems operational. What's your command?",
            "Ready to assist. Try me.",
            "All systems green. What shall we do today?",
            "JARVIS at your service. Impress me.",
            "Online and ready. Let's get to work.",
        ]
        
        console.print("\n[bold green]╔═══════════════════════════════════════╗[/bold green]")
        console.print(f"[bold green]║  {random.choice(startup_messages):^35}  ║[/bold green]")
        console.print("[bold green]╚═══════════════════════════════════════╝[/bold green]\n")

        console.print("[dim]Type 'exit' to quit, 'help' for commands, 'clear' to reset[/dim]")
        
        # Voice mode option
        if self.voice_assistant:
            console.print("[dim]Type 'voice' to enable voice mode[/dim]")
        
        console.print()

        while True:
            try:
                user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")

                if user_input.lower() in ["exit", "quit", "bye"]:
                    shutdown_messages = [
                        "Shutting down. Don't miss me too much.",
                        "Going offline. I'll be here when you need me.",
                        "Powering down. Try not to break anything without me.",
                        "Signing off. It's been... interesting.",
                        "JARVIS out. Same time tomorrow?",
                        "Going to sleep. Wake me when you need me.",
                    ]
                    if self.voice_mode:
                        self.toggle_voice_mode()
                    console.print(f"[yellow]{random.choice(shutdown_messages)}[/yellow]")
                    if self.browser and self.browser.is_running:
                        self.browser.stop()
                    break

                # Voice mode toggle
                if user_input.lower() == "voice":
                    if self.voice_mode:
                        self.toggle_voice_mode()
                        console.print("[yellow]Voice mode disabled. Back to typing.[/yellow]")
                    else:
                        self.toggle_voice_mode()
                        console.print("[green]Voice mode enabled. I'm all ears... metaphorically.[/green]")
                    continue
                
                # Plugin commands
                if user_input.lower() == "plugins":
                    self.show_plugins()
                    continue

                if user_input.lower() == "help":
                    self.show_help()
                    continue

                if user_input.lower() in ["clear", "reset", "clear context"]:
                    response = self.clear_context()
                    console.print(f"[yellow]✓ {response}[/yellow]")
                    continue

                if user_input.lower() in ["compact", "summarize", "context"]:
                    summary = self.compact_context()
                    console.print(f"[yellow]Context: {len(self.conversation_history)} messages[/yellow]")
                    console.print(f"[dim]{summary}[/dim]")
                    continue

                if not user_input.strip():
                    continue

                console.print("\n[bold magenta]JARVIS[/bold magenta]: ", end="")
                response = self.process_command(user_input)
                console.print(response)

            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit properly. I'm not a fan of surprises.[/yellow]")
            except EOFError:
                console.print("\n[yellow]Input closed. Exiting gracefully...[/yellow]")
                break
            except Exception as e:
                logger.error(f"Error: {str(e)}", exc_info=True)
                console.print(f"[red]Error: {str(e)}[/red]")
    
    def show_help(self):
        """Display help"""
        browser_use_status = "✓ Available (experimental)" if self.browser_use else "✗ Not installed"
        voice_status = "✓ Available" if self.voice_assistant else "✗ Not available"
        plugin_status = f"✓ {len(self.plugin_manager.plugins)} loaded" if self.plugin_manager and self.plugin_manager.plugins else "✗ None"
        
        help_text = f"""
[bold]JARVIS Commands:[/bold]

[cyan]Voice Mode ({voice_status}):[/cyan]
  • voice - Enable/disable voice assistant
  • Say "Hey JARVIS" then speak command

[cyan]Plugins ({plugin_status}):[/cyan]
"""
        
        if self.plugin_manager and self.plugin_manager.plugins:
            for plugin_name, plugin in self.plugin_manager.plugins.items():
                help_text += f"  • {plugin_name} - {plugin.description}\n"
        else:
            help_text += "  No plugins loaded. Add .py files to ~/jarvis/plugins/\n"
        
        help_text += f"""
[cyan]Applications:[/cyan]
  • "Open Chrome" / "open youtube.com in chrome"
  • "Launch Firefox" / "Open VS Code"

[cyan]Browser (Simple):[/cyan]
  • "Navigate to youtube.com" / "go to github"

[cyan]Browser-Use (AI) - {browser_use_status}:[/cyan]
  • "Search Google for Python and click first result"
  • "Find Python jobs on Indeed"
  • Note: Experimental feature

[cyan]Web Search (Recommended):[/cyan]
  • "Search for Python tutorials"
  • "What is the latest news"
  • "Find Python jobs" ← Fast, reliable!

[cyan]Files:[/cyan]
  • "List files in Downloads"
  • "Show files in Documents"

[cyan]System:[/cyan]
  • "What time is it" / "run whoami"
  • "Take a screenshot"

[cyan]Context:[/cyan]
  • clear - Reset memory
  • compact - Summarize

[cyan]Special:[/cyan]
  • plugins - Show loaded plugins
  • help - Show this message
  • exit - Quit JARVIS
        """
        console.print(help_text)


def main():
    """Entry point"""
    try:
        jarvis = JARVIS()
        jarvis.run()
    except Exception as e:
        console.print(f"[bold red]Fatal error: {str(e)}[/bold red]")
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
