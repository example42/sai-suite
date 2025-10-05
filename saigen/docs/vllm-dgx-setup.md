# vLLM Setup Guide for NVIDIA DGX Systems

This guide explains how to set up and use vLLM with SAIGEN on NVIDIA DGX systems for high-performance local LLM inference.

## Why vLLM for DGX?

vLLM is optimized for NVIDIA GPUs and provides:
- **High throughput**: Continuous batching for maximum GPU utilization
- **Efficient memory**: PagedAttention reduces memory usage by up to 2x
- **Fast inference**: Optimized CUDA kernels for NVIDIA hardware
- **Multi-GPU support**: Tensor parallelism for large models
- **Zero API costs**: Run models locally without external API calls

## Prerequisites

- NVIDIA DGX system with DGX OS 7
- CUDA 11.8+ or 12.1+
- Python 3.8+
- Sufficient GPU memory for your chosen model

## Installation

### 1. Install vLLM

```bash
# Install vLLM with CUDA support
pip install vllm

# Or for specific CUDA version (e.g., CUDA 12.1)
pip install vllm-cuda121
```

### 2. Verify Installation

```bash
python -c "import vllm; print(vllm.__version__)"
```

## Starting vLLM Server

### Basic Setup (Single GPU)

```bash
# Start vLLM server with Llama 3 8B model
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --host 0.0.0.0 \
    --port 8000
```

### Multi-GPU Setup (Tensor Parallelism)

For larger models or faster inference, use multiple GPUs:

```bash
# Use 2 GPUs for Llama 3 70B model
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-70B-Instruct \
    --tensor-parallel-size 2 \
    --host 0.0.0.0 \
    --port 8000
```

### Optimized DGX Configuration

For maximum performance on DGX systems:

```bash
# Llama 3 70B on 4 GPUs with optimized settings
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-70B-Instruct \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.95 \
    --max-model-len 8192 \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype auto
```

### Advanced Options

```bash
# Full configuration example
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-70B-Instruct \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.95 \
    --max-model-len 8192 \
    --max-num-seqs 256 \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype auto \
    --trust-remote-code
```

## SAIGEN Configuration

### Option 1: Using vLLM Provider (Recommended)

Add to your `~/.saigen/config.yaml`:

```yaml
llm_providers:
  vllm:
    provider: "vllm"
    base_url: "http://localhost:8000/v1"
    model: "meta-llama/Meta-Llama-3-70B-Instruct"
    temperature: 0.1
    max_tokens: 4096
    timeout: 120
    enabled: true
    # vLLM-specific settings (informational, set when starting server)
    tensor_parallel_size: 4
    gpu_memory_utilization: 0.95
```

### Option 2: Using OpenAI Provider with vLLM

vLLM is OpenAI-compatible, so you can also use the OpenAI provider:

```yaml
llm_providers:
  vllm:
    provider: "openai"
    api_key: "not-needed"
    api_base: "http://localhost:8000/v1"
    model: "meta-llama/Meta-Llama-3-70B-Instruct"
    temperature: 0.1
    max_tokens: 4096
    timeout: 120
    enabled: true
```

## Recommended Models for DGX

### For DGX A100 (8x 40GB or 8x 80GB)

| Model | GPUs | Memory | Best For |
|-------|------|--------|----------|
| Llama 3 8B | 1 | 16GB | Fast iteration, testing |
| Llama 3 70B | 2-4 | 140GB | Production quality |
| Mixtral 8x7B | 2 | 90GB | Good balance |
| CodeLlama 34B | 2 | 70GB | Code generation |
| Qwen2 72B | 4 | 145GB | Multilingual, high quality |

### Model Selection Guide

```bash
# Fast and efficient (1 GPU)
--model meta-llama/Meta-Llama-3-8B-Instruct

# Best quality (2-4 GPUs)
--model meta-llama/Meta-Llama-3-70B-Instruct

# Code-focused (2 GPUs)
--model codellama/CodeLlama-34b-Instruct-hf

# Mixture of Experts (2 GPUs)
--model mistralai/Mixtral-8x7B-Instruct-v0.1
```

## Usage with SAIGEN

### Generate Single Package

