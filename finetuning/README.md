# JARVIS Fine-Tuning Framework

Personalize your JARVIS assistant through fine-tuning on your usage patterns.

## Quick Start

### 1. Check Data Collection Status

```bash
cd ~/jarvis/finetuning
./run_finetuning.sh collect
```

### 2. Prepare Dataset (after 100+ interactions)

```bash
./run_finetuning.sh prepare
```

### 3. Fine-Tune Model

```bash
./run_finetuning.sh train
```

### 4. Deploy to Ollama

```bash
./run_finetuning.sh deploy
```

### 5. Activate in JARVIS

```python
from finetuning import switch_to_finetuned_model
switch_to_finetuned_model("jarvis-finetuned:v1")
```

## Commands

| Command | Description |
|---------|-------------|
| `collect` | Show data collection status |
| `prepare` | Prepare training dataset |
| `train` | Run fine-tuning |
| `deploy` | Deploy to Ollama |
| `evaluate` | Evaluate fine-tuned model |
| `ab-test` | A/B test models |
| `clean` | Remove fine-tuning artifacts |

## Directory Structure

```
finetuning/
├── __init__.py              # Package exports
├── integration.py            # JARVIS integration
├── data_collector.py         # Data collection
├── tools/
│   ├── prepare_training_data.py
│   ├── finetune_unsloth.py
│   ├── evaluate_model.py
│   └── deploy_model.py
├── tests/
│   └── test_finetuning.py
├── data/                     # Datasets
├── models/                   # Models
├── evals/                    # Evaluations
├── run_finetuning.sh         # Workflow script
└── FINETUNING_GUIDE.md       # Full documentation
```

## Requirements

- **GPU**: NVIDIA with 8GB+ VRAM recommended
- **Storage**: ~10GB for models and datasets
- **RAM**: 16GB+ recommended

## Testing

```bash
python -m pytest finetuning/tests/ -v
```

## Documentation

See [FINETUNING_GUIDE.md](FINETUNING_GUIDE.md) for complete documentation.
