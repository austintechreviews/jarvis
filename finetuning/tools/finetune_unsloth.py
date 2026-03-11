"""
Comprehensive Fine-Tuning Framework for JARVIS
Multiple methods: Unsloth (fast), Transformers (standard), LoRA (efficient)
"""

import json
import torch
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class FineTuningConfig:
    """Configuration for fine-tuning"""
    model_name: str = "unsloth/qwen2.5-coder-3b-instruct-bnb-4bit"
    max_seq_length: int = 2048
    load_in_4bit: bool = True
    r: int = 16
    lora_alpha: int = 16
    lora_dropout: float = 0.0
    num_epochs: int = 3
    batch_size: int = 2
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    warmup_steps: int = 10
    weight_decay: float = 0.01
    output_dir: str = "./jarvis-finetuned"
    quantization: str = "q4_k_m"
    seed: int = 3407
    target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj",
        "o_proj", "gate_proj", "up_proj", "down_proj"
    ])


class BaseFineTuner(ABC):
    """Abstract base class for fine-tuning implementations"""
    
    def __init__(self, config: FineTuningConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.train_dataset = None
        self.val_dataset = None
        self.trainer = None
    
    @abstractmethod
    def load_model(self):
        """Load the base model"""
        pass
    
    @abstractmethod
    def prepare_dataset(self, train_file: str, val_file: str):
        """Prepare training and validation datasets"""
        pass
    
    @abstractmethod
    def train(self) -> Dict[str, Any]:
        """Run fine-tuning"""
        pass
    
    @abstractmethod
    def save_model(self, output_dir: str):
        """Save the fine-tuned model"""
        pass
    
    def get_memory_stats(self) -> Dict[str, float]:
        """Get GPU memory statistics"""
        if not torch.cuda.is_available():
            return {"available": False}
        
        return {
            "available": True,
            "gpu_name": torch.cuda.get_device_properties(0).name,
            "total_memory_gb": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2),
            "reserved_gb": round(torch.cuda.max_memory_reserved() / 1024**3, 2),
            "allocated_gb": round(torch.cuda.max_memory_allocated() / 1024**3, 2)
        }


