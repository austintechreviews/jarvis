"""
LLM-Powered Tool Router
Uses LLM to intelligently route commands to appropriate tools
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMToolRouter:
    """
    Intelligent tool routing using LLM reasoning
    
    Instead of keyword matching, the LLM:
    1. Sees all available tools
    2. Understands user intent
    3. Chooses the right tool
    4. Extracts parameters
    """
    
    def __init__(self, llm_client, plugin_manager=None):
        """
        Initialize LLM tool router
        
        Args:
            llm_client: LLM instance (e.g., interpreter)
            plugin_manager: Plugin manager for tool discovery
        """
        self.llm = llm_client
        self.plugin_manager = plugin_manager
        
        # Core tools (built-in JARVIS capabilities)
        self.core_tools = self._define_core_tools()
        
    def _define_core_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Define core JARVIS tools with schemas
        
        Returns:
            {
                "tool_name": {
                    "description": "What it does",
                    "parameters": {"param": "type"},
                    "examples": ["example usage"]
                }
            }
        """
        return {
            "web_search": {
                "description": "Search the web using SearXNG (headless)",
                "parameters": {
                    "query": "string - search query"
                },
                "examples": [
                    "search for Python tutorials",
                    "find news about AI"
                ]
            },
            "browser_navigate": {
                "description": "Navigate browser to a URL",
                "parameters": {
                    "url": "string - website URL"
                },
                "examples": [
                    "go to youtube.com",
                    "navigate to github"
                ]
            },
            "browser_use": {
                "description": "Complex browser automation with AI",
                "parameters": {
                    "task": "string - natural language task"
                },
                "examples": [
                    "search Google for cats and click first result",
                    "find cheap flights on Kayak"
                ]
            },
            "file_list": {
                "description": "List files in a directory",
                "parameters": {
                    "path": "string - directory path"
                },
                "examples": [
                    "list files in Documents",
                    "show my downloads"
                ]
            },
            "file_read": {
                "description": "Read contents of a file",
                "parameters": {
                    "path": "string - file path"
                },
                "examples": [
                    "read config.txt",
                    "show me the Python file"
                ]
            },
            "terminal": {
                "description": "Execute terminal command",
                "parameters": {
                    "command": "string - bash command"
                },
                "examples": [
                    "run whoami",
                    "check disk space"
                ]
            },
            "app_launch": {
                "description": "Launch desktop application",
                "parameters": {
                    "app_name": "string - application name"
                },
                "examples": [
                    "open chrome",
                    "launch vscode"
                ]
            }
        }
    
    def _get_plugin_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all plugin tools with schemas
        
        Returns:
            Dictionary of plugin tools
        """
        plugin_tools = {}
        
        if not self.plugin_manager:
            return plugin_tools
        
        for plugin_name, plugin in self.plugin_manager.plugins.items():
            tools = plugin.get_tools()
            
            for tool_name, tool_func in tools.items():
                full_name = f"{plugin_name}.{tool_name}"
                
                # Extract docstring
                doc = tool_func.__doc__ or "No description"
                
                # Extract parameters from function signature
                import inspect
                sig = inspect.signature(tool_func)
                params = {}
                for param_name, param in sig.parameters.items():
                    if param_name != 'self':
                        params[param_name] = str(param.annotation) if param.annotation != inspect.Parameter.empty else "any"
                
                plugin_tools[full_name] = {
                    "description": doc.split('\n')[0].strip(),
                    "parameters": params,
                    "plugin": plugin_name
                }
        
        return plugin_tools
    
    def route(self, user_input: str) -> Dict[str, Any]:
        """
        Route user command to appropriate tool using LLM
        
        Args:
            user_input: User's natural language command
            
        Returns:
            {
                "tool": "tool_name",
                "parameters": {"param": "value"},
                "reasoning": "why this tool was chosen"
            }
        """
        # Get all available tools
        all_tools = {**self.core_tools, **self._get_plugin_tools()}
        
        # Build tool catalog for LLM
        tool_catalog = self._build_tool_catalog(all_tools)
        
        # Create routing prompt
        prompt = f"""You are a tool router for JARVIS assistant. Given a user command, determine which tool to use.

