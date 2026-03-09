"""
Plugin System for JARVIS
Allows dynamic loading of new tools and capabilities
"""

import logging
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Callable, Any, Optional
import sys

logger = logging.getLogger(__name__)


class JARVISPlugin:
    """
    Base class for all JARVIS plugins
    
    Subclass this to create new plugins
    """
    
    # Plugin metadata (override in subclass)
    name: str = "base_plugin"
    version: str = "1.0.0"
    description: str = "Base plugin class"
    author: str = "Unknown"
    
    # Dependencies (package names)
    required_packages: List[str] = []
    
    def __init__(self):
        """Initialize plugin"""
        pass
    
    def check_dependencies(self) -> bool:
        """
        Check if all required packages are installed
        
        Returns:
            True if all dependencies are met
        """
        for package in self.required_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                logger.warning(f"Plugin '{self.name}' missing dependency: {package}")
                return False
        return True
    
    def initialize(self) -> bool:
        """
        Initialize the plugin
        
        Returns:
            True if initialization successful
        """
        return True
    
    def get_tools(self) -> Dict[str, Callable]:
        """
        Return dictionary of tool functions this plugin provides
        
        Returns:
            {"tool_name": function, ...}
        """
        return {}
    
    def get_system_prompt_addition(self) -> str:
        """
        Return text to add to JARVIS system prompt
        
        Returns:
            Markdown-formatted text describing plugin capabilities
        """
        return ""
    
    def cleanup(self):
        """Cleanup plugin resources"""
        pass


