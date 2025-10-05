#!/bin/bash
# Start vLLM server optimized for NVIDIA DGX systems
# Usage: ./start-vllm-dgx.sh [model] [num_gpus]

set -e

# Default configuration
DEFAULT_MODEL="meta-llama/Meta-Llama-3-70B-Instruct"
DEFAULT_GPUS=4
DEFAULT_PORT=8000

# Parse arguments
MODEL="${1:-$DEFAULT_MODEL}"
NUM_GPUS="${2:-$DEFAULT_GPUS}"
PORT="${3:-$DEFAULT_PORT}"

echo "=========================================="
echo "Starting vLLM Server on DGX"
echo "=========================================="
echo "Model: $MODEL"
echo "GPUs: $NUM_GPUS"
echo "Port: $PORT"
echo "=========================================="

# Check if vLLM is installed
if ! python -c "import vllm" 2>/dev/null; then
    echo "ERROR: vLLM is not installed"
    echo "Install with: pip install vllm"
    exit 1
fi

# Check GPU availability
GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
echo "Available GPUs: $GPU_COUNT"

if [ "$NUM_GPUS" -gt "$GPU_COUNT" ]; then
    echo "WARNING: Requested $NUM_GPUS GPUs but only $GPU_COUNT available"
    echo "Using $GPU_COUNT GPUs instead"
    NUM_GPUS=$GPU_COUNT
fi

# Check if HuggingFace token is needed for gated models
if [[ "$MODEL" == *"llama"* ]] || [[ "$MODEL" == *"Llama"* ]]; then
    if [ -z "$HF_TOKEN" ]; then
        echo ""
        echo "NOTE: This model may require HuggingFace authentication"
        echo "If you get access errors, run: huggingface-cli login"
        echo "Or set: export HF_TOKEN=your_token"
        echo ""
    fi
fi

# Start vLLM server
echo ""
echo "Starting vLLM server..."
echo "API will be available at: http://localhost:$PORT/v1"
echo "Press Ctrl+C to stop"
echo ""

python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --tensor-parallel-size "$NUM_GPUS" \
    --gpu-memory-utilization 0.95 \
    --max-model-len 8192 \
    --max-num-seqs 256 \
    --host 0.0.0.0 \
    --port "$PORT" \
    --dtype auto \
    --trust-remote-code