# AVAILABLE TOOLS

{tool_catalog}

# USER COMMAND
"{user_input}"

# YOUR TASK
Analyze the command and respond with ONLY a JSON object (no markdown, no explanation):

{{
  "tool": "exact_tool_name",
  "parameters": {{"param_name": "value"}},
  "reasoning": "brief explanation"
}}

Rules:
- Choose the MOST SPECIFIC tool that matches the intent
- If multiple tools could work, prefer plugin tools over core tools
- Extract parameter values from the user command
- For Spotify: "play" = spotify.play(), "pause/stop" = spotify.pause(), "next" = spotify.next()
- For weather: any weather query = weather.current or weather.forecast
- If no tool matches, use "none"

JSON response:"""

        try:
            # Get LLM response
            response = self.llm.chat(prompt, display=False, stream=False)
            
            # Extract JSON from response
            routing = self._extract_json(response)
            
            if routing:
                logger.info(f"LLM routing: {routing['tool']} - {routing.get('reasoning', 'No reason')}")
                return routing
            else:
                logger.warning("LLM routing failed to parse JSON")
                return {"tool": "none", "parameters": {}, "reasoning": "Parse error"}
        
        except Exception as e:
            logger.error(f"LLM routing error: {str(e)}", exc_info=True)
            return {"tool": "none", "parameters": {}, "reasoning": f"Error: {str(e)}"}
    
    def _build_tool_catalog(self, tools: Dict[str, Dict[str, Any]]) -> str:
        """
        Build formatted tool catalog for LLM
        
        Args:
            tools: Dictionary of tools
            
        Returns:
            Formatted string catalog
        """
        catalog_parts = []
        
        # Group by category
        core = {k: v for k, v in tools.items() if '.' not in k}
        plugins = {k: v for k, v in tools.items() if '.' in k}
        
        # Core tools
        if core:
            catalog_parts.append("## Core Tools\n")
            for name, info in core.items():
                catalog_parts.append(f"**{name}**")
                catalog_parts.append(f"  Description: {info['description']}")
                if info.get('parameters'):
                    params = ", ".join(f"{k}: {v}" for k, v in info['parameters'].items())
                    catalog_parts.append(f"  Parameters: {params}")
                if info.get('examples'):
                    examples = ", ".join(f'"{ex}"' for ex in info['examples'][:2])
                    catalog_parts.append(f"  Examples: {examples}")
                catalog_parts.append("")
        
        # Plugin tools (grouped by plugin)
        if plugins:
            catalog_parts.append("## Plugin Tools\n")
            
            # Group by plugin
            by_plugin = {}
            for name, info in plugins.items():
                plugin = info.get('plugin', name.split('.')[0])
                if plugin not in by_plugin:
                    by_plugin[plugin] = []
                by_plugin[plugin].append((name, info))
            
            for plugin_name, plugin_tools in by_plugin.items():
                catalog_parts.append(f"### {plugin_name}")
                for name, info in plugin_tools:
                    catalog_parts.append(f"**{name}**")
                    catalog_parts.append(f"  {info['description']}")
                    if info.get('parameters'):
                        params = ", ".join(f"{k}: {v}" for k, v in info['parameters'].items())
                        catalog_parts.append(f"  Parameters: {params}")
                catalog_parts.append("")
        
        return "\n".join(catalog_parts)
    
    def _extract_json(self, response) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from LLM response
        
        Args:
            response: LLM response (might contain extra text)
            
        Returns:
            Parsed JSON or None
        """
        # Convert response to string if needed
        if isinstance(response, list):
            response = " ".join(str(chunk.get('content', '')) for chunk in response if isinstance(chunk, dict))
        
        response_str = str(response)
        
        # Try to find JSON object
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_str, re.DOTALL)
        
        if json_match:
            try:
                # Clean up common issues
                json_str = json_match.group()
                json_str = json_str.replace("'", '"')  # Single quotes to double
                
                # Parse JSON
                data = json.loads(json_str)
                
                # Validate structure
                if "tool" in data:
                    return data
            
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {str(e)}")
                logger.debug(f"Failed JSON: {json_str[:200]}")
        
        return None


