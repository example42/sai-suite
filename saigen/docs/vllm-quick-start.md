# vLLM Quick Start Guide

Get up and running with vLLM on your NVIDIA DGX in 5 minutes.

## 1. Install vLLM

```bash
pip install vllm
```

## 2. Start vLLM Server

```bash
# Quick start with Llama 3 70B on 4 GPUs
./scripts/development/saigen/start-vllm-dgx.sh

# Or manually:
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-70B-Instruct \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.95 \
    --host 0.0.0.0 \
    --port 8000
```

## 3. Configure SAIGEN

Add to `~/.saigen/config.yaml`:

```yaml
llm_providers:
  vllm:
    provider: "vllm"
    base_url: "http://localhost:8000/v1"
    model: "meta-llama/Meta-Llama-3-70B-Instruct"
    temperature: 0.1
    enabled: true
```

## 4. Test Connection

```bash
python scripts/development/saigen/test-vllm-provider.py
```

## 5. Generate Saidata

```bash
# Single package
saigen generate nginx --llm-provider vllm

# Batch generation
saigen batch generate software-list.txt --llm-provider vllm --max-concurrent 10
```

## Common Models

### Fast (1 GPU, ~16GB)
```bash
--model meta-llama/Meta-Llama-3-8B-Instruct
```

### Balanced (2 GPUs, ~90GB)
```bash
--model mistralai/Mixtral-8x7B-Instruct-v0.1 --tensor-parallel-size 2
```

### Best Quality (4 GPUs, ~140GB)
```bash
--model meta-llama/Meta-Llama-3-70B-Instruct --tensor-parallel-size 4
```

## Troubleshooting

### Server won't start
```bash
# Check GPU availability
nvidia-smi

# Check if port is in use
lsof -i :8000
```

### Out of memory
```bash
# Reduce memory utilization
--gpu-memory-utilization 0.85

# Use more GPUs
--tensor-parallel-size 8
```

### Model access denied
```bash
# Login to HuggingFace
huggingface-cli login

# Or set token
export HF_TOKEN=your_token
```

## Full Documentation

See [vllm-dgx-setup.md](vllm-dgx-setup.md) for complete guide.
