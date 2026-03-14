#!/bin/bash

# Tanu Brain: GGUF Soul & Memory Unified Trainer
# Author: Pikachuxxxx
# Version: 3.5.0

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$BASE_DIR/venv"
HF_BASE="Qwen/Qwen2.5-0.5B"
CORE_ADAPTER="tanu-core-adapter"
CORE_GGUF="tanu-core.gguf"
MEM_ADAPTER="tanu-memory.bin"

[ -d "$VENV_DIR" ] && source "$VENV_DIR/bin/activate"

OS_TYPE=$(uname)

# 0. Ensure LFS files are pulled
git lfs pull

# 1. CORE SOUL (GGUF Personality)
if [[ "$*" == *"--personality"* ]]; then
    echo "--- Building Core Soul ---"
    python hello_world_tanu.py --build-personality
    
    mkdir -p .tmp_data
    if [ "$OS_TYPE" == "Darwin" ]; then
        python hello_world_tanu.py --convert tanu_base_data.jsonl .tmp_data/train.jsonl mlx
        # Need at least 4 examples for validation to satisfy default MLX-LM batch size
        tail -n 8 .tmp_data/train.jsonl > .tmp_data/valid.jsonl 
        echo "   [TRAIN] Building Soul Adapter (MLX)..."
        mlx_lm.lora --model $HF_BASE --train --data .tmp_data --iters 2000 --adapter-path $CORE_ADAPTER
        echo "   [FUSE] Fusing Soul into GGUF directory..."
        mlx_lm.fuse --model $HF_BASE --adapter-path $CORE_ADAPTER --save-path $CORE_GGUF
    else
        python hello_world_tanu.py --convert tanu_base_data.jsonl .tmp_data/train.json hf
        echo "   [TRAIN] Building Soul Adapter (AMD/Linux)..."
        python LLaMA-Factory/src/train.py --stage sft --do_train --model_name_or_path $HF_BASE --dataset_dir .tmp_data --dataset train --finetuning_type lora --output_dir $CORE_ADAPTER --overwrite_output_dir --fp16 True --num_train_epochs 3.0
    fi
    
    rm -rf .tmp_data
    python hello_world_tanu.py --update-model-file
    python hello_world_tanu.py --install
    echo "Core GGUF soul ($CORE_GGUF) ready."
fi

# 2. EXPERIENCE (Memory Layer)
if [[ "$*" == *"--memory"* ]]; then
    echo "--- Updating Memory ---"
    if [ ! -f "$CORE_GGUF" ] && [ ! -d "$CORE_GGUF" ]; then echo "Error: Build soul first (--personality)"; exit 1; fi
    
    mkdir -p .tmp_mem_data
    if [ "$OS_TYPE" == "Darwin" ]; then
        python hello_world_tanu.py --convert tanu_train_data.jsonl .tmp_mem_data/train.jsonl mlx
        tail -n 8 .tmp_mem_data/train.jsonl > .tmp_mem_data/valid.jsonl
        echo "   [TRAIN] Building Memory Adapter on top of $CORE_GGUF..."
        mlx_lm.lora --model $CORE_GGUF --train --data .tmp_mem_data --iters 2000 --adapter-path $MEM_ADAPTER
    else
        python hello_world_tanu.py --convert tanu_train_data.jsonl .tmp_mem_data/train.json hf
        echo "   [TRAIN] Building Memory Adapter on top of $CORE_GGUF (Linux/AMD)..."
        python LLaMA-Factory/src/train.py --stage sft --do_train --model_name_or_path $CORE_GGUF --dataset_dir .tmp_mem_data --dataset train --finetuning_type lora --output_dir $MEM_ADAPTER --overwrite_output_dir --fp16 True --num_train_epochs 3.0
    fi
    
    rm -rf .tmp_mem_data
    python hello_world_tanu.py --update-model-file
    python hello_world_tanu.py --install
    echo "Memory adapter ($MEM_ADAPTER) updated."
fi

if [ $# -eq 0 ]; then
    echo "Usage: ./train_tanu.sh [--personality] [--memory]"
fi
