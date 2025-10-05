# vLLM Quick Start Guide

Get up and running with vLLM on your NVIDIA GB10 (Grace Blackwell) in 5 minutes.

## Setup Options

Choose based on where you want to run SAIGEN:
- **Option A**: Local (both vLLM and SAIGEN on GB10)
- **Option B**: Remote (vLLM on GB10, SAIGEN on dev machine)

---

## Option A: Local Setup (Everything on GB10)

### 1. On GB10: Install vLLM

```bash
pip install vllm
```

### 2. On GB10: Start vLLM Server

```bash
# Quick start with Llama 3 8B
./scripts/development/saigen/start-vllm-dgx.sh

# Or manually:
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --gpu-memory-utilization 0.90 \
    --host 0.0.0.0 \
    --port 8000
```

### 3. On GB10: Configure SAIGEN

Add to `~/.saigen/config.yaml`:

```yaml
llm_providers:
  vllm:
    provider: "vllm"
    base_url: "http://localhost:8000/v1"
    model: "meta-llama/Meta-Llama-3-8B-Instruct"
    temperature: 0.1
    enabled: true
```

### 4. On GB10: Generate

```bash
saigen generate nginx --llm-provider vllm
```

---

## Option B: Remote Setup (vLLM on GB10, SAIGEN on Dev Machine)

### 1. On GB10: Install vLLM

```bash
pip install vllm
```

### 2. On GB10: Start vLLM Server

```bash
# IMPORTANT: Use --host 0.0.0.0 for remote access
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --gpu-memory-utilization 0.90 \
    --host 0.0.0.0 \
    --port 8000
```

### 3. On GB10: Get IP Address

```bash
hostname -I
# Example output: 192.168.1.100
```

### 4. On Dev Machine: Configure SAIGEN

Add to `~/.saigen/config.yaml`:

```yaml
llm_providers:
  vllm:
    provider: "vllm"
    base_url: "http://192.168.1.100:8000/v1"  # Use GB10's IP
    model: "meta-llama/Meta-Llama-3-8B-Instruct"
    temperature: 0.1
    timeout: 120  # Longer for network
    enabled: true
```

### 5. On Dev Machine: Test Connection

```bash
curl http://192.168.1.100:8000/v1/models
```

### 6. On Dev Machine: Generate

```bash
saigen generate nginx --llm-provider vllm
```

---

## Batch Generation

```bash
# Local on GB10 (higher concurrency)
saigen batch generate software-list.txt --llm-provider vllm --max-concurrent 15

# Remote over 10 GbE
saigen batch generate software-list.txt --llm-provider vllm --max-concurrent 10

# Remote over WiFi 7
saigen batch generate software-list.txt --llm-provider vllm --max-concurrent 5
```

## GB10 Hardware Specs

- **GPU**: NVIDIA Blackwell (1 PFLOP FP4)
- **CPU**: 20-core Arm (10x Cortex-X925 + 10x Cortex-A725)
- **Memory**: 128 GB LPDDR5x unified @ 273 GB/s
- **Network**: 10 GbE + ConnectX-7 @ 200 Gbps + WiFi 7
- **Power**: 240W TDP

## Recommended Models for GB10

### Fast & Efficient (~16GB)
```bash
--model meta-llama/Meta-Llama-3-8B-Instruct  # Recommended
--model mistralai/Mistral-7B-Instruct-v0.2   # Alternative
```

### High Quality (~90GB, leverages 128GB unified memory)
```bash
--model mistralai/Mixtral-8x7B-Instruct-v0.1
```

### Code-Focused (~70GB)
```bash
--model codellama/CodeLlama-34b-Instruct-hf
```

### Best Quality (~40GB with quantization)
```bash
--model meta-llama/Meta-Llama-3-70B-Instruct --quantization awq
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
--gpu-memory-utilization 0.80

# Use a smaller model
--model mistralai/Mistral-7B-Instruct-v0.2
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