class UnslothFineTuner(BaseFineTuner):
    """
    Fine-tune using Unsloth - fastest method with optimized memory usage
    Best for: Quick iteration, limited GPU resources
    """
    
    def load_model(self):
        """Load model with Unsloth optimizations"""
        try:
            from unsloth import FastLanguageModel
        except ImportError:
            raise ImportError(
                "Unsloth not installed. Run:\n"
                'pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"\n'
                "pip install --no-deps xformers trl peft accelerate bitsandbytes"
            )
        
        self.FastLanguageModel = FastLanguageModel
        
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.config.model_name,
            max_seq_length=self.config.max_seq_length,
            dtype=None,
            load_in_4bit=self.config.load_in_4bit,
        )
        
        self.model = FastLanguageModel.get_peft_model(
            self.model,
            r=self.config.r,
            target_modules=self.config.target_modules,
            lora_alpha=self.config.lora_alpha,
            lora_dropout=self.config.lora_dropout,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=self.config.seed,
            use_rslora=False,
            loftq_config=None,
        )
        
        print(f"✓ Model loaded: {self.config.model_name}")
        print(f"✓ Memory stats: {self.get_memory_stats()}")
    
    def prepare_dataset(self, train_file: str, val_file: str):
        """Load and prepare dataset"""
        from datasets import load_dataset
        
        train_dataset = load_dataset('json', data_files=train_file, split='train')
        val_dataset = load_dataset('json', data_files=val_file, split='train')
        
        def format_prompts(examples):
            texts = []
            for messages in examples['messages']:
                text = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=False
                )
                texts.append(text)
            return {"text": texts}
        
        self.train_dataset = train_dataset.map(format_prompts, batched=True)
        self.val_dataset = val_dataset.map(format_prompts, batched=True)
        
        print(f"✓ Training samples: {len(self.train_dataset)}")
        print(f"✓ Validation samples: {len(self.val_dataset)}")
    
    def train(self) -> Dict[str, Any]:
        """Run fine-tuning"""
        from trl import SFTTrainer
        from transformers import TrainingArguments
        
        trainer = SFTTrainer(
            model=self.model,
            tokenizer=self.tokenizer,
            train_dataset=self.train_dataset,
            eval_dataset=self.val_dataset,
            dataset_text_field="text",
            max_seq_length=self.config.max_seq_length,
            dataset_num_proc=2,
            packing=False,
            args=TrainingArguments(
                per_device_train_batch_size=self.config.batch_size,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                warmup_steps=self.config.warmup_steps,
                num_train_epochs=self.config.num_epochs,
                learning_rate=self.config.learning_rate,
                fp16=not torch.cuda.is_bf16_supported(),
                bf16=torch.cuda.is_bf16_supported(),
                logging_steps=10,
                optim="adamw_8bit",
                weight_decay=self.config.weight_decay,
                lr_scheduler_type="linear",
                seed=self.config.seed,
                output_dir=self.config.output_dir,
                report_to="none",
                save_strategy="epoch",
                evaluation_strategy="epoch",
                save_total_limit=2,
            ),
        )
        
        self.trainer = trainer
        
        print("\n=== Starting Training ===")
        print(f"GPU: {torch.cuda.get_device_properties(0).name if torch.cuda.is_available() else 'CPU'}")
        print(f"Epochs: {self.config.num_epochs}")
        print(f"Batch size: {self.config.batch_size}")
        print(f"Learning rate: {self.config.learning_rate}")
        print()
        
        train_result = trainer.train()
        
        metrics = train_result.metrics
        metrics["train_samples"] = len(self.train_dataset)
        metrics["val_samples"] = len(self.val_dataset)
        
        print("\n=== Training Complete ===")
        print(f"Train loss: {metrics.get('train_loss', 'N/A')}")
        print(f"Eval loss: {metrics.get('eval_loss', 'N/A')}")
        
        return metrics
    
    def save_model(self, output_dir: str = None):
        """Save fine-tuned model"""
        output_dir = output_dir or self.config.output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        gguf_dir = Path(output_dir) / "gguf"
        gguf_dir.mkdir(parents=True, exist_ok=True)
        
        self.model.save_pretrained_gguf(
            str(gguf_dir),
            self.tokenizer,
            quantization_method=self.config.quantization
        )
        
        print(f"\n✓ Model saved to {output_dir}")
        print(f"✓ GGUF model saved to {gguf_dir}")


class TransformersFineTuner(BaseFineTuner):
    """
    Fine-tune using standard HuggingFace Transformers
    Best for: Maximum control, research purposes
    """
    
    def load_model(self):
        """Load model with standard transformers"""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        
        print(f"Loading model: {self.config.model_name.replace('unsloth/', '')}...")
        
        model_name = self.config.model_name.replace('unsloth/', '').replace('-bnb-4bit', '')
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            load_in_8bit=True,
            device_map="auto",
            torch_dtype=torch.float16
        )
        
        self.model = prepare_model_for_kbit_training(self.model)
        
        lora_config = LoraConfig(
            r=self.config.r,
            lora_alpha=self.config.lora_alpha,
            target_modules=self.config.target_modules[:2],
            lora_dropout=self.config.lora_dropout,
            bias="none",
            task_type="CAUSAL_LM"
        )
        
        self.model = get_peft_model(self.model, lora_config)
        
        print(f"✓ Model loaded with LoRA")
        print(f"✓ Trainable parameters: {self.model.get_nb_trainable_parameters()[0]:,}")
    
    def prepare_dataset(self, train_file: str, val_file: str):
        """Prepare datasets"""
        from datasets import load_dataset
        from transformers import DataCollatorForLanguageModeling
        
        train_dataset = load_dataset('json', data_files=train_file, split='train')
        val_dataset = load_dataset('json', data_files=val_file, split='train')
        
        def tokenize_function(examples):
            texts = []
            for messages in examples['messages']:
                text = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False
                )
                texts.append(text)
            
            return self.tokenizer(
                texts,
                padding="max_length",
                truncation=True,
                max_length=512
            )
        
        self.train_dataset = train_dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=train_dataset.column_names
        )
        
        self.val_dataset = val_dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=val_dataset.column_names
        )
        
        self.data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )
        
        print(f"✓ Training samples: {len(self.train_dataset)}")
        print(f"✓ Validation samples: {len(self.val_dataset)}")
    
    def train(self) -> Dict[str, Any]:
        """Run training"""
        from transformers import Trainer, TrainingArguments
        
        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.num_epochs,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            eval_strategy="epoch",
            save_strategy="epoch",
            learning_rate=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
            fp16=True,
            logging_steps=10,
            seed=self.config.seed,
            save_total_limit=2,
        )
        
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=self.train_dataset,
            eval_dataset=self.val_dataset,
            data_collator=self.data_collator
        )
        
        print("\n=== Starting Training ===")
        train_result = self.trainer.train()
        
        return train_result.metrics
    
    def save_model(self, output_dir: str = None):
        """Save model"""
        output_dir = output_dir or self.config.output_dir
        self.trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        print(f"✓ Model saved to {output_dir}")


