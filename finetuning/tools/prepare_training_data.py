"""
Comprehensive Dataset Preparation Tools for JARVIS Fine-Tuning
Clean, deduplicate, balance, augment, and analyze training data
"""

import json
import re
import hashlib
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict
from datetime import datetime


class DatasetPreparator:
    """
    Clean and format raw logs into training-ready datasets
    """
    
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.stats = {
            "loaded": 0,
            "cleaned": 0,
            "deduplicated": 0,
            "balanced": 0,
            "final": 0
        }
    
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
        
        user_msg = self._normalize_whitespace(user_msg)
        assistant_msg = self._normalize_whitespace(assistant_msg)
        
        return {
            "messages": [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": assistant_msg}
            ],
            "metadata": conv.get('metadata', {}),
            "category": conv.get('category', 'unknown')
        }
    
    def _remove_sensitive_data(self, text: str) -> str:
        """Remove potential sensitive information"""
        # Remove API keys (pattern: 32+ alphanumeric chars)
        text = re.sub(r'\b[A-Za-z0-9]{32,}\b', '[API_KEY]', text)
        
        # Remove passwords in commands
        text = re.sub(r'password[=\s]+\S+', 'password=[REDACTED]', text, flags=re.IGNORECASE)
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        
        # Remove IP addresses
        text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_ADDRESS]', text)
        
        # Remove SSH keys
        text = re.sub(r'ssh-rsa\s+[A-Za-z0-9+/=]+', 'ssh-rsa [KEY]', text)
        
        # Remove AWS keys
        text = re.sub(r'AKIA[0-9A-Z]{16}', '[AWS_KEY]', text)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text"""
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text
    
    def deduplicate(self, conversations: List[Dict]) -> List[Dict]:
        """Remove duplicate or very similar conversations"""
        seen = set()
        unique = []
        
        for conv in conversations:
            user_msg = conv['messages'][0]['content']
            msg_hash = hashlib.md5(user_msg.lower().strip().encode()).hexdigest()
            
            if msg_hash not in seen:
                seen.add(msg_hash)
                unique.append(conv)
        
        self.stats["deduplicated"] = len(conversations) - len(unique)
        return unique
    
    def deduplicate_fuzzy(self, conversations: List[Dict], threshold: float = 0.9) -> List[Dict]:
        """Remove fuzzy duplicates using Jaccard similarity"""
        unique = []
        
        for conv in conversations:
            user_msg = set(conv['messages'][0]['content'].lower().split())
            
            is_duplicate = False
            for existing in unique:
                existing_msg = set(existing['messages'][0]['content'].lower().split())
                
                if not existing_msg or not user_msg:
                    continue
                
                intersection = len(user_msg & existing_msg)
                union = len(user_msg | existing_msg)
                similarity = intersection / union if union > 0 else 0
                
                if similarity >= threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(conv)
        
        return unique
    
    def balance_dataset(
        self,
        conversations: List[Dict],
        max_per_category: int = 100,
        min_per_category: int = 10,
        strategy: str = "sample"
    ) -> List[Dict]:
        """
        Balance dataset across different command types
        
        Args:
            conversations: List of conversations
            max_per_category: Maximum examples per category
            min_per_category: Minimum examples per category
            strategy: "sample" (take recent) or "distribute" (even distribution)
        """
        categories = defaultdict(list)
        
        for conv in conversations:
            category = conv.get('category', 'other')
            categories[category].append(conv)
        
        balanced = []
        
        if strategy == "sample":
            for category, items in categories.items():
                if len(items) > max_per_category:
                    items = items[-max_per_category:]
                balanced.extend(items)
        elif strategy == "distribute":
            max_items = max(len(items) for items in categories.values()) if categories else 1
            target_per_category = min(max_per_category, max_items)
            
            for category, items in categories.items():
                if len(items) < target_per_category:
                    items = items * (target_per_category // len(items) + 1)
                items = items[:target_per_category]
                random.shuffle(items)
                balanced.extend(items)
        
        random.shuffle(balanced)
        self.stats["balanced"] = len(balanced)
        return balanced
    
    def create_train_val_split(
        self,
        conversations: List[Dict],
        val_split: float = 0.1,
        stratify: bool = True
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Create train/validation split
        
        Args:
            conversations: List of conversations
            val_split: Fraction for validation
            stratify: Maintain category distribution
        """
        if not stratify:
            random.shuffle(conversations)
            split_idx = int(len(conversations) * (1 - val_split))
            return conversations[:split_idx], conversations[split_idx:]
        
        categories = defaultdict(list)
        for conv in conversations:
            category = conv.get('category', 'other')
            categories[category].append(conv)
        
        train_data = []
        val_data = []
        
        for category, items in categories.items():
            random.shuffle(items)
            split_idx = int(len(items) * (1 - val_split))
            train_data.extend(items[:split_idx])
            val_data.extend(items[split_idx:])
        
        random.shuffle(train_data)
        random.shuffle(val_data)
        
        return train_data, val_data
    
    def create_training_dataset(
        self,
        input_file: Path,
        output_dir: Path,
        validation_split: float = 0.1,
        balance: bool = True,
        deduplicate: bool = True,
        max_per_category: int = 100
    ) -> Dict[str, Any]:
        """
        Create complete training dataset with train/validation split
        
        Returns:
            Dict with counts and file paths
        """
        conversations = []
        
        with open(input_file, 'r') as f:
            for line in f:
                try:
                    conversations.append(json.loads(line))
                    self.stats["loaded"] += 1
                except json.JSONDecodeError:
                    continue
        
        cleaned = [self.clean_conversation(c) for c in conversations]
        self.stats["cleaned"] = len(cleaned)
        
        if deduplicate:
            unique = self.deduplicate(cleaned)
        else:
            unique = cleaned
        
        if balance:
            balanced = self.balance_dataset(unique, max_per_category)
        else:
            balanced = unique
        
        train_data, val_data = self.create_train_val_split(balanced, validation_split)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        train_file = output_dir / "train.jsonl"
        val_file = output_dir / "val.jsonl"
        
        with open(train_file, 'w') as f:
            for item in train_data:
                f.write(json.dumps(item) + '\n')
        
        with open(val_file, 'w') as f:
            for item in val_data:
                f.write(json.dumps(item) + '\n')
        
        self.stats["final"] = len(train_data) + len(val_data)
        
        return {
            "train": len(train_data),
            "val": len(val_data),
            "total": len(train_data) + len(val_data),
            "train_file": str(train_file),
            "val_file": str(val_file),
            "stats": self.stats
        }


