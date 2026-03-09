"""
Browser-Use Controller - LLM-powered browser automation
Uses AI to understand pages and execute tasks

Note: Browser-Use v0.1+ requires a specific LLM interface.
We wrap ChatOllama to provide the expected interface.
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Try to import browser_use, handle if not installed
try:
    from browser_use import Agent
    from browser_use.browser.profile import BrowserProfile
    from langchain_ollama import ChatOllama
    from langchain_core.messages import HumanMessage, SystemMessage
    BROWSER_USE_AVAILABLE = True
    logger.info("Browser-Use library loaded successfully")
except ImportError as e:
    logger.warning(f"Browser-Use import failed: {e}")
    BROWSER_USE_AVAILABLE = False
    Agent = None
    BrowserProfile = None
    ChatOllama = None


class SimpleLLMWrapper:
    """
    Simple wrapper to make ChatOllama compatible with Browser-Use
    Browser-Use expects: llm.invoke(messages) -> response
    """
    
    def __init__(self, chat_model: ChatOllama, model_name: str = "qwen2.5-coder:3b"):
        self.chat_model = chat_model
        self.provider = "ollama"  # Required by Browser-Use
        self.model_name = model_name  # Required by Browser-Use cloud events
    
    def invoke(self, messages: List) -> Any:
        """Invoke the LLM with messages"""
        # Convert to format ChatOllama expects
        langchain_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'system':
                    langchain_messages.append(SystemMessage(content=content))
                else:
                    langchain_messages.append(HumanMessage(content=content))
        
        response = self.chat_model.invoke(langchain_messages)
        return response
    
    def __getattr__(self, name):
        """Delegate other attributes to chat_model"""
        return getattr(self.chat_model, name)


class BrowserUseController:
    """
    Intelligent browser automation using Browser-Use
    
    What it can do:
    - "Login to Gmail and send an email to X"
    - "Search Amazon for headphones under $50"
    - "Find Python jobs on Indeed and save the first 5"
    
    Note: Browser-Use API has changed significantly in recent versions.
    This implementation uses the latest API structure.
    """
    
    def __init__(
        self, 
        headless: bool = False,
        model_name: str = "qwen2.5-coder:3b",
        use_vision: bool = False
    ):
        """
        Initialize Browser-Use controller
        
        Args:
            headless: Run browser in headless mode
            model_name: Ollama model to use
            use_vision: Use vision model (llava) for screenshot analysis
        """
        self.headless = headless
        self.model_name = model_name
        self.use_vision = use_vision
        
        if not BROWSER_USE_AVAILABLE:
            raise ImportError("Browser-Use not installed. Install with: pip install browser-use langchain-ollama")
        
        # Initialize LLM with wrapper for Browser-Use compatibility
        if use_vision:
            # Use vision model for better page understanding
            chat_model = ChatOllama(
                model="llava:13b",
                temperature=0.1,
            )
        else:
            # Use text-only model
            chat_model = ChatOllama(
                model=model_name,
                temperature=0.1,
            )
        
        # Wrap for Browser-Use compatibility
        self.llm = SimpleLLMWrapper(chat_model, model_name=model_name)
        
        # Browser profile configuration
        self.browser_profile = BrowserProfile(
            headless=headless,
        )
        
        # Agent will be created per-task
        self.current_agent: Optional[Agent] = None
        self.is_running = False
        
        logger.info(f"Browser-Use initialized with model: {model_name}")
    
    def execute_task(self, task: str, max_steps: int = 10) -> Dict[str, Any]:
        """
        Execute a browser automation task using AI
        
        Args:
            task: Natural language task description
            max_steps: Maximum number of actions agent can take
            
        Returns:
            {
                "success": bool,
                "result": str,
                "steps_taken": int,
                "final_url": str,
                "error": str
            }
        """
        if not BROWSER_USE_AVAILABLE:
            return {
                "success": False,
                "result": "",
                "steps_taken": 0,
                "final_url": "",
                "error": "Browser-Use not installed"
            }
        
        try:
            logger.info(f"Executing Browser-Use task: {task}")
            
            # Create agent for this task
            agent = Agent(
                task=task,
                llm=self.llm,
                browser_profile=self.browser_profile,
            )
            
            self.current_agent = agent
            self.is_running = True
            
            # Run the agent (async)
            import asyncio
            try:
                # Try to run in existing event loop
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop, create new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(agent.run(max_steps=max_steps))
            
            self.is_running = False
            
            return {
                "success": True,
                "result": str(result) if result else "Task completed",
                "steps_taken": max_steps,
                "final_url": "Completed",
                "error": ""
            }
        
        except Exception as e:
            logger.error(f"Browser-Use task failed: {str(e)}", exc_info=True)
            self.is_running = False
            
            return {
                "success": False,
                "result": "",
                "steps_taken": 0,
                "final_url": "",
                "error": str(e)
            }
    
    def stop(self):
        """Stop current browser session"""
        try:
            if self.current_agent:
                self.current_agent = None
            self.is_running = False
            logger.info("Browser-Use stopped")
        except Exception as e:
            logger.error(f"Error stopping Browser-Use: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Browser-Use is available"""
        return BROWSER_USE_AVAILABLE
