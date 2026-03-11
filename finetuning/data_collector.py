"""
JARVIS Data Collector for Fine-Tuning
Comprehensive data collection with context, corrections, and quality metrics
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict
import re


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
        self.patterns_log = self.log_dir / "successful_patterns.jsonl"
        self.context_log = self.log_dir / "context.jsonl"
        
        # In-memory caches
        self._session_interactions = []
        self._corrections_cache = []
        
    def log_interaction(
        self,
        user_input: str,
        assistant_response: str,
        tool_used: Optional[str] = None,
        success: bool = True,
        execution_time: float = 0.0,
        context: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Log a complete interaction with metadata
        
        Args:
            user_input: User's command
            assistant_response: JARVIS's response
            tool_used: Which tool was invoked (terminal, browser, etc.)
            success: Whether the command executed successfully
            execution_time: Time taken to execute
            context: Additional context (current directory, open apps, etc.)
            metadata: Additional metadata
            
        Returns:
            Interaction ID for tracking
        """
        interaction_id = self._generate_id(user_input, datetime.now())
        
        entry = {
            "id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "user": user_input,
            "assistant": assistant_response,
            "metadata": {
                "tool": tool_used,
                "success": success,
                "execution_time": execution_time,
                "context": context or {},
                "custom": metadata or {}
            }
        }
        
        with open(self.conversation_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        self._session_interactions.append(entry)
        return interaction_id
    
    def log_user_correction(
        self,
        original_command: str,
        assistant_attempt: str,
        user_correction: str,
        correction_type: str = "command",
        interaction_id: str = None
    ) -> str:
        """
        Log when user corrects JARVIS
        These are HIGH VALUE training examples
        
        Args:
            original_command: What user asked for
            assistant_attempt: What JARVIS tried to do
            user_correction: What user said should have happened
            correction_type: Type of correction (command, path, parameter, style, etc.)
            interaction_id: Original interaction ID if available
            
        Returns:
            Correction ID
        """
        correction_id = self._generate_id(user_correction, datetime.now())
        
        entry = {
            "id": correction_id,
            "interaction_id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "type": "correction",
            "original": original_command,
            "attempt": assistant_attempt,
            "correction": user_correction,
            "correction_type": correction_type,
            "quality_score": 1.0  # Corrections are high-quality
        }
        
        with open(self.feedback_log, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        self._corrections_cache.append(entry)
        return correction_id
    
    def log_successful_pattern(
        self,
        command: str,
        execution: str,
        outcome: str,
        frequency: int = 1,
        confidence: float = 1.0
    ) -> str:
        """
        Log successful command patterns for reinforcement
        
        Args:
            command: Natural language command
            execution: Actual execution (bash command, Python code, etc.)
            outcome: Result description
            frequency: How many times this pattern has been successful
            confidence: Confidence score (0-1)
            
        Returns:
            Pattern ID
        """
        pattern_id = self._generate_id(f"{command}:{execution}", datetime.now())
        
        pattern = {
            "id": pattern_id,
            "timestamp": datetime.now().isoformat(),
            "type": "successful_pattern",
            "command": command,
            "execution": execution,
            "outcome": outcome,
            "frequency": frequency,
            "confidence": confidence
        }
        
        with open(self.patterns_log, 'a') as f:
            f.write(json.dumps(pattern) + '\n')
        
        return pattern_id
    
    def log_context(
        self,
        working_directory: str = None,
        open_applications: List[str] = None,
        environment_variables: Dict[str, str] = None,
        system_state: Dict[str, Any] = None
    ):
        """Log contextual information for better understanding"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "working_directory": working_directory,
            "open_applications": open_applications or [],
            "environment_variables": environment_variables or {},
            "system_state": system_state or {}
        }
        
        with open(self.context_log, 'a') as f:
            f.write(json.dumps(context) + '\n')
    
    def export_for_training(
        self,
        output_file: Path,
        min_success_rate: float = 0.8,
        exclude_errors: bool = True,
        include_corrections: bool = True,
        deduplicate: bool = True
    ) -> Tuple[int, Dict[str, int]]:
        """
        Export high-quality training examples
        
        Args:
            output_file: Where to save training data
            min_success_rate: Minimum success rate for commands
            exclude_errors: Skip failed executions
            include_corrections: Include user corrections (augmented)
            deduplicate: Remove duplicates
            
        Returns:
            Tuple of (count, stats by category)
        """
        conversations = []
        stats = defaultdict(int)
        seen_hashes = set()
        
        # Read conversations
        if self.conversation_log.exists():
            with open(self.conversation_log, 'r') as f:
                for line in f:
                    try:
                        conv = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    # Filter based on success
                    if exclude_errors and not conv['metadata'].get('success', True):
                        continue
                    
                    # Deduplicate
                    if deduplicate:
                        msg_hash = hashlib.md5(
                            f"{conv['user']}:{conv['assistant']}".encode()
                        ).hexdigest()
                        if msg_hash in seen_hashes:
                            continue
                        seen_hashes.add(msg_hash)
                    
                    # Categorize
                    category = self._categorize_interaction(conv['user'])
                    stats[category] += 1
                    
                    conversations.append({
                        "messages": [
                            {"role": "user", "content": conv['user']},
                            {"role": "assistant", "content": conv['assistant']}
                        ],
                        "metadata": conv['metadata'],
                        "category": category
                    })
        
        # Add corrections as augmented examples
        if include_corrections and self.feedback_log.exists():
            with open(self.feedback_log, 'r') as f:
                for line in f:
                    try:
                        correction = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    # Create training example from correction
                    conversations.append({
                        "messages": [
                            {"role": "user", "content": correction['original']},
                            {"role": "assistant", "content": correction['correction']}
                        ],
                        "metadata": {
                            "source": "correction",
                            "correction_type": correction.get('correction_type', 'unknown'),
                            "quality_score": 1.0
                        },
                        "category": self._categorize_interaction(correction['original'])
                    })
                    stats["corrections"] += 1
        
        # Write to output file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            for conv in conversations:
                f.write(json.dumps(conv) + '\n')
        
        return len(conversations), dict(stats)
    
    def _categorize_interaction(self, user_input: str) -> str:
        """Categorize interaction by type"""
        text = user_input.lower()
        
        categories = {
            'file_ops': ['file', 'folder', 'directory', 'create', 'delete', 'move', 'copy', 'rename'],
            'web_search': ['search', 'find information', 'google', 'look up', 'what is'],
            'browser': ['browser', 'click', 'navigate', 'website', 'open firefox', 'open chrome'],
            'terminal': ['run', 'execute', 'command', 'install', 'sudo', 'apt', 'pacman'],
            'desktop': ['screenshot', 'mouse', 'type', 'keyboard', 'click', 'window'],
            'code': ['python', 'script', 'code', 'program', 'function', 'class'],
            'system': ['system', 'config', 'settings', 'update', 'upgrade'],
        }
        
        for category, keywords in categories.items():
            if any(kw in text for kw in keywords):
                return category
        
        return 'other'
    
    def _generate_id(self, content: str, timestamp: datetime) -> str:
        """Generate unique ID for an entry"""
        hash_input = f"{content}:{timestamp.isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about collected data"""
        stats = {
            "total_interactions": 0,
            "successful": 0,
            "failed": 0,
            "corrections": 0,
            "patterns": 0,
            "by_category": defaultdict(int),
            "by_tool": defaultdict(int)
        }
        
        if self.conversation_log.exists():
            with open(self.conversation_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        stats["total_interactions"] += 1
                        
                        if entry['metadata'].get('success', True):
                            stats["successful"] += 1
                        else:
                            stats["failed"] += 1
                        
                        # Category stats
                        category = self._categorize_interaction(entry['user'])
                        stats["by_category"][category] += 1
                        
                        # Tool stats
                        tool = entry['metadata'].get('tool', 'unknown')
                        stats["by_tool"][tool] += 1
                    except (json.JSONDecodeError, KeyError):
                        continue
        
        if self.feedback_log.exists():
            with open(self.feedback_log, 'r') as f:
                stats["corrections"] = sum(1 for _ in f)
        
        if self.patterns_log.exists():
            with open(self.patterns_log, 'r') as f:
                stats["patterns"] = sum(1 for _ in f)
        
        # Convert defaultdicts to regular dicts for JSON serialization
        stats["by_category"] = dict(stats["by_category"])
        stats["by_tool"] = dict(stats["by_tool"])
        
        return stats
    
    def get_quality_report(self) -> Dict[str, Any]:
        """Generate data quality report"""
        stats = self.get_stats()
        
        total = stats['total_interactions']
        successful = stats['successful']
        corrections = stats['corrections']
        
        # Calculate quality metrics
        success_rate = successful / total if total > 0 else 0
        correction_rate = corrections / total if total > 0 else 0
        
        # Readiness assessment
        readiness = {
            "ready": False,
            "level": "insufficient",
            "recommendations": []
        }
        
        if total >= 500:
            readiness["level"] = "excellent"
            readiness["ready"] = True
        elif total >= 100:
            readiness["level"] = "good"
            readiness["ready"] = True
        elif total >= 50:
            readiness["level"] = "fair"
            readiness["recommendations"].append("Collect more diverse interactions")
        else:
            readiness["level"] = "insufficient"
            readiness["recommendations"].append(f"Need {100 - total} more interactions")
        
        if success_rate < 0.7:
            readiness["recommendations"].append("Improve success rate (currently {:.1%})".format(success_rate))
        
        if corrections > total * 0.3:
            readiness["recommendations"].append("High correction rate - model needs more training")
        
        return {
            "statistics": stats,
            "quality_metrics": {
                "success_rate": success_rate,
                "correction_rate": correction_rate,
                "unique_categories": len(stats["by_category"]),
                "unique_tools": len(stats["by_tool"])
            },
            "readiness": readiness
        }
    
    def clear_session(self):
        """Clear in-memory caches"""
        self._session_interactions = []
        self._corrections_cache = []
    
    def backup_logs(self, backup_dir: Path = None) -> Path:
        """Create backup of all logs"""
        backup_dir = backup_dir or (self.log_dir / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S"))
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        import shutil
        for log_file in [self.conversation_log, self.feedback_log, self.patterns_log, self.context_log]:
            if log_file.exists():
                shutil.copy2(log_file, backup_dir / log_file.name)
        
        return backup_dir


if __name__ == "__main__":
    import sys
    
    log_dir = Path.home() / "jarvis" / "logs"
    if len(sys.argv) > 1:
        log_dir = Path(sys.argv[1])
    
    collector = DataCollector(log_dir)
    
    if len(sys.argv) > 2 and sys.argv[2] == "report":
        report = collector.get_quality_report()
        print(json.dumps(report, indent=2))
    else:
        stats = collector.get_stats()
        print("=== Data Collection Statistics ===")
        print(f"Total interactions: {stats['total_interactions']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"User corrections: {stats['corrections']}")
        print(f"Successful patterns: {stats['patterns']}")
        print(f"\nBy category: {stats['by_category']}")
        print(f"By tool: {stats['by_tool']}")