class LoRAFineTuner(BaseFineTuner):
    """
    Fine-tune using LoRA with configurable adapters
    Best for: Multiple task-specific adapters, memory efficiency
    """
    
    def __init__(self, config: FineTuningConfig, adapter_name: str = "default"):
        super().__init__(config)
        self.adapter_name = adapter_name
        self.adapters = {}
    
    def load_model(self):
        """Load base model for LoRA"""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import LoraConfig, get_peft_model
        
        model_name = self.config.model_name.replace('unsloth/', '').replace('-bnb-4bit', '')
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        lora_config = LoraConfig(
            r=self.config.r,
            lora_alpha=self.config.lora_alpha,
            target_modules=self.config.target_modules,
            lora_dropout=self.config.lora_dropout,
            bias="none",
            task_type="CAUSAL_LM"
        )
        
        self.model = get_peft_model(self.model, lora_config, adapter_name=self.adapter_name)
        
        print(f"✓ Base model loaded: {model_name}")
        print(f"✓ LoRA adapter '{self.adapter_name}' configured")
    
    def add_adapter(self, adapter_name: str, task_type: str = "default"):
        """Add a new LoRA adapter for a specific task"""
        from peft import LoraConfig
        
        lora_config = LoraConfig(
            r=self.config.r,
            lora_alpha=self.config.lora_alpha,
            target_modules=self.config.target_modules,
            lora_dropout=self.config.lora_dropout,
            bias="none",
            task_type="CAUSAL_LM"
        )
        
        self.model.add_adapter(lora_config, adapter_name=adapter_name)
        self.adapters[adapter_name] = task_type
        
        print(f"✓ Added adapter '{adapter_name}' for task: {task_type}")
    
    def set_active_adapter(self, adapter_name: str):
        """Set the active adapter"""
        if adapter_name in self.adapters or adapter_name == self.adapter_name:
            self.model.set_adapter(adapter_name)
            print(f"✓ Active adapter: {adapter_name}")
        else:
            print(f"✗ Adapter '{adapter_name}' not found")
    
    def prepare_dataset(self, train_file: str, val_file: str):
        """Prepare dataset"""
        from datasets import load_dataset
        
        self.train_dataset = load_dataset('json', data_files=train_file, split='train')
        self.val_dataset = load_dataset('json', data_files=val_file, split='train')
        
        def format_prompts(examples):
            texts = []
            for messages in examples['messages']:
                text = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=False
                )
                texts.append(text)
            return {"text": texts}
        
        self.train_dataset = self.train_dataset.map(format_prompts, batched=True)
        self.val_dataset = self.val_dataset.map(format_prompts, batched=True)
    
    def train(self) -> Dict[str, Any]:
        """Train with active adapter"""
        from trl import SFTTrainer
        from transformers import TrainingArguments
        
        trainer = SFTTrainer(
            model=self.model,
            tokenizer=self.tokenizer,
            train_dataset=self.train_dataset,
            eval_dataset=self.val_dataset,
            dataset_text_field="text",
            max_seq_length=self.config.max_seq_length,
            dataset_num_proc=2,
            packing=False,
            args=TrainingArguments(
                per_device_train_batch_size=self.config.batch_size,
                gradient_accumulation_steps=self.config.gradient_accumulation_steps,
                warmup_steps=self.config.warmup_steps,
                num_train_epochs=self.config.num_epochs,
                learning_rate=self.config.learning_rate,
                fp16=True,
                logging_steps=10,
                optim="adamw_8bit",
                weight_decay=self.config.weight_decay,
                lr_scheduler_type="linear",
                seed=self.config.seed,
                output_dir=self.config.output_dir,
                report_to="none",
                save_strategy="epoch",
                evaluation_strategy="epoch",
            ),
        )
        
        print(f"\n=== Training adapter '{self.adapter_name}' ===")
        train_result = trainer.train()
        
        return train_result.metrics
    
    def save_model(self, output_dir: str = None):
        """Save all adapters"""
        output_dir = output_dir or self.config.output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        adapters_dir = Path(output_dir) / "adapters"
        adapters_dir.mkdir(parents=True, exist_ok=True)
        
        for adapter_name in list(self.adapters.keys()) + [self.adapter_name]:
            adapter_path = adapters_dir / adapter_name
            adapter_path.mkdir(parents=True, exist_ok=True)
            self.model.set_adapter(adapter_name)
            self.model.save_pretrained(str(adapter_path))
        
        print(f"✓ Model and adapters saved to {output_dir}")


