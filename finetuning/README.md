# JARVIS Fine-Tuning Framework

Personalize your JARVIS assistant through fine-tuning on your usage patterns.

## Quick Start

### 1. Enable Data Collection

Add to your main JARVIS code:

```python
from finetuning import FineTuningIntegration

# Initialize
finetuning = FineTuningIntegration(enabled=True)

# After each interaction, log it
finetuning.on_interaction(
    user_input=user_input,
    assistant_response=response,
    tool_used="terminal",  # or "browser", "file", etc.
    success=True
)

# When user corrects JARVIS
finetuning.on_correction(
    original=user_command,
    attempt=jarvis_attempt,
    correction=user_correction
)
```

### 2. Collect Data (2-4 weeks)

Use JARVIS normally. Data is automatically logged to:
- `~/jarvis/logs/conversations.jsonl`

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
# Convert to Ollama format
python tools/deploy_model.py --gguf ~/jarvis/finetuning/models/jarvis-finetuned-v1/gguf/model-q4_k_m.gguf

# Test
ollama run jarvis-finetuned:v1
```

### 6. Activate in JARVIS

```python
from finetuning import switch_to_finetuned_model
switch_to_finetuned_model("jarvis-finetuned:v1")
```

## Directory Structure

```
finetuning/
├── __init__.py              # Package exports
├── integration.py            # Main JARVIS integration
├── data_collector.py         # Data collection module
├── tools/
│   ├── prepare_training_data.py  # Dataset preparation
│   ├── finetune_unsloth.py       # Fine-tuning script
│   ├── evaluate_model.py         # Evaluation tools
│   └── deploy_model.py           # Deployment script
├── data/                     # Training datasets
├── models/                   # Fine-tuned models
└── evals/                    # Evaluation results
```

## Commands

### Check Collection Stats

```bash
python -m finetuning.data_collector
```

### Evaluate Model

```bash
python tools/evaluate_model.py --test-file data/dataset_val.jsonl
```

### A/B Test

```bash
python tools/evaluate_model.py --ab-test "list files" "search for Python tips"
```

## Requirements

- **GPU**: NVIDIA with 8GB+ VRAM recommended
- **Storage**: ~10GB for models and datasets
- **RAM**: 16GB+ recommended

## Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| Data Collection | 2-4 weeks | Use JARVIS normally |
| Dataset Prep | 1 day | Clean and format |
| Fine-Tuning | 4-12 hours | Train model |
| Evaluation | 1 day | Test and validate |
| Deployment | 1 hour | Deploy to Ollama |

## Expected Improvements

- **30-50%** better command accuracy
- **60-80%** reduction in path hallucinations
- **Personalized** to your workflow

## Troubleshooting

### Out of Memory

Reduce batch size and use gradient accumulation:
```bash
python tools/finetune_unsloth.py --batch-size 1
```

### Model Overfitting

Use fewer epochs:
```bash
python tools/finetune_unsloth.py --epochs 1
```

## License

MIT
