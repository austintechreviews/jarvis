#!/bin/bash
# JARVIS Fine-Tuning Workflow Script
# Automates the complete fine-tuning pipeline

set -e

JARVIS_DIR="$HOME/jarvis"
FINETUNING_DIR="$JARVIS_DIR/finetuning"
LOGS_DIR="$JARVIS_DIR/logs"
DATA_DIR="$FINETUNING_DIR/data"
MODELS_DIR="$FINETUNING_DIR/models"

echo "╔════════════════════════════════════════════╗"
echo "║     JARVIS Fine-Tuning Workflow Script     ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Check if running from correct directory
if [ ! -d "$FINETUNING_DIR" ]; then
    echo "Error: Fine-tuning directory not found at $FINETUNING_DIR"
    exit 1
fi

cd "$FINETUNING_DIR"

# Parse command
case "${1:-help}" in
    collect)
        echo "📊 Data Collection Status"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        python3 -c "
import sys
sys.path.insert(0, '$FINETUNING_DIR/..')
from finetuning.data_collector import DataCollector
from pathlib import Path
c = DataCollector(Path('$LOGS_DIR'))
stats = c.get_stats()
print(f'Total interactions: {stats[\"total_interactions\"]}')
print(f'Successful: {stats[\"successful\"]}')
print(f'Failed: {stats[\"failed\"]}')
print(f'Corrections: {stats[\"corrections\"]}')
"
        if [ -f "$LOGS_DIR/conversations.jsonl" ]; then
            COUNT=$(wc -l < "$LOGS_DIR/conversations.jsonl")
            echo ""
            echo "Conversation log: $COUNT entries"
            if [ "$COUNT" -ge 100 ]; then
                echo "✓ Ready for fine-tuning!"
            else
                echo "⚠ Need $((100 - COUNT)) more interactions for basic fine-tuning"
            fi
        else
            echo "No conversation log found. Use JARVIS to collect data."
        fi
        ;;
    
    prepare)
        echo "📁 Preparing Training Dataset"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        mkdir -p "$DATA_DIR"
        python3 "$FINETUNING_DIR/tools/prepare_training_data.py" "$LOGS_DIR" "$DATA_DIR/dataset.jsonl"
        echo ""
        echo "Dataset prepared in $DATA_DIR"
        ls -lh "$DATA_DIR"/*.jsonl 2>/dev/null || echo "No dataset files found"
        ;;
    
    train)
        echo "🚀 Starting Fine-Tuning"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        # Check for GPU
        if ! command -v nvidia-smi &> /dev/null; then
            echo "⚠ Warning: NVIDIA GPU not detected. Training may be slow or fail."
        fi
        
        # Check dependencies
        if ! python3 -c "import unsloth" 2>/dev/null; then
            echo "Installing Unsloth..."
            pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
            pip install --no-deps xformers trl peft accelerate bitsandbytes
        fi
        
        # Run training
        python3 "$FINETUNING_DIR/tools/finetune_unsloth.py" \
            --train "$DATA_DIR/dataset_train.jsonl" \
            --val "$DATA_DIR/dataset_val.jsonl" \
            --output "$MODELS_DIR/jarvis-finetuned-v1" \
            "${@:2}"
        ;;
    
    deploy)
        echo "📦 Deploying to Ollama"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        GGUF_FILE="$MODELS_DIR/jarvis-finetuned-v1/gguf/model-q4_k_m.gguf"
        if [ ! -f "$GGUF_FILE" ]; then
            echo "Error: GGUF model not found at $GGUF_FILE"
            echo "Run fine-tuning first: $0 train"
            exit 1
        fi
        
        python3 "$FINETUNING_DIR/tools/deploy_model.py" \
            --gguf "$GGUF_FILE" \
            --name jarvis-finetuned \
            --version v1
        
        echo ""
        echo "✓ Deployment complete!"
        echo "Test with: ollama run jarvis-finetuned:v1"
        ;;
    
    evaluate)
        echo "📈 Evaluating Model"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        
        if [ ! -f "$DATA_DIR/dataset_val.jsonl" ]; then
            echo "Error: Validation set not found. Run prepare first."
            exit 1
        fi
        
        python3 "$FINETUNING_DIR/tools/evaluate_model.py" \
            --test-file "$DATA_DIR/dataset_val.jsonl" \
            --output "$FINETUNING_DIR/evals/results.json" \
            "${@:2}"
        ;;
    
    ab-test)
        echo "🔬 A/B Testing"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        shift
        python3 "$FINETUNING_DIR/tools/evaluate_model.py" --ab-test "$@"
        ;;
    
    clean)
        echo "🧹 Cleaning Up"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        rm -rf "$MODELS_DIR"/*
        rm -rf "$DATA_DIR"/*
        rm -rf "$FINETUNING_DIR/evals"/*
        echo "✓ Cleaned models, data, and evaluations"
        ;;
    
    help|*)
        echo "Usage: $0 {command} [options]"
        echo ""
        echo "Commands:"
        echo "  collect   - Show data collection status"
        echo "  prepare   - Prepare training dataset"
        echo "  train     - Run fine-tuning"
        echo "  deploy    - Deploy to Ollama"
        echo "  evaluate  - Evaluate fine-tuned model"
        echo "  ab-test   - A/B test models (provide prompts)"
        echo "  clean     - Remove all fine-tuning artifacts"
        echo "  help      - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 collect"
        echo "  $0 prepare"
        echo "  $0 train --epochs 3 --batch-size 2"
        echo "  $0 deploy"
        echo "  $0 ab-test \"list files\" \"search for Python\""
        ;;
esac