def get_finetuner(method: str = "unsloth", config: FineTuningConfig = None) -> BaseFineTuner:
    """
    Factory function to get the appropriate fine-tuner
    
    Args:
        method: "unsloth", "transformers", or "lora"
        config: Fine-tuning configuration
    """
    config = config or FineTuningConfig()
    
    if method == "unsloth":
        return UnslothFineTuner(config)
    elif method == "transformers":
        return TransformersFineTuner(config)
    elif method == "lora":
        return LoRAFineTuner(config)
    else:
        raise ValueError(f"Unknown method: {method}. Choose from: unsloth, transformers, lora")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fine-tune JARVIS model")
    parser.add_argument("--method", type=str, default="unsloth",
                       choices=["unsloth", "transformers", "lora"])
    parser.add_argument("--train", type=str, default=str(Path.home() / "jarvis/finetuning/data/train.jsonl"))
    parser.add_argument("--val", type=str, default=str(Path.home() / "jarvis/finetuning/data/val.jsonl"))
    parser.add_argument("--output", type=str, default=str(Path.home() / "jarvis/finetuning/models/jarvis-finetuned-v1"))
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--model", type=str, default="unsloth/qwen2.5-coder-3b-instruct-bnb-4bit")
    
    args = parser.parse_args()
    
    config = FineTuningConfig(
        model_name=args.model,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        output_dir=args.output
    )
    
    print("=== JARVIS Fine-Tuning ===")
    print(f"Method: {args.method}")
    print(f"Model: {config.model_name}")
    print(f"Output: {config.output_dir}")
    print(f"Epochs: {config.num_epochs}")
    print(f"Batch size: {config.batch_size}")
    print(f"Learning rate: {config.learning_rate}")
    print()
    
    finetuner = get_finetuner(args.method, config)
    finetuner.load_model()
    finetuner.prepare_dataset(args.train, args.val)
    metrics = finetuner.train()
    finetuner.save_model()
    
    print("\n=== Fine-Tuning Complete ===")
    print(f"Metrics: {json.dumps(metrics, indent=2)}")
