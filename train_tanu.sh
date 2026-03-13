#!/bin/bash

# Tanu Brain: Unified Training Script (macOS / Linux AMD)
# Author: Pikachuxxxx
# Version: 1.2.0

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$BASE_DIR/venv"
ADAPTER_NAME="tanu-brain.bin"
MODEL_NAME="tanu"
TRAIN_DATA="tanu_train_data.jsonl"

echo "🧠 Starting Tanu Brain Unified Trainer..."

# 1. Environment Check
if [ -d "$VENV_DIR" ]; then
    echo "   Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
else
    echo "   No virtual environment found. Using system python (not recommended)..."
fi

# 2. Step 1: Metadata Generation (Only if missing)
if [ ! -f "$TRAIN_DATA" ]; then
    echo "--- [1/3] Generating Initial Training Data ---"
    python hello_world_tanu.py --build-metadata
else
    echo "--- [1/3] Master Dataset Detected ($TRAIN_DATA) ---"
    echo "    Skipping base generation to preserve live memories."
fi

# 3. Dependency Check & Command Setup
OS_TYPE=$(uname)
if [ "$OS_TYPE" == "Darwin" ]; then
    echo "   Detected macOS (M-series)..."
    if ! pip show mlx-lm > /dev/null 2>&1; then
        echo "   Installing MLX LM for Apple Silicon..."
        pip install mlx-lm
    fi
    TRAIN_CMD="mlx_lm.lora --model qwen2.5:0.5b --train --data $TRAIN_DATA --iters 200 --adapter-path $ADAPTER_NAME"
elif [ "$OS_TYPE" == "Linux" ]; then
    echo "   Detected Linux (AMD/NVIDIA)..."
    if lspci | grep -i "AMD/ATI" > /dev/null 2>&1; then
        echo "   AMD GPU detected. Ensuring ROCm-enabled PyTorch is available..."
        if ! python -c "import torch; print(torch.cuda.is_available())" > /dev/null 2>&1; then
            echo "   Installing ROCm-enabled PyTorch..."
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.0
        fi
    fi
    
    if [ ! -d "LLaMA-Factory" ]; then
        echo "   Cloning LLaMA-Factory for Linux training..."
        git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
        cd LLaMA-Factory && pip install -e .[metrics,qwen] && cd ..
    fi
    TRAIN_CMD="python LLaMA-Factory/src/train.py --stage sft --do_train --model_name_or_path qwen2.5:0.5b --dataset tanu_train_data --finetuning_type lora --output_dir $ADAPTER_NAME --overwrite_output_dir --fp16 True --num_train_epochs 3.0"
else
    echo "❌ Unsupported OS: $OS_TYPE"
    exit 1
fi

# 4. Step 2: Training
echo "--- [2/3] Training the Adapter (LoRA) ---"
echo "   Running: $TRAIN_CMD"
eval $TRAIN_CMD

# 5. Step 3: Ollama Registration
echo "--- [3/3] Registering Model with Ollama ---"
if ! pgrep -x "ollama" > /dev/null && ! pgrep -x "Ollama" > /dev/null; then
    echo "⚠️  Ollama is not running. Model registration might fail."
fi
python hello_world_tanu.py --install

echo "✅ Tanu Brain evolved. 'ollama run tanu' to speak with her."