class DataAugmenter:
    """
    Create synthetic training examples from existing data
    """
    
    def __init__(self):
        self.synonyms = {
            'list': ['show', 'display', 'get', 'view'],
            'find': ['search', 'locate', 'look for', 'discover'],
            'delete': ['remove', 'erase', 'get rid of', 'trash'],
            'create': ['make', 'generate', 'build', 'write'],
            'open': ['launch', 'start', 'run', 'execute'],
            'run': ['execute', 'start', 'launch', 'invoke'],
            'install': ['add', 'set up', 'configure', 'download'],
            'search': ['find', 'look up', 'query', 'google'],
        }
        
        self.locations = [
            'Downloads', 'Documents', 'Desktop', 'Pictures',
            'Music', 'Videos', 'Projects', 'work', 'school'
        ]
        
        self.file_types = [
            ('*.py', 'Python files'),
            ('*.txt', 'text files'),
            ('*.pdf', 'PDFs'),
            ('*.jpg', 'images'),
            ('*.mp3', 'audio files'),
        ]
    
    def augment_by_paraphrasing(self, conversation: Dict, max_variations: int = 3) -> List[Dict]:
        """Create variations by replacing synonyms"""
        user_msg = conversation['messages'][0]['content']
        assistant_msg = conversation['messages'][1]['content']
        
        variations = []
        used = set()
        
        for word, synonyms in self.synonyms.items():
            if word in user_msg.lower():
                for syn in synonyms[:max_variations]:
                    new_user_msg = re.sub(
                        r'\b' + word + r'\b',
                        syn,
                        user_msg,
                        flags=re.IGNORECASE
                    )
                    
                    if new_user_msg not in used:
                        used.add(new_user_msg)
                        variations.append({
                            "messages": [
                                {"role": "user", "content": new_user_msg},
                                {"role": "assistant", "content": assistant_msg}
                            ],
                            "metadata": {**conversation.get('metadata', {}), "augmented": "paraphrase"},
                            "category": conversation.get('category', 'unknown')
                        })
        
        return variations
    
    def augment_with_context(self, conversation: Dict, max_variations: int = 5) -> List[Dict]:
        """Add contextual variations"""
        user_msg = conversation['messages'][0]['content']
        assistant_msg = conversation['messages'][1]['content']
        
        variations = []
        
        if 'file' in user_msg.lower():
            for loc in self.locations[:max_variations]:
                new_user_msg = f"{user_msg.rstrip('?')} in {loc}?"
                new_assistant_msg = assistant_msg.replace('ls', f'ls ~/{loc}')
                
                variations.append({
                    "messages": [
                        {"role": "user", "content": new_user_msg},
                        {"role": "assistant", "content": new_assistant_msg}
                    ],
                    "metadata": {**conversation.get('metadata', {}), "augmented": "context"},
                    "category": conversation.get('category', 'unknown')
                })
        
        return variations
    
    def augment_with_file_types(self, conversation: Dict) -> List[Dict]:
        """Add file type variations"""
        user_msg = conversation['messages'][0]['content']
        assistant_msg = conversation['messages'][1]['content']
        
        variations = []
        
        if any(kw in user_msg.lower() for kw in ['file', 'find', 'list', 'search']):
            for pattern, description in self.file_types[:3]:
                new_user_msg = f"Find all {description}"
                new_assistant_msg = assistant_msg.replace('ls', f'find . -name "{pattern}"')
                
                variations.append({
                    "messages": [
                        {"role": "user", "content": new_user_msg},
                        {"role": "assistant", "content": new_assistant_msg}
                    ],
                    "metadata": {**conversation.get('metadata', {}), "augmented": "file_type"},
                    "category": "file_ops"
                })
        
        return variations
    
    def augment_dataset(self, conversations: List[Dict], strategies: List[str] = None) -> List[Dict]:
        """
        Apply augmentation strategies to dataset
        
        Args:
            conversations: Original conversations
            strategies: List of strategies to apply (paraphrase, context, file_types)
        """
        if strategies is None:
            strategies = ['paraphrase', 'context']
        
        augmented = list(conversations)
        
        for conv in conversations:
            if 'paraphrase' in strategies:
                augmented.extend(self.augment_by_paraphrasing(conv))
            
            if 'context' in strategies:
                augmented.extend(self.augment_with_context(conv))
            
            if 'file_types' in strategies:
                augmented.extend(self.augment_with_file_types(conv))
        
        random.shuffle(augmented)
        return augmented


