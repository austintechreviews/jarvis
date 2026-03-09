"""
Dataset Preparation Tools for JARVIS Fine-Tuning
Clean, deduplicate, and balance training data
"""

import json
import re
import random
from pathlib import Path
from typing import List, Dict, Any


class DatasetPreparator:
    """
    Clean and format raw logs into training-ready datasets
    """
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        
    def clean_conversation(self, conv: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean a single conversation
        - Remove sensitive info (passwords, API keys)
        - Normalize paths
        - Fix formatting
        """
        user_msg = conv['messages'][0]['content']
        assistant_msg = conv['messages'][1]['content']
        
        user_msg = self._remove_sensitive_data(user_msg)
        assistant_msg = self._remove_sensitive_data(assistant_msg)
        
        home = str(Path.home())
        user_msg = user_msg.replace(home, '~')
        assistant_msg = assistant_msg.replace(home, '~')
        
        return {
            "messages": [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg}
            ]
        }
    
    def _remove_sensitive_data(self, text: str) -> str:
        """Remove potential sensitive information"""
        text = re.sub(r'\b[A-Za-z0-9]{32,}\b', '[API_KEY]', text)
        text = re.sub(r'password[=\s]+\S+', 'password=[REDACTED]', text, flags=re.IGNORECASE)
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_ADDRESS]', text)
        return text
    
    def deduplicate(self, conversations: List[Dict]) -> List[Dict]:
        """Remove duplicate or very similar conversations"""
        seen = set()
        unique = []
        
        for conv in conversations:
            user_msg = conv['messages'][0]['content']
            msg_hash = hash(user_msg.lower().strip())
            
            if msg_hash not in seen:
                seen.add(msg_hash)
                unique.append(conv)
        
        return unique
    
    def balance_dataset(
        self,
        conversations: List[Dict],
        max_per_category: int = 100
    ) -> List[Dict]:
        """
        Balance dataset across different command types
        Prevents over-fitting on common commands like 'ls'
        """
        categories = {
            'file_ops': [],
            'web_search': [],
            'browser': [],
            'terminal': [],
            'desktop': [],
            'other': []
        }
        
        for conv in conversations:
            user_msg = conv['messages'][0]['content'].lower()
            
            if any(kw in user_msg for kw in ['file', 'folder', 'directory', 'create', 'delete']):
                categories['file_ops'].append(conv)
            elif any(kw in user_msg for kw in ['search', 'find information', 'google']):
                categories['web_search'].append(conv)
            elif any(kw in user_msg for kw in ['browser', 'click', 'navigate']):
                categories['browser'].append(conv)
            elif any(kw in user_msg for kw in ['run', 'execute', 'command', 'install']):
                categories['terminal'].append(conv)
            elif any(kw in user_msg for kw in ['screenshot', 'mouse', 'type', 'keyboard']):
                categories['desktop'].append(conv)
            else:
                categories['other'].append(conv)
        
        balanced = []
        for category, items in categories.items():
            if len(items) > max_per_category:
                items = items[-max_per_category:]
            balanced.extend(items)
        
        return balanced
    
    def create_training_dataset(
        self,
        input_file: Path,
        output_file: Path,
        validation_split: float = 0.1
    ) -> Dict[str, Any]:
        """
        Create train/validation split
        
        Returns:
            Dict with train/val counts and file paths
        """
        conversations = []
        with open(input_file, 'r') as f:
            for line in f:
                conversations.append(json.loads(line))
        
        cleaned = [self.clean_conversation(c) for c in conversations]
        unique = self.deduplicate(cleaned)
        balanced = self.balance_dataset(unique)
        
        split_idx = int(len(balanced) * (1 - validation_split))
        train_data = balanced[:split_idx]
        val_data = balanced[split_idx:]
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        train_file = output_file.parent / f"{output_file.stem}_train.jsonl"
        val_file = output_file.parent / f"{output_file.stem}_val.jsonl"
        
        with open(train_file, 'w') as f:
            for item in train_data:
                f.write(json.dumps(item) + '\n')
        
        with open(val_file, 'w') as f:
            for item in val_data:
                f.write(json.dumps(item) + '\n')
        
        return {
            "train": len(train_data),
            "val": len(val_data),
            "train_file": str(train_file),
            "val_file": str(val_file)
        }


class DataAugmenter:
    """
    Create synthetic training examples from existing data
    """
    
    def __init__(self):
        self.synonyms = {
            'list': ['show', 'display', 'get'],
            'find': ['search', 'locate', 'look for'],
            'delete': ['remove', 'erase', 'get rid of'],
            'create': ['make', 'generate', 'build'],
            'open': ['launch', 'start', 'run'],
        }
    
    def augment_by_paraphrasing(self, conversation: Dict) -> List[Dict]:
        """Create variations by replacing synonyms"""
        user_msg = conversation['messages'][0]['content']
        assistant_msg = conversation['messages'][1]['content']
        
        variations = []
        
        for word, synonyms in self.synonyms.items():
            if word in user_msg.lower():
                for syn in synonyms:
                    new_user_msg = user_msg.lower().replace(word, syn)
                    variations.append({
                        "messages": [
                            {"role": "user", "content": new_user_msg},
                            {"role": "assistant", "content": assistant_msg}
                        ]
                    })
        
        return variations
    
    def augment_with_context(self, conversation: Dict) -> List[Dict]:
        """Add contextual variations"""
        user_msg = conversation['messages'][0]['content']
        assistant_msg = conversation['messages'][1]['content']
        
        variations = []
        locations = ['Downloads', 'Documents', 'Desktop', 'home directory']
        
        if 'file' in user_msg.lower():
            for loc in locations:
                new_user_msg = f"{user_msg} in {loc}"
                new_assistant_msg = assistant_msg.replace('ls', f'ls ~/{loc}')
                variations.append({
                    "messages": [
                        {"role": "user", "content": new_user_msg},
                        {"role": "assistant", "content": new_assistant_msg}
                    ]
                })
        
        return variations


if __name__ == "__main__":
    import sys
    
    log_dir = Path.home() / "jarvis" / "logs"
    output_file = Path.home() / "jarvis" / "finetuning" / "data" / "dataset.jsonl"
    
    if len(sys.argv) > 1:
        log_dir = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
    
    prep = DatasetPreparator(log_dir)
    
    input_file = log_dir / "training_ready.jsonl"
    if not input_file.exists():
        print(f"Error: {input_file} not found. Run data collector first.")
        sys.exit(1)
    
    result = prep.create_training_dataset(
        input_file=input_file,
        output_file=output_file
    )
    
    print(f"Created {result['train']} training examples")
    print(f"Created {result['val']} validation examples")
    print(f"Train file: {result['train_file']}")
    print(f"Val file: {result['val_file']}")
