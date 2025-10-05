# vLLM Setup Guide for NVIDIA GB10 (Grace Blackwell) Systems

This guide explains how to set up and use vLLM with SAIGEN on NVIDIA GB10 Grace Blackwell desktop workstations for high-performance local LLM inference.

## Why vLLM for GB10?

vLLM is optimized for NVIDIA GPUs and provides:
- **High throughput**: Continuous batching for maximum GPU utilization
- **Efficient memory**: PagedAttention reduces memory usage by up to 2x
- **Fast inference**: Optimized CUDA kernels for Blackwell architecture
- **Coherent memory**: Leverages GB10's unified CPU-GPU memory architecture
- **Zero API costs**: Run models locally without external API calls

## Prerequisites

- NVIDIA GB10 Grace Blackwell workstation with DGX OS
- CUDA 12.1+ (Blackwell support)
- Python 3.8+
- Network access to GB10 (if running SAIGEN remotely)

**Note**: The GB10 can run vLLM server while your development machine runs SAIGEN remotely over the network.

## Installation

### On GB10 Workstation

```bash
# On GB10: Install vLLM with CUDA support
pip install vllm

# Or for specific CUDA version (e.g., CUDA 12.1 for Blackwell)
pip install vllm-cuda121

# Verify installation
python -c "import vllm; print(vllm.__version__)"
```

### On Development Machine (Optional)

```bash
# On dev machine: Install SAIGEN only (vLLM runs on GB10)
pip install saigen

# Or install from source
pip install -e ./saigen
```

## Starting vLLM Server

### On GB10 Workstation

#### Basic Setup (Single GPU)

```bash
# On GB10: Start vLLM server with Llama 3 8B model
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --host 0.0.0.0 \
    --port 8000
```

**Note**: Using `--host 0.0.0.0` allows remote access from your development machine.

#### Optimized GB10 Configuration

For maximum performance leveraging GB10's 128GB unified memory:

```bash
# On GB10: Llama 3 8B optimized for Blackwell architecture
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --gpu-memory-utilization 0.90 \
    --max-model-len 8192 \
    --max-num-seqs 128 \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype auto
```

#### Larger Models on GB10

GB10's 128GB unified memory can handle larger models:

```bash
# On GB10: Mixtral 8x7B (leveraging unified memory)
python -m vllm.entrypoints.openai.api_server \
    --model mistralai/Mixtral-8x7B-Instruct-v0.1 \
    --gpu-memory-utilization 0.85 \
    --max-model-len 8192 \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype auto

# On GB10: Llama 3 70B (may work with quantization)
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-70B-Instruct \
    --gpu-memory-utilization 0.80 \
    --max-model-len 4096 \
    --quantization awq \
    --host 0.0.0.0 \
    --port 8000
```

**Note**: GB10's 128GB unified memory allows running larger models than typical single-GPU systems.

### Advanced Options

```bash
# Full configuration example for GB10
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --gpu-memory-utilization 0.90 \
    --max-model-len 8192 \
    --max-num-seqs 128 \
    --host 0.0.0.0 \
    --port 8000 \
    --dtype auto \
    --trust-remote-code
```

## SAIGEN Configuration

### Local Setup (SAIGEN on GB10)

If running SAIGEN directly on the GB10, add to `~/.saigen/config.yaml`:

```yaml
llm_providers:
  vllm:
    provider: "vllm"
    base_url: "http://localhost:8000/v1"
    model: "meta-llama/Meta-Llama-3-8B-Instruct"
    temperature: 0.1
    max_tokens: 4096
    timeout: 90
    enabled: true
```

### Remote Setup (SAIGEN on Development Machine)

If running SAIGEN on a separate development machine, use the GB10's IP address:

```yaml
llm_providers:
  vllm:
    provider: "vllm"
    base_url: "http://gb10-hostname:8000/v1"  # Replace with GB10 IP or hostname
    model: "meta-llama/Meta-Llama-3-8B-Instruct"
    temperature: 0.1
    max_tokens: 4096
    timeout: 120  # Longer timeout for network latency
    enabled: true
```

**Example with IP address:**
```yaml
llm_providers:
  vllm:
    provider: "vllm"
    base_url: "http://192.168.1.100:8000/v1"  # GB10's IP address
    model: "meta-llama/Meta-Llama-3-8B-Instruct"
    temperature: 0.1
    max_tokens: 4096
    timeout: 120
    enabled: true
```

**Network Requirements:**
- GB10 must be accessible on port 8000
- 10 GbE or ConnectX-7 (200 Gbps) recommended for best performance
- WiFi 7 also available but slower for large batches

### Alternative: Using OpenAI Provider with vLLM

vLLM is OpenAI-compatible, so you can also use the OpenAI provider:

```yaml
llm_providers:
  vllm:
    provider: "openai"
    api_key: "not-needed"
    api_base: "http://gb10-hostname:8000/v1"  # Use GB10's address
    model: "meta-llama/Meta-Llama-3-8B-Instruct"
    temperature: 0.1
    max_tokens: 4096
    timeout: 120
    enabled: true
```

## Recommended Models for GB10

### For GB10 Grace Blackwell (128GB Unified Memory)

