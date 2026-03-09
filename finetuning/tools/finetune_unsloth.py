"""
JARVIS Fine-Tuning using Unsloth
Fast and memory-efficient fine-tuning for Qwen2.5-Coder
"""

from pathlib import Path
import torch
from typing import Optional


class JARVISFineTuner:
    """
    Fine-tune JARVIS using Unsloth for maximum efficiency
    """
    
    def __init__(
        self,
        model_name: str = "unsloth/qwen2.5-coder-3b-instruct-bnb-4bit",
        max_seq_length: int = 2048,
        load_in_4bit: bool = True
    ):
        """
        Initialize fine-tuning setup
        
        Args:
            model_name: Base model to fine-tune
            max_seq_length: Maximum sequence length
            load_in_4bit: Use 4-bit quantization (saves memory)
        """
        try:
            from unsloth import FastLanguageModel
        except ImportError:
            print("Error: Unsloth not installed. Run:")
            print('pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"')
            print("pip install --no-deps xformers trl peft accelerate bitsandbytes")
            raise
        
        self.max_seq_length = max_seq_length
        self.FastLanguageModel = FastLanguageModel
        
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=model_name,
            max_seq_length=max_seq_length,
            dtype=None,
            load_in_4bit=load_in_4bit,
        )
        
        self.model = FastLanguageModel.get_peft_model(
            self.model,
            r=16,
            target_modules=[
                "q_proj", "k_proj", "v_proj",
                "o_proj", "gate_proj", "up_proj", "down_proj"
            ],
            lora_alpha=16,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=3407,
            use_rslora=False,
            loftq_config=None,
        )
    
    def prepare_dataset(self, train_file: str, val_file: str):
        """
        Load and prepare dataset
        
        Args:
            train_file: Path to training JSONL
            val_file: Path to validation JSONL
        """
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
    
    def train(
        self,
        output_dir: str = "./jarvis-finetuned",
        num_epochs: int = 3,
        batch_size: int = 2,
        learning_rate: float = 2e-4,
        warmup_steps: int = 10,
        logging_steps: int = 10
    ):
        """
        Run fine-tuning
        
        Args:
            output_dir: Where to save the model
            num_epochs: Number of training epochs
            batch_size: Batch size per device
            learning_rate: Learning rate
            warmup_steps: Warmup steps
            logging_steps: Log every N steps
        """
        from trl import SFTTrainer
        from transformers import TrainingArguments
        
        trainer = SFTTrainer(
            model=self.model,
            tokenizer=self.tokenizer,
            train_dataset=self.train_dataset,
            eval_dataset=self.val_dataset,
            dataset_text_field="text",
            max_seq_length=self.max_seq_length,
            dataset_num_proc=2,
            packing=False,
            args=TrainingArguments(
                per_device_train_batch_size=batch_size,
                gradient_accumulation_steps=4,
                warmup_steps=warmup_steps,
                num_train_epochs=num_epochs,
                learning_rate=learning_rate,
                fp16=not torch.cuda.is_bf16_supported(),
                bf16=torch.cuda.is_bf16_supported(),
                logging_steps=logging_steps,
                optim="adamw_8bit",
                weight_decay=0.01,
                lr_scheduler_type="linear",
                seed=3407,
                output_dir=output_dir,
                report_to="none",
                save_strategy="epoch",
                evaluation_strategy="epoch",
            ),
        )
        
        gpu_stats = torch.cuda.get_device_properties(0)
        start_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
        max_memory = round(gpu_stats.total_memory / 1024 / 1024 / 1024, 3)
        
        print(f"GPU = {gpu_stats.name}. Max memory = {max_memory} GB.")
        print(f"{start_memory} GB of memory reserved before training.")
        
        trainer_stats = trainer.train()
        
        used_memory = round(torch.cuda.max_memory_reserved() / 1024 / 1024 / 1024, 3)
        used_memory_for_training = round(used_memory - start_memory, 3)
        used_percentage = round(used_memory / max_memory * 100, 3)
        
        print(f"{used_memory} GB of memory used for training ({used_percentage}%).")
        print(f"Peak reserved memory = {used_memory_for_training} GB.")
        
        return trainer_stats
    
    def save_model(self, output_dir: str, quantization: str = "q4_k_m"):
        """
        Save fine-tuned model
        
        Args:
            output_dir: Output directory
            quantization: Quantization method (q4_k_m, q8_0, f16)
        """
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        gguf_dir = Path(output_dir) / "gguf"
        gguf_dir.mkdir(parents=True, exist_ok=True)
        
        self.model.save_pretrained_gguf(
            str(gguf_dir),
            self.tokenizer,
            quantization_method=quantization
        )
        
        print(f"Model saved to {output_dir}")
        print(f"GGUF model saved to {gguf_dir}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fine-tune JARVIS model")
    parser.add_argument(
        "--train", 
        type=str,
        default=str(Path.home() / "jarvis/finetuning/data/dataset_train.jsonl"),
        help="Training data file"
    )
    parser.add_argument(
        "--val",
        type=str,
        default=str(Path.home() / "jarvis/finetuning/data/dataset_val.jsonl"),
        help="Validation data file"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path.home() / "jarvis/finetuning/models/jarvis-finetuned-v1"),
        help="Output directory"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of epochs"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2,
        help="Batch size"
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=2e-4,
        help="Learning rate"
    )
    
    args = parser.parse_args()
    
    print("=== JARVIS Fine-Tuning ===")
    print(f"Training data: {args.train}")
    print(f"Validation data: {args.val}")
    print(f"Output: {args.output}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.lr}")
    print()
    
    finetuner = JARVISFineTuner(
        model_name="unsloth/qwen2.5-coder-3b-instruct-bnb-4bit",
        max_seq_length=2048,
        load_in_4bit=True
    )
    
    finetuner.prepare_dataset(args.train, args.val)
    
    stats = finetuner.train(
        output_dir=args.output,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr
    )
    
    finetuner.save_model(args.output, quantization="q4_k_m")
    
    print("\nFine-tuning complete!")