class PluginManager:
    """
    Manages JARVIS plugins
    
    Features:
    - Auto-discover plugins in plugins/ directory
    - Load/unload plugins dynamically
    - Register plugin tools with JARVIS
    - Aggregate system prompts from plugins
    """
    
    def __init__(self, plugins_dir: Path):
        """
        Initialize plugin manager
        
        Args:
            plugins_dir: Directory containing plugin files
        """
        self.plugins_dir = plugins_dir
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # Loaded plugins
        self.plugins: Dict[str, JARVISPlugin] = {}
        
        # Aggregated tools from all plugins
        self.tools: Dict[str, Callable] = {}
        
        logger.info(f"Plugin manager initialized: {plugins_dir}")
    
    def discover_plugins(self) -> List[str]:
        """
        Discover all available plugins in plugins directory
        
        Returns:
            List of plugin module names
        """
        plugin_files = []
        
        # Find all .py files in plugins directory
        for file_path in self.plugins_dir.glob("*.py"):
            if file_path.stem.startswith("_"):
                continue  # Skip __init__.py and private files
            
            plugin_files.append(file_path.stem)
        
        logger.info(f"Discovered {len(plugin_files)} potential plugins: {plugin_files}")
        return plugin_files
    
    def load_plugin(self, module_name: str) -> bool:
        """
        Load a single plugin by module name
        
        Args:
            module_name: Name of plugin file (without .py)
            
        Returns:
            True if loaded successfully
        """
        try:
            # Add plugins directory to path
            plugins_path = str(self.plugins_dir.parent)
            if plugins_path not in sys.path:
                sys.path.insert(0, plugins_path)
            
            # Import the module
            full_module_name = f"plugins.{module_name}"
            module = importlib.import_module(full_module_name)
            
            # Find JARVISPlugin subclass in module
            plugin_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, JARVISPlugin) and obj != JARVISPlugin:
                    plugin_class = obj
                    break
            
            if not plugin_class:
                logger.error(f"No JARVISPlugin subclass found in {module_name}")
                return False
            
            # Instantiate plugin
            plugin = plugin_class()
            
            # Check dependencies
            if not plugin.check_dependencies():
                logger.warning(f"Plugin '{plugin.name}' dependencies not met")
                return False
            
            # Initialize plugin
            if not plugin.initialize():
                logger.error(f"Plugin '{plugin.name}' initialization failed")
                return False
            
            # Register plugin
            self.plugins[plugin.name] = plugin
            
            # Register tools
            plugin_tools = plugin.get_tools()
            for tool_name, tool_func in plugin_tools.items():
                # Namespace tool names with plugin name
                namespaced_name = f"{plugin.name}.{tool_name}"
                self.tools[namespaced_name] = tool_func
                logger.info(f"Registered tool: {namespaced_name}")
            
            logger.info(f"✓ Plugin loaded: {plugin.name} v{plugin.version}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load plugin {module_name}: {str(e)}", exc_info=True)
            return False
    
    def load_all_plugins(self) -> int:
        """
        Load all discovered plugins
        
        Returns:
            Number of successfully loaded plugins
        """
        plugin_names = self.discover_plugins()
        
        loaded_count = 0
        for plugin_name in plugin_names:
            if self.load_plugin(plugin_name):
                loaded_count += 1
        
        logger.info(f"Loaded {loaded_count}/{len(plugin_names)} plugins")
        return loaded_count
    
    def unload_plugin(self, plugin_name: str):
        """Unload a plugin and cleanup its resources"""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            
            # Cleanup
            plugin.cleanup()
            
            # Remove tools
            tools_to_remove = [name for name in self.tools.keys() 
                             if name.startswith(f"{plugin_name}.")]
            for tool_name in tools_to_remove:
                del self.tools[tool_name]
            
            # Remove plugin
            del self.plugins[plugin_name]
            
            logger.info(f"Unloaded plugin: {plugin_name}")
    
    def get_tool(self, tool_name: str) -> Optional[Callable]:
        """
        Get a tool function by name
        
        Args:
            tool_name: Full tool name (plugin.tool or just tool)
            
        Returns:
            Tool function or None
        """
        # Try exact match first
        if tool_name in self.tools:
            return self.tools[tool_name]
        
        # Try without namespace
        for name, func in self.tools.items():
            if name.endswith(f".{tool_name}"):
                return func
        
        return None
    
    def list_tools(self) -> Dict[str, str]:
        """
        List all available tools with descriptions
        
        Returns:
            {tool_name: description}
        """
        tools_info = {}
        
        for plugin_name, plugin in self.plugins.items():
            plugin_tools = plugin.get_tools()
            for tool_name in plugin_tools.keys():
                full_name = f"{plugin_name}.{tool_name}"
                # Get docstring as description
                func = plugin_tools[tool_name]
                description = func.__doc__ or "No description"
                tools_info[full_name] = description.split('\n')[0].strip()
        
        return tools_info
    
    def get_aggregated_system_prompt(self) -> str:
        """
        Aggregate system prompt additions from all plugins
        
        Returns:
            Combined system prompt text
        """
        prompt_parts = []
        
        for plugin_name, plugin in self.plugins.items():
            addition = plugin.get_system_prompt_addition()
            if addition:
                prompt_parts.append(f"## {plugin.name}")
                prompt_parts.append(addition)
                prompt_parts.append("")
        
        if prompt_parts:
            header = "# PLUGIN TOOLS\n\n"
            return header + "\n".join(prompt_parts)
        
        return ""
    
    def get_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all plugins
        
        Returns:
            {
                plugin_name: {
                    "version": "1.0.0",
                    "status": "loaded",
                    "tools": ["tool1", "tool2"]
                }
            }
        """
        status = {}
        
        for plugin_name, plugin in self.plugins.items():
            tools = list(plugin.get_tools().keys())
            status[plugin_name] = {
                "version": plugin.version,
                "description": plugin.description,
                "author": plugin.author,
                "status": "loaded",
                "tools": tools,
                "tool_count": len(tools)
            }
        
        return status
    
    def cleanup_all(self):
        """Cleanup all plugins"""
        for plugin in self.plugins.values():
            try:
                plugin.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up plugin: {str(e)}")