class DatasetAnalyzer:
    """Analyze dataset quality and characteristics"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
    
    def analyze(self, train_file: Path = None, val_file: Path = None) -> Dict[str, Any]:
        """Comprehensive dataset analysis"""
        train_file = train_file or self.data_dir / "train.jsonl"
        val_file = val_file or self.data_dir / "val.jsonl"
        
        train_data = self._load_data(train_file)
        val_data = self._load_data(val_file)
        
        return {
            "train": self._analyze_split(train_data, "train"),
            "val": self._analyze_split(val_data, "val"),
            "recommendations": self._generate_recommendations(train_data, val_data)
        }
    
    def _load_data(self, file_path: Path) -> List[Dict]:
        """Load JSONL data"""
        if not file_path.exists():
            return []
        
        data = []
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return data
    
    def _analyze_split(self, data: List[Dict], name: str) -> Dict[str, Any]:
        """Analyze a single data split"""
        if not data:
            return {"error": f"No data in {name}"}
        
        categories = defaultdict(int)
        user_msg_lengths = []
        assistant_msg_lengths = []
        
        for conv in data:
            category = conv.get('category', 'unknown')
            categories[category] += 1
            
            user_msg = conv['messages'][0]['content']
            assistant_msg = conv['messages'][1]['content']
            
            user_msg_lengths.append(len(user_msg.split()))
            assistant_msg_lengths.append(len(assistant_msg.split()))
        
        return {
            "count": len(data),
            "categories": dict(categories),
            "avg_user_msg_length": sum(user_msg_lengths) / len(user_msg_lengths),
            "avg_assistant_msg_length": sum(assistant_msg_lengths) / len(assistant_msg_lengths),
            "category_distribution": {k: v/len(data)*100 for k, v in categories.items()}
        }
    
    def _generate_recommendations(self, train_data: List[Dict], val_data: List[Dict]) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []
        
        total = len(train_data) + len(val_data)
        
        if total < 100:
            recommendations.append(f"Dataset is small ({total} examples). Aim for 500+ for better results.")
        
        if total > 10000:
            recommendations.append(f"Large dataset ({total} examples). Consider balancing categories.")
        
        categories = defaultdict(int)
        for conv in train_data:
            categories[conv.get('category', 'unknown')] += 1
        
        if categories:
            max_cat = max(categories.values())
            min_cat = min(categories.values())
            if max_cat > min_cat * 5:
                recommendations.append("Category imbalance detected. Consider balancing the dataset.")
        
        if not recommendations:
            recommendations.append("Dataset looks good! Ready for fine-tuning.")
        
        return recommendations


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare training dataset")
    parser.add_argument("--input", type=str, default=str(Path.home() / "jarvis/logs/training_ready.jsonl"))
    parser.add_argument("--output", type=str, default=str(Path.home() / "jarvis/finetuning/data"))
    parser.add_argument("--val-split", type=float, default=0.1)
    parser.add_argument("--balance", action="store_true", default=True)
    parser.add_argument("--augment", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_dir = Path(args.output)
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        exit(1)
    
    print("=== Dataset Preparation ===")
    print(f"Input: {input_file}")
    print(f"Output: {output_dir}")
    print()
    
    prep = DatasetPreparator(Path.home() / "jarvis" / "logs")
    result = prep.create_training_dataset(
        input_file=input_file,
        output_dir=output_dir,
        validation_split=args.val_split,
        balance=args.balance
    )
    
    print(f"Created {result['train']} training examples")
    print(f"Created {result['val']} validation examples")
    print(f"Train file: {result['train_file']}")
    print(f"Val file: {result['val_file']}")
    print(f"\nStats: {result['stats']}")
    
    if args.augment:
        print("\n=== Data Augmentation ===")
        augmenter = DataAugmenter()
        
        train_data = []
        with open(result['train_file'], 'r') as f:
            for line in f:
                train_data.append(json.loads(line))
        
        augmented = augmenter.augment_dataset(train_data)
        
        with open(result['train_file'], 'w') as f:
            for item in augmented:
                f.write(json.dumps(item) + '\n')
        
        print(f"Augmented dataset: {len(augmented)} examples (was {len(train_data)})")
    
    if args.analyze:
        print("\n=== Dataset Analysis ===")
        analyzer = DatasetAnalyzer(output_dir)
        analysis = analyzer.analyze()
        print(json.dumps(analysis, indent=2))
