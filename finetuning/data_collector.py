"""
JARVIS Data Collector for Fine-Tuning
Captures interactions, user corrections, and successful patterns
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class DataCollector:
    """
    Enhanced data collection for fine-tuning
    Captures context, success metrics, and user corrections
    """
    
    def __init__(self, log_dir: Path = None):
        self.log_dir = log_dir or Path.home() / "jarvis" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.conversation_log = self.log_dir / "conversations.jsonl"
        self.training_data = self.log_dir / "training_ready.jsonl"
        self.feedback_log = self.log_dir / "user_feedback.jsonl"
        
    def log_interaction(
        self,
        user_input: str,
        assistant_response: str,
        tool_used: Optional[str] = None,
        success: bool = True,
        execution_time: float = 0.0,
        context: Dict[str, Any] = None
    ):
        """
        Log a complete interaction with metadata
        
        Args:
            user_input: User's command
            assistant_response: JARVIS's response
            tool_used: Which tool was invoked (terminal, browser, etc.)
            success: Whether the command executed successfully
            execution_time: Time taken to execute
            context: Additional context (current directory, open apps, etc.)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "assistant": assistant_response,
            "metadata": {
                "tool": tool_used,
                "success": success,
                "execution_time": execution_time,
                "context": context or {}
            }
        }
        
        with open(self.conversation_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def log_user_correction(
        self,
        original_command: str,
        assistant_attempt: str,
        user_correction: str,
        correction_type: str = "command"
    ):
        """
        Log when user corrects JARVIS
        These are HIGH VALUE training examples
        
        Args:
            original_command: What user asked for
            assistant_attempt: What JARVIS tried to do
            user_correction: What user said should have happened
            correction_type: Type of correction (command, path, parameter, etc.)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "correction",
            "original": original_command,
            "attempt": assistant_attempt,
            "correction": user_correction,
            "correction_type": correction_type
        }
        
        with open(self.feedback_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def log_successful_pattern(
        self,
        command: str,
        execution: str,
        outcome: str,
        frequency: int = 1
    ):
        """
        Log successful command patterns for reinforcement
        
        Args:
            command: Natural language command
            execution: Actual execution (bash command, Python code, etc.)
            outcome: Result description
            frequency: How many times this pattern has been successful
        """
        pattern = {
            "timestamp": datetime.now().isoformat(),
            "type": "successful_pattern",
            "command": command,
            "execution": execution,
            "outcome": outcome,
            "frequency": frequency
        }
        
        with open(self.training_data, 'a') as f:
            f.write(json.dumps(pattern) + '\n')
    
    def export_for_training(
        self,
        output_file: Path,
        min_success_rate: float = 0.8,
        exclude_errors: bool = True
    ) -> int:
        """
        Export high-quality training examples
        
        Args:
            output_file: Where to save training data
            min_success_rate: Minimum success rate for commands
            exclude_errors: Skip failed executions
            
        Returns:
            Number of examples exported
        """
        conversations = []
        with open(self.conversation_log, 'r') as f:
            for line in f:
                conv = json.loads(line)
                
                if exclude_errors and not conv['metadata'].get('success', True):
                    continue
                
                conversations.append({
                    "messages": [
                        {"role": "user", "content": conv['user']},
                        {"role": "assistant", "content": conv['assistant']}
                    ],
                    "metadata": conv['metadata']
                })
        
        with open(output_file, 'w') as f:
            for conv in conversations:
                f.write(json.dumps(conv) + '\n')
        
        return len(conversations)
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about collected data"""
        stats = {
            "total_interactions": 0,
            "successful": 0,
            "failed": 0,
            "corrections": 0,
            "patterns": 0
        }
        
        if self.conversation_log.exists():
            with open(self.conversation_log, 'r') as f:
                for line in f:
                    stats["total_interactions"] += 1
                    entry = json.loads(line)
                    if entry['metadata'].get('success', True):
                        stats["successful"] += 1
                    else:
                        stats["failed"] += 1
        
        if self.feedback_log.exists():
            with open(self.feedback_log, 'r') as f:
                stats["corrections"] = sum(1 for _ in f)
        
        if self.training_data.exists():
            with open(self.training_data, 'r') as f:
                stats["patterns"] = sum(1 for _ in f)
        
        return stats


if __name__ == "__main__":
    collector = DataCollector()
    stats = collector.get_stats()
    
    print("=== Data Collection Statistics ===")
    print(f"Total interactions: {stats['total_interactions']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"User corrections: {stats['corrections']}")
    print(f"Successful patterns: {stats['patterns']}")
