"""
Example Plugin Template for JARVIS
Copy this file to create your own plugins!
"""

import logging
from typing import Dict, Callable
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from modules.plugin_system import JARVISPlugin

logger = logging.getLogger(__name__)


class ExamplePlugin(JARVISPlugin):
    """
    Example plugin showing the structure
    
    Copy this file and modify:
    1. Change class name
    2. Update metadata (name, version, description)
    3. Add your tools in get_tools()
    4. Implement your tool functions
    5. Update system prompt addition
    """
    
    # Metadata - CHANGE THESE
    name = "example"
    version = "1.0.0"
    description = "Example plugin template - copy me!"
    author = "Your Name"
    
    # Required packages (list of package names)
    # Example: required_packages = ["requests", "beautifulsoup4"]
    required_packages = []
    
    def __init__(self):
        """Initialize plugin"""
        super().__init__()
        # Your initialization here
        self.some_state = None
    
    def check_dependencies(self) -> bool:
        """
        Check if all required packages are installed
        
        Returns:
            True if all dependencies are met
        """
        # You can override this for custom dependency checks
        return super().check_dependencies()
    
    def initialize(self) -> bool:
        """
        Setup plugin (called after __init__)
        Load config, connect to APIs, etc.
        
        Returns:
            True if successful
        """
        try:
            # Your initialization logic here
            # Example: Load config file
            config_file = Path.home() / "jarvis" / "config" / f"{self.name}_config.json"
            
            if config_file.exists():
                import json
                with open(config_file) as f:
                    config = json.load(f)
                logger.info(f"{self.name} plugin loaded config")
            
            logger.info(f"{self.name} plugin initialized")
            return True
        except Exception as e:
            logger.error(f"{self.name} initialization failed: {str(e)}")
            return False
    
    def get_tools(self) -> Dict[str, Callable]:
        """
        Return tools this plugin provides
        
        Returns:
            Dictionary mapping tool names to functions
        
        Example:
            return {
                "my_action": self.my_action,
                "another_action": self.another_action
            }
        """
        return {
            "example_action": self.example_action,
            "hello": self.hello
        }
    
    def example_action(self, param1: str, param2: int = 10) -> Dict:
        """
        Example tool function
        
        Args:
            param1: First parameter (required)
            param2: Second parameter (optional, default=10)
            
        Returns:
            Result dictionary with "success" and other fields
        
        Tip: Always return a dict with "success": True/False
        """
        try:
            # Your logic here
            result = f"Processed {param1} with value {param2}"
            
            return {
                "success": True,
                "result": result,
                "message": "Action completed successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def hello(self, name: str = "World") -> Dict:
        """
        Simple hello function
        
        Args:
            name: Name to greet
            
        Returns:
            Greeting message
        """
        return {
            "success": True,
            "message": f"Hello, {name}! from {self.name} plugin"
        }
    
    def get_system_prompt_addition(self) -> str:
        """
        Text to add to JARVIS system prompt
        Describe what your plugin can do
        
        Returns:
            Markdown-formatted description
        
        Tip: Include examples of how to use your tools
        """
        return """**Example Plugin Tools:**

- `example.example_action(param1, param2)` - Does something useful
- `example.hello(name)` - Says hello

Usage examples:
- "Use example plugin to process data"
- "Say hello to Alice"
- "Call example action with test parameter"
"""
    
    def cleanup(self):
        """
        Cleanup resources (called on shutdown)
        Close connections, save state, etc.
        """
        logger.info(f"{self.name} plugin cleanup")


# Create config template (optional)
def create_config_template():
    """Create a config template for this plugin"""
    config = {
        "api_key": "your_api_key_here",
        "setting1": "value1",
        "setting2": 42
    }
    
    config_path = Path.home() / "jarvis" / "config" / "example_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Config template created: {config_path}")


if __name__ == "__main__":
    # Run this to create config template
    create_config_template()