class LLMToolExecutor:
    """
    Executes tools based on LLM routing decisions
    """
    
    def __init__(self, jarvis_instance):
        """
        Initialize executor
        
        Args:
            jarvis_instance: Reference to main JARVIS instance
        """
        self.jarvis = jarvis_instance
    
    def execute(self, routing: Dict[str, Any]) -> str:
        """
        Execute the routed tool
        
        Args:
            routing: Routing decision from LLMToolRouter
            
        Returns:
            Result string
        """
        tool_name = routing.get("tool")
        parameters = routing.get("parameters", {})
        
        if tool_name == "none":
            # No tool match - let LLM handle conversationally
            return self.jarvis.execute_with_llm(routing.get("original_command", ""))
        
        logger.info(f"Executing tool: {tool_name} with params: {parameters}")
        
        # Check if it's a plugin tool
        if '.' in tool_name:
            return self._execute_plugin_tool(tool_name, parameters)
        
        # Core tools
        if tool_name == "web_search":
            query = parameters.get("query", "")
            return self.jarvis.execute_web_search(query)
        
        elif tool_name == "browser_navigate":
            url = parameters.get("url", "")
            return self.jarvis.execute_browser_task(f"navigate to {url}")
        
        elif tool_name == "browser_use":
            task = parameters.get("task", "")
            return self.jarvis.execute_browser_use_task(task)
        
        elif tool_name == "file_list":
            path = parameters.get("path", "~")
            return self.jarvis.execute_file_operation(f"list files in {path}")
        
        elif tool_name == "file_read":
            path = parameters.get("path", "")
            return self.jarvis.execute_file_operation(f"read {path}")
        
        elif tool_name == "terminal":
            command = parameters.get("command", "")
            return self.jarvis.execute_terminal_command(command)
        
        elif tool_name == "app_launch":
            app = parameters.get("app_name", "")
            return self.jarvis.execute_app_launch(f"open {app}")
        
        else:
            return f"Unknown tool: {tool_name}"
    
    def _execute_plugin_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """
        Execute a plugin tool
        
        Args:
            tool_name: Full tool name (plugin.tool)
            parameters: Tool parameters
            
        Returns:
            Result string
        """
        plugin_manager = self.jarvis.plugin_manager
        
        if not plugin_manager:
            return "Plugin system not available"
        
        # Split plugin and tool name
        parts = tool_name.split('.', 1)
        if len(parts) != 2:
            return f"Invalid plugin tool name: {tool_name}"
        
        plugin_name, tool_func_name = parts
        
        # Get plugin
        plugin = plugin_manager.plugins.get(plugin_name)
        if not plugin:
            return f"Plugin not loaded: {plugin_name}"
        
        # Get tool function
        tools = plugin.get_tools()
        tool_func = tools.get(tool_func_name)
        
        if not tool_func:
            return f"Tool not found: {tool_name}"
        
        try:
            # Execute tool
            result = tool_func(**parameters)
            
            # Format result
            if isinstance(result, dict):
                if result.get("success"):
                    return result.get("message", str(result))
                else:
                    return f"Error: {result.get('message', 'Unknown error')}"
            else:
                return str(result)
        
        except TypeError as e:
            # Parameter mismatch
            logger.error(f"Tool parameter error: {str(e)}")
            return f"Tool parameter error: {str(e)}"
        
        except Exception as e:
            logger.error(f"Tool execution error: {str(e)}", exc_info=True)
            return f"Error executing tool: {str(e)}"
