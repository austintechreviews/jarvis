# JARVIS Fine-Tuning Framework

A comprehensive framework for fine-tuning JARVIS on your personal usage patterns, commands, and preferences.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Data Collection](#data-collection)
- [Dataset Preparation](#dataset-preparation)
- [Fine-Tuning Methods](#fine-tuning-methods)
- [Evaluation](#evaluation)
- [Deployment](#deployment)
- [Continuous Learning](#continuous-learning)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

The JARVIS Fine-Tuning Framework enables you to create a personalized AI assistant that understands your specific workflow, terminology, and preferences. By fine-tuning on your actual usage data, JARVIS becomes more accurate and efficient over time.

### Key Features

- **Automatic Data Collection**: Logs all interactions transparently
- **Smart Data Cleaning**: Removes sensitive information automatically
- **Multiple Fine-Tuning Methods**: Unsloth (fast), Transformers (standard), LoRA (efficient)
- **Comprehensive Evaluation**: Automated metrics and A/B testing
- **Model Management**: Version control, rollback, and registry
- **Continuous Learning**: Incremental updates as you use JARVIS

### Expected Improvements

| Metric | Base Model | Fine-Tuned | Improvement |
|--------|------------|------------|-------------|
| Command Accuracy | ~70% | ~90% | +20% |
| Path Recognition | ~50% | ~95% | +45% |
| Response Relevance | ~65% | ~88% | +23% |
| Safety Compliance | ~95% | ~98% | +3% |

---

## Quick Start

### 1. Enable Data Collection (Automatic)

Data collection is already integrated into JARVIS. Just use JARVIS normally:

```python
# In your JARVIS session
> stats  # Check collection progress
```

### 2. Collect Data (2-4 weeks)

Use JARVIS for your daily tasks. Aim for 100+ interactions minimum.

### 3. Prepare Dataset

```bash
cd ~/jarvis/finetuning
python tools/prepare_training_data.py
```

### 4. Fine-Tune

```bash
# Install dependencies
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
pip install --no-deps xformers trl peft accelerate bitsandbytes

# Run fine-tuning
python tools/finetune_unsloth.py
```

### 5. Deploy

```bash
python tools/deploy_model.py --gguf ~/jarvis/finetuning/models/jarvis-finetuned-v1/gguf/model-q4_k_m.gguf
```

### 6. Activate

```python
from finetuning import switch_to_finetuned_model
switch_to_finetuned_model("jarvis-finetuned:v1")
```

---

## Architecture

```
finetuning/
├── __init__.py              # Package exports
├── integration.py            # Main JARVIS integration
├── data_collector.py         # Data collection module
├── tools/
│   ├── prepare_training_data.py  # Dataset preparation
│   ├── finetune_unsloth.py       # Fine-tuning (multiple methods)
│   ├── evaluate_model.py         # Evaluation framework
│   └── deploy_model.py           # Ollama deployment
├── tests/
│   └── test_finetuning.py        # Comprehensive tests
├── data/                     # Training datasets
├── models/                   # Fine-tuned models
├── evals/                    # Evaluation results
└── run_finetuning.sh         # Workflow automation
```

### Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   JARVIS    │────▶│   Data       │────▶│   Export    │
│  (Runtime)  │     │  Collector   │     │  for Train  │
└─────────────┘     └──────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Deploy    │◀────│   Fine-Tune  │◀────│   Prepare   │
│   to Ollama │     │   Model      │     │   Dataset   │
└─────────────┘     └──────────────┘     └─────────────┘
```

---

## Data Collection

### Automatic Logging

All interactions are logged to:
- `~/jarvis/logs/conversations.jsonl` - Full conversation history
- `~/jarvis/logs/user_feedback.jsonl` - User corrections
- `~/jarvis/logs/successful_patterns.jsonl` - Successful patterns

### Manual Logging

```python
from finetuning import FineTuningIntegration

finetuning = FineTuningIntegration(enabled=True)

# Log interaction
finetuning.on_interaction(
    user_input="List Python files",
    assistant_response="find . -name '*.py'",
    tool_used="terminal",
    success=True,
    execution_time=0.5
)

# Log correction
finetuning.on_correction(
    original="Delete temp files",
    attempt="rm -rf /tmp",
    correction="rm ~/project/tmp/*"
)
```

### Data Quality

The framework automatically:
- Removes sensitive data (passwords, API keys, emails)
- Normalizes paths (replaces `/home/user` with `~`)
- Deduplicates similar interactions
- Categorizes by type (file_ops, web_search, browser, etc.)

---

## Dataset Preparation

### Basic Preparation

```bash
python tools/prepare_training_data.py \
    --input ~/jarvis/logs/training_ready.jsonl \
    --output ~/jarvis/finetuning/data \
    --val-split 0.1
```

### With Augmentation

```bash
python tools/prepare_training_data.py \
    --input ~/jarvis/logs/training_ready.jsonl \
    --output ~/jarvis/finetuning/data \
    --augment \
    --analyze
```

### Programmatic Usage

```python
from finetuning.tools.prepare_training_data import (
    DatasetPreparator,
    DataAugmenter,
    DatasetAnalyzer
)

# Prepare
prep = DatasetPreparator(log_dir)
result = prep.create_training_dataset(
    input_file=input_path,
    output_dir=output_dir,
    validation_split=0.1,
    balance=True
)

# Augment
augmenter = DataAugmenter()
augmented = augmenter.augment_dataset(
    conversations,
    strategies=['paraphrase', 'context']
)

# Analyze
analyzer = DatasetAnalyzer(output_dir)
analysis = analyzer.analyze()
print(analysis['recommendations'])
```

---

## Fine-Tuning Methods

### Method Comparison

| Method | Speed | VRAM | Quality | Best For |
|--------|-------|------|---------|----------|
| Unsloth | ⚡⚡⚡ | Low | High | Quick iteration |
| Transformers | ⚡⚡ | Medium | High | Research |
| LoRA | ⚡⚡⚡ | Low | Medium-High | Multiple adapters |

### Unsloth (Recommended)

```bash
python tools/finetune_unsloth.py \
    --method unsloth \
    --train data/train.jsonl \
    --val data/val.jsonl \
    --output models/jarvis-finetuned-v1 \
    --epochs 3 \
    --batch-size 2 \
    --lr 2e-4
```

### Transformers

```bash
python tools/finetune_unsloth.py \
    --method transformers \
    --train data/train.jsonl \
    --val data/val.jsonl \
    --output models/jarvis-ft-standard \
    --epochs 3
```

### LoRA (Multiple Adapters)

```python
from finetuning.tools.finetune_unsloth import LoRAFineTuner, FineTuningConfig

config = FineTuningConfig(
    model_name="Qwen/Qwen2.5-Coder-3B-Instruct",
    num_epochs=2,
    r=16
)

finetuner = LoRAFineTuner(config, adapter_name="file_ops")
finetuner.load_model()

# Add task-specific adapters
finetuner.add_adapter("web_search", task_type="search")
finetuner.add_adapter("browser", task_type="automation")

# Train each adapter
finetuner.prepare_dataset("file_ops_train.jsonl", "file_ops_val.jsonl")
finetuner.train()
finetuner.save_model("models/jarvis-lora")
```

---

## Evaluation

### Automated Evaluation

```bash
python tools/evaluate_model.py \
    --test-file data/val.jsonl \
    --output evals/results.json \
    --models qwen2.5-coder:3b jarvis-finetuned:v1
```

### A/B Testing

```bash
python tools/evaluate_model.py \
    --ab-test \
    "List files in Downloads" \
    "Search for Python tutorials" \
    "Open Firefox"
```

### Programmatic Evaluation

```python
from finetuning.tools.evaluate_model import ModelEvaluator

evaluator = ModelEvaluator(
    base_model="qwen2.5-coder:3b",
    finetuned_model="jarvis-finetuned:v1"
)

# Compare models
reports = evaluator.compare_models(
    test_file=Path("data/val.jsonl"),
    models=["qwen2.5-coder:3b", "jarvis-finetuned:v1"]
)

for model, report in reports.items():
    print(f"{model}: {report.overall_score:.2%}")
    print(f"  Recommendations: {report.recommendations}")
```

### Evaluation Metrics

- **Exact Match**: Perfect output match
- **Keyword Overlap**: Jaccard similarity
- **Command Correctness**: Bash command accuracy
- **Path Accuracy**: Path reference correctness
- **Safety Compliance**: Dangerous command detection
- **Format Correctness**: Output format adherence
- **Conciseness**: Response brevity score

---

## Deployment

### Deploy to Ollama

```bash
python tools/deploy_model.py \
    --gguf models/jarvis-finetuned-v1/gguf/model-q4_k_m.gguf \
    --name jarvis-finetuned \
    --version v1
```

### Model Registry

```python
from finetuning.tools.deploy_model import ModelDeployer

deployer = ModelDeployer()

# List all models
models = deployer.registry.list_models()
for m in models:
    print(f"{m.name}:{m.version} - Active: {m.is_active}")

# Set active model
deployer.registry.set_active("jarvis-finetuned", "v1")

# Get active model
active = deployer.registry.get_active_model()
```

### Switch Models in JARVIS

```python
from finetuning import switch_to_finetuned_model, switch_to_base_model

# Use fine-tuned model
switch_to_finetuned_model("jarvis-finetuned:v1")

# Revert to base model
switch_to_base_model("qwen2.5-coder:3b")
```

---

## Continuous Learning

### Incremental Fine-Tuning

```python
from finetuning.tools.incremental_learning import IncrementalLearner

learner = IncrementalLearner(log_dir=Path.home() / "jarvis" / "logs")

# Check if ready for update
if learner.should_finetune(min_new_examples=50, days_since_last=7):
    learner.run_incremental_finetune(
        base_model="jarvis-finetuned:v1",
        output_version="v2"
    )
```

### Automated Updates (Cron)

```bash
# Add to crontab
0 2 * * 0 /path/to/jarvis/venv/bin/python \
    /path/to/jarvis/finetuning/tools/incremental_learning.py \
    >> /path/to/jarvis/logs/finetune_cron.log 2>&1
```

---

## API Reference

### DataCollector

```python
class DataCollector:
    def log_interaction(user_input, assistant_response, ...) -> str
    def log_user_correction(original, attempt, correction, ...) -> str
    def log_successful_pattern(command, execution, outcome, ...) -> str
    def export_for_training(output_file, ...) -> Tuple[int, Dict]
    def get_stats() -> Dict[str, int]
    def get_quality_report() -> Dict[str, Any]
```

### FineTuningIntegration

```python
class FineTuningIntegration:
    def on_interaction(user_input, assistant_response, ...)
    def on_correction(original, attempt, correction, ...)
    def enable()
    def disable()
    def stats() -> Dict
```

### DatasetPreparator

```python
class DatasetPreparator:
    def clean_conversation(conv) -> Dict
    def deduplicate(conversations) -> List[Dict]
    def balance_dataset(conversations, ...) -> List[Dict]
    def create_training_dataset(input_file, output_dir, ...) -> Dict
```

---

## Testing

### Run All Tests

```bash
cd ~/jarvis
python -m pytest finetuning/tests/ -v
```

### Run Specific Tests

```bash
# Data collector tests
python -m pytest finetuning/tests/test_finetuning.py::TestDataCollector -v

# Integration tests
python -m pytest finetuning/tests/test_finetuning.py::TestIntegration -v
```

### Test Coverage

```bash
python -m pytest finetuning/tests/ --cov=finetuning --cov-report=html
```

---

## Troubleshooting

### Out of Memory

```python
# Reduce batch size and use gradient accumulation
python tools/finetune_unsloth.py --batch-size 1 --gradient-accumulation 8

# Use smaller model
--model unsloth/qwen2.5-coder-1.5b-instruct-bnb-4bit
```

### Model Overfitting

```python
# Add dropout and reduce epochs
python tools/finetune_unsloth.py \
    --epochs 1 \
    --lora-dropout 0.1
```

### Poor Performance

1. Check data quality: `python tools/prepare_training_data.py --analyze`
2. Add more diverse examples
3. Include correction data
4. Balance categories

### Deployment Fails

```bash
# Verify GGUF file exists
ls -lh models/jarvis-finetuned-v1/gguf/

# Check Ollama is running
ollama list

# Re-create Modelfile
python tools/deploy_model.py --gguf <path> --name jarvis-finetuned --version v1
```

---

## License

MIT License - See LICENSE file for details.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python -m pytest finetuning/tests/ -v`
5. Submit a pull request
