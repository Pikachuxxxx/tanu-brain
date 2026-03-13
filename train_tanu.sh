#!/bin/bash

# Tanu Brain: Unified Training & Fusing Script (macOS / Linux AMD)
# Author: Pikachuxxxx
# Version: 1.4.0 (Fused Soul & Live Memory)

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$BASE_DIR/venv"
HF_BASE_MODEL="Qwen/Qwen2.5-0.5B"
CORE_ADAPTER_DIR="tanu-core-adapter"
FUSED_MODEL_DIR="tanu-fused-core"
MEMORY_ADAPTER="tanu-memory.bin"
BASE_DATA="tanu_base_data.jsonl"
TRAIN_DATA="tanu_train_data.jsonl"

echo "🧠 Starting Tanu Brain Fusing Trainer..."

# 1. Environment Check
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
fi

# 2. Dependency Check
OS_TYPE=$(uname)
if [ "$OS_TYPE" == "Darwin" ]; then
    if ! pip show mlx-lm > /dev/null 2>&1; then pip install mlx-lm; fi
elif [ "$OS_TYPE" == "Linux" ]; then
    if [ ! -d "LLaMA-Factory" ]; then
        git clone --depth 1 https://github.com/hiyouga/LLaMA-Factory.git
        cd LLaMA-Factory && pip install -e .[metrics,qwen] && cd ..
    fi
fi

# 3. BUILD CORE PERSONALITY (The Fused Soul)
if [[ "$*" == *"--personality"* ]]; then
    echo "--- [1/2] BUILDING CORE PERSONALITY (The Fused Soul) ---"
    python hello_world_tanu.py --build-tanu-personality
    
    if [ "$OS_TYPE" == "Darwin" ]; then
        echo "   [TRAIN] Building Soul Adapter..."
        mlx_lm.lora --model $HF_BASE_MODEL --train --data $BASE_DATA --iters 200 --adapter-path $CORE_ADAPTER_DIR
        echo "   [FUSE] Fusing Soul into Base Model..."
        mlx_lm.fuse --model $HF_BASE_MODEL --adapter-path $CORE_ADAPTER_DIR --save-path $FUSED_MODEL_DIR
    elif [ "$OS_TYPE" == "Linux" ]; then
        echo "   [TRAIN & FUSE] Building & Exporting Fused Soul..."
        # LLaMA-Factory combined command to train and export fused model
        python LLaMA-Factory/src/train.py --stage sft --do_train --model_name_or_path $HF_BASE_MODEL --dataset tanu_base_data --finetuning_type lora --output_dir $CORE_ADAPTER_DIR --overwrite_output_dir --fp16 True --num_train_epochs 3.0
        python LLaMA-Factory/src/train.py --stage sft --model_name_or_path $HF_BASE_MODEL --adapter_name_or_path $CORE_ADAPTER_DIR --template qwen --finetuning_type lora --export_dir $FUSED_MODEL_DIR --export_size 2 --export_legacy_format False
    fi
    
    python hello_world_tanu.py --install tanu-base
    echo "✅ tanu-base (Fused Soul) is now live in Ollama."
fi

# 4. UPDATE MEMORY (The Live Adapter)
if [[ "$*" == *"--memory"* ]]; then
    echo "--- [2/2] BUILDING EXPERIENCE (Memory Adapter) ---"
    if [ ! -f "$TRAIN_DATA" ]; then
        echo "❌ No live thoughts detected in $TRAIN_DATA."
        exit 1
    fi
    python hello_world_tanu.py --update-tanu-memory
    
    if [ "$OS_TYPE" == "Darwin" ]; then
        # We train on top of the FUSED model
        echo "   [TRAIN] Building Memory Adapter on top of Fused Soul..."
        mlx_lm.lora --model $FUSED_MODEL_DIR --train --data $TRAIN_DATA --iters 200 --adapter-path $MEMORY_ADAPTER
    elif [ "$OS_TYPE" == "Linux" ]; then
        echo "   [TRAIN] Building Memory Adapter..."
        python LLaMA-Factory/src/train.py --stage sft --do_train --model_name_or_path $FUSED_MODEL_DIR --dataset tanu_train_data --finetuning_type lora --output_dir $MEMORY_ADAPTER --overwrite_output_dir --fp16 True --num_train_epochs 3.0
    fi
    
    python hello_world_tanu.py --install tanu
    echo "✅ tanu (Evolved Brain) is now live in Ollama."
fi

if [ $# -eq 0 ]; then
    echo "Usage: ./train_tanu.sh [--personality] [--memory]"
fi