```bash
# Using vLLM provider
saigen generate nginx --llm-provider vllm

# With specific providers
saigen generate nginx --llm-provider vllm --providers apt,brew,winget
```

### Batch Generation

```bash
# Generate multiple packages
saigen batch generate software-list.txt --llm-provider vllm --max-concurrent 5

# With category filter
saigen batch generate software-list.txt --llm-provider vllm --category webserver
```

### Test Connection

```bash
# Verify vLLM is working
python -c "
from saigen.llm.providers.vllm import VLLMProvider
import asyncio

async def test():
    provider = VLLMProvider({
        'base_url': 'http://localhost:8000/v1',
        'model': 'meta-llama/Meta-Llama-3-70B-Instruct'
    })
    result = await provider.validate_connection()
    print(f'Connection valid: {result}')

asyncio.run(test())
"
```

## Performance Optimization

### GPU Memory Utilization

Adjust based on your workload:

```bash
# Conservative (more headroom for other processes)
--gpu-memory-utilization 0.85

# Balanced (default)
--gpu-memory-utilization 0.90

# Aggressive (maximum performance)
--gpu-memory-utilization 0.95
```

### Batch Size Tuning

For SAIGEN batch generation:

```bash
# In config.yaml
generation:
  parallel_requests: 10  # Increase for vLLM's continuous batching
  request_timeout: 120
```

### Context Length

Adjust based on your needs:

```bash
# Shorter context (faster, less memory)
--max-model-len 4096

# Standard context
--max-model-len 8192

# Extended context (slower, more memory)
--max-model-len 16384
```

## Monitoring

### Check GPU Usage

```bash
# Monitor GPU utilization
nvidia-smi -l 1

# Detailed monitoring
watch -n 1 nvidia-smi
```

### vLLM Metrics

vLLM exposes metrics at `http://localhost:8000/metrics` (Prometheus format).

## Troubleshooting

### Out of Memory

```bash
# Reduce memory utilization
--gpu-memory-utilization 0.85

# Reduce max sequence length
--max-model-len 4096

# Use more GPUs
--tensor-parallel-size 4
```

### Slow Inference

```bash
# Increase batch size
--max-num-seqs 256

# Use quantization (if supported)
--quantization awq

# Check GPU utilization with nvidia-smi
```

### Model Not Found

```bash
# Models are downloaded from HuggingFace automatically
# Ensure you have access to gated models (Llama, etc.)
huggingface-cli login

# Or set token
export HF_TOKEN=your_token_here
```

## Running as a Service

### Systemd Service (DGX OS)

Create `/etc/systemd/system/vllm.service`:

```ini
[Unit]
Description=vLLM OpenAI-Compatible Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username
Environment="CUDA_VISIBLE_DEVICES=0,1,2,3"
ExecStart=/usr/bin/python3 -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-70B-Instruct \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization 0.95 \
    --host 0.0.0.0 \
    --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vllm
sudo systemctl start vllm
sudo systemctl status vllm
```

## Docker Deployment

```bash
# Pull vLLM Docker image
docker pull vllm/vllm-openai:latest

# Run with GPU support
docker run --gpus all \
    -p 8000:8000 \
    --ipc=host \
    vllm/vllm-openai:latest \
    --model meta-llama/Meta-Llama-3-70B-Instruct \
    --tensor-parallel-size 4
```

## Cost Savings

Running vLLM locally eliminates API costs:

- **OpenAI GPT-4**: ~$0.03 per 1K tokens
- **Anthropic Claude**: ~$0.015 per 1K tokens
- **vLLM (local)**: $0.00 per 1K tokens

For generating 10,000 packages with ~5K tokens each:
- **Cloud APIs**: $1,500 - $2,500
- **vLLM**: $0 (electricity costs only)

## Additional Resources

- [vLLM Documentation](https://docs.vllm.ai/)
- [vLLM GitHub](https://github.com/vllm-project/vllm)
- [Model Performance Benchmarks](https://github.com/vllm-project/vllm#performance)
- [HuggingFace Model Hub](https://huggingface.co/models)

## Support

For issues specific to:
- **vLLM**: https://github.com/vllm-project/vllm/issues
- **SAIGEN**: https://github.com/example42/sai/issues
- **DGX OS**: NVIDIA Enterprise Support
