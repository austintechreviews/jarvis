"""
JARVIS Fine-Tuning Integration Module
Hooks for integrating fine-tuning with main JARVIS assistant
"""

from pathlib import Path
from typing import Optional


def get_data_collector():
    """Get data collector instance for main JARVIS"""
    from .data_collector import DataCollector
    return DataCollector(Path.home() / "jarvis" / "logs")


def log_interaction(
    user_input: str,
    assistant_response: str,
    tool_used: Optional[str] = None,
    success: bool = True,
    execution_time: float = 0.0,
    context: dict = None
):
    """
    Log interaction from main JARVIS
    
    Call this in your main JARVIS loop after each interaction
    """
    collector = get_data_collector()
    collector.log_interaction(
        user_input=user_input,
        assistant_response=assistant_response,
        tool_used=tool_used,
        success=success,
        execution_time=execution_time,
        context=context
    )


def log_correction(
    original_command: str,
    assistant_attempt: str,
    user_correction: str,
    correction_type: str = "command"
):
    """
    Log user correction from main JARVIS
    
    Call this when user provides feedback/correction
    """
    collector = get_data_collector()
    collector.log_user_correction(
        original_command=original_command,
        assistant_attempt=assistant_attempt,
        user_correction=user_correction,
        correction_type=correction_type
    )


def switch_to_finetuned_model(model_name: str = "jarvis-finetuned:v1"):
    """
    Switch JARVIS to use fine-tuned model
    
    Call this to activate fine-tuned model
    """
    import interpreter
    interpreter.llm.model = f"ollama/{model_name}"
    print(f"Switched to fine-tuned model: {model_name}")


def switch_to_base_model(model_name: str = "qwen2.5-coder:3b"):
    """
    Switch JARVIS back to base model
    
    Call this to deactivate fine-tuned model
    """
    import interpreter
    interpreter.llm.model = f"ollama/{model_name}"
    print(f"Switched to base model: {model_name}")


def get_collection_stats():
    """Get statistics about collected training data"""
    collector = get_data_collector()
    return collector.get_stats()


class FineTuningIntegration:
    """
    Main integration class for fine-tuning
    Attach this to your JARVIS instance
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.collector = get_data_collector() if enabled else None
        
    def on_interaction(
        self,
        user_input: str,
        assistant_response: str,
        tool_used: Optional[str] = None,
        success: bool = True,
        execution_time: float = 0.0,
        context: dict = None
    ):
        """Call after each interaction"""
        if self.enabled and self.collector:
            self.collector.log_interaction(
                user_input=user_input,
                assistant_response=assistant_response,
                tool_used=tool_used,
                success=success,
                execution_time=execution_time,
                context=context
            )
    
    def on_correction(
        self,
        original: str,
        attempt: str,
        correction: str,
        correction_type: str = "command"
    ):
        """Call when user provides correction"""
        if self.enabled and self.collector:
            self.collector.log_user_correction(
                original_command=original,
                assistant_attempt=attempt,
                user_correction=correction,
                correction_type=correction_type
            )
    
    def enable(self):
        """Enable data collection"""
        self.enabled = True
        self.collector = get_data_collector()
        print("Fine-tuning data collection enabled")
    
    def disable(self):
        """Disable data collection"""
        self.enabled = False
        self.collector = None
        print("Fine-tuning data collection disabled")
    
    def stats(self):
        """Get collection statistics"""
        if self.collector:
            return self.collector.get_stats()
        return {}


if __name__ == "__main__":
    print("JARVIS Fine-Tuning Integration Module")
    print("Import this module in your main JARVIS code")
    print()
    print("Example usage:")
    print("  from finetuning.integration import FineTuningIntegration")
    print("  finetuning = FineTuningIntegration(enabled=True)")
    print("  # After each interaction:")
    print("  finetuning.on_interaction(user_input, response, tool_used='terminal')")