| Model | Memory | Best For | Notes |
|-------|--------|----------|-------|
| Llama 3 8B | ~16GB | Production, fast inference | Recommended |
| Mistral 7B | ~16GB | Balanced performance | Good alternative |
| Mixtral 8x7B | ~90GB | High quality, MoE | Leverages unified memory |
| CodeLlama 34B | ~70GB | Code generation | Possible with unified memory |
| Llama 3 70B (AWQ) | ~40GB | Best quality | With quantization |
| Qwen2 7B | ~16GB | Multilingual | Good for non-English |

**GB10 Advantage**: The 128GB unified coherent memory allows running larger models than typical single-GPU systems. Models up to 70B can work with quantization (AWQ/GPTQ).

### Model Selection Guide

```bash
# Recommended: Fast and high quality (16GB)
--model meta-llama/Meta-Llama-3-8B-Instruct

# High quality MoE (90GB - leverages unified memory)
--model mistralai/Mixtral-8x7B-Instruct-v0.1

# Code-focused medium (70GB)
--model codellama/CodeLlama-34b-Instruct-hf

# Best quality with quantization (40GB)
--model TheBloke/Llama-2-70B-Chat-AWQ --quantization awq

# Very fast (8GB)
--model microsoft/Phi-3-medium-4k-instruct
```

## Usage with SAIGEN

### From Development Machine (Remote)

```bash
# On your development machine, SAIGEN connects to GB10 over network
saigen generate nginx --llm-provider vllm

# Batch generation leveraging GB10's 200 Gbps network
saigen batch generate software-list.txt --llm-provider vllm --max-concurrent 10

# With category filter
saigen batch generate software-list.txt --llm-provider vllm --category webserver
```

### From GB10 Directly (Local)

```bash
# On GB10 itself
saigen generate nginx --llm-provider vllm --providers apt,brew,winget

# Batch generation with higher concurrency (local = no network latency)
saigen batch generate software-list.txt --llm-provider vllm --max-concurrent 15
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

GB10's 128GB unified memory allows flexible allocation:

```bash
# Conservative (for smaller models, 8B-13B)
--gpu-memory-utilization 0.85

# Balanced (recommended for most workloads)
--gpu-memory-utilization 0.90

# Aggressive (for large models leveraging unified memory)
--gpu-memory-utilization 0.95
```

### Network Optimization (Remote Setup)

When running SAIGEN remotely:

```bash
# Use GB10's high-speed network
# - 10 GbE: Good for moderate batch sizes
# - ConnectX-7 @ 200 Gbps: Excellent for large batches
# - WiFi 7: Convenient but slower

# Increase batch size with high-speed network
saigen batch generate list.txt --max-concurrent 20  # With 200 Gbps
saigen batch generate list.txt --max-concurrent 5   # With WiFi 7
```

### Batch Size Tuning

For SAIGEN batch generation:

```yaml
# In config.yaml - Local on GB10
generation:
  parallel_requests: 15  # Higher for local access
  request_timeout: 90

# In config.yaml - Remote over network
generation:
  parallel_requests: 10  # Moderate for network latency
  request_timeout: 120   # Longer timeout for network
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

## Remote Setup (Development Machine → GB10)

### Network Configuration

1. **On GB10**: Ensure vLLM server binds to all interfaces:
```bash
# On GB10: Start with --host 0.0.0.0
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --host 0.0.0.0 \
    --port 8000
```

2. **Find GB10's IP address**:
```bash
# On GB10
ip addr show  # Look for inet address
# Or use hostname
hostname -I
```

3. **Test connectivity from development machine**:
```bash
# From dev machine
curl http://gb10-ip:8000/v1/models
# Should return list of available models
```

### Firewall Configuration

```bash
# On GB10: Allow port 8000 (if firewall is enabled)
sudo ufw allow 8000/tcp
# Or
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

### Network Performance

- **10 GbE**: Good for moderate batch sizes (5-10 concurrent)
- **ConnectX-7 @ 200 Gbps**: Excellent for large batches (20+ concurrent)
- **WiFi 7**: Convenient but slower (3-5 concurrent recommended)

## Troubleshooting

### Out of Memory

```bash
# On GB10: Reduce memory utilization
--gpu-memory-utilization 0.80

# Reduce max sequence length
--max-model-len 4096

# Use smaller model
--model mistralai/Mistral-7B-Instruct-v0.2

# Use quantization for large models
--model meta-llama/Meta-Llama-3-70B-Instruct --quantization awq
```

### Slow Inference

```bash
# On GB10: Increase batch size
--max-num-seqs 128

# Use quantization (if supported)
--quantization awq

# Check GPU utilization
nvidia-smi -l 1
```

### Connection Refused (Remote Setup)

```bash
# On GB10: Verify server is running
curl http://localhost:8000/v1/models

# Check firewall
sudo ufw status

# Ensure --host 0.0.0.0 was used when starting vLLM
```

### Model Not Found

```bash
# On GB10: Models are downloaded from HuggingFace automatically
# Ensure you have access to gated models (Llama, etc.)
huggingface-cli login

# Or set token
export HF_TOKEN=your_token_here
```

## Running as a Service

### Systemd Service (DGX OS on GB10)

Create `/etc/systemd/system/vllm.service`:

```ini
[Unit]
Description=vLLM OpenAI-Compatible Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username
Environment="CUDA_VISIBLE_DEVICES=0"
ExecStart=/usr/bin/python3 -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --gpu-memory-utilization 0.90 \
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

# Run with GPU support on GB10
docker run --gpus all \
    -p 8000:8000 \
    --ipc=host \
    vllm/vllm-openai:latest \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --gpu-memory-utilization 0.90
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
