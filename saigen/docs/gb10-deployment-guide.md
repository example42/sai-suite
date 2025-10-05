# GB10 Deployment Guide for SAIGEN

Complete guide for deploying SAIGEN with vLLM on NVIDIA GB10 (Grace Blackwell) workstations.

## GB10 Hardware Overview

| Component | Specification |
|-----------|---------------|
| **GPU** | NVIDIA Blackwell Architecture, 5th Gen Tensor Cores |
| **CPU** | 20-core Arm (10x Cortex-X925 + 10x Cortex-A725) |
| **Performance** | 1 PFLOP tensor performance (FP4) |
| **Memory** | 128 GB LPDDR5x unified coherent @ 273 GB/s |
| **Storage** | 4 TB NVMe M.2 with self-encryption |
| **Network** | 10 GbE + ConnectX-7 @ 200 Gbps + WiFi 7 |
| **Power** | 240W TDP |
| **OS** | NVIDIA DGX OS |

## Deployment Architectures

### Architecture 1: Standalone (All on GB10)

```
┌─────────────────────────────────────┐
│         GB10 Workstation            │
│                                     │
│  ┌──────────┐      ┌──────────┐   │
│  │  vLLM    │◄────►│ SAIGEN   │   │
│  │  Server  │      │          │   │
│  └──────────┘      └──────────┘   │
│       ▲                             │
│       │                             │
│  ┌────┴─────┐                      │
│  │ Blackwell│                      │
│  │   GPU    │                      │
│  └──────────┘                      │
└─────────────────────────────────────┘
```

**Best for:**
- Single user
- Maximum performance
- No network latency

**Configuration:**
```yaml
llm_providers:
  vllm:
    base_url: "http://localhost:8000/v1"
    timeout: 90
```

**Concurrency:** 15+ parallel requests

---

### Architecture 2: Remote (vLLM on GB10, SAIGEN on Dev Machine)

```
┌──────────────────┐         ┌─────────────────────────┐
│  Dev Machine     │         │   GB10 Workstation      │
│                  │         │                         │
│  ┌──────────┐   │  10GbE  │   ┌──────────┐         │
│  │ SAIGEN   │◄──┼─────────┼──►│  vLLM    │         │
│  │          │   │  or     │   │  Server  │         │
│  └──────────┘   │ 200Gbps │   └──────────┘         │
│                  │         │        ▲                │
│                  │         │        │                │
│                  │         │   ┌────┴─────┐         │
│                  │         │   │ Blackwell│         │
│                  │         │   │   GPU    │         │
│                  │         │   └──────────┘         │
└──────────────────┘         └─────────────────────────┘
```

**Best for:**
- Team access
- Multiple developers
- Flexible development

**Configuration:**
```yaml
llm_providers:
  vllm:
    base_url: "http://gb10-ip:8000/v1"
    timeout: 120  # Longer for network
```

**Concurrency:**
- 10 GbE: 10 parallel requests
- ConnectX-7 @ 200 Gbps: 20+ parallel requests
- WiFi 7: 5 parallel requests

---

### Architecture 3: Multi-User (Multiple Dev Machines → GB10)

```
┌──────────────┐
│ Dev Machine 1│─┐
└──────────────┘ │
                 │  10GbE
┌──────────────┐ │  or        ┌─────────────────────────┐
│ Dev Machine 2│─┼─200Gbps───►│   GB10 Workstation      │
└──────────────┘ │             │                         │
                 │             │   ┌──────────┐         │
┌──────────────┐ │             │   │  vLLM    │         │
│ Dev Machine 3│─┘             │   │  Server  │         │
└──────────────┘               │   └──────────┘         │
                               │        ▲                │
                               │        │                │
                               │   ┌────┴─────┐         │
                               │   │ Blackwell│         │
                               │   │   GPU    │         │
                               │   └──────────┘         │
                               └─────────────────────────┘
```

**Best for:**
- Team environments
- Shared GPU resources
- Cost-effective AI infrastructure

**Note:** vLLM handles concurrent requests efficiently with continuous batching.

---

## Setup Instructions

### Step 1: On GB10 - Install vLLM

```bash
# SSH into GB10 or work directly on it
ssh user@gb10-hostname

# Install vLLM
pip install vllm

# Verify installation
python -c "import vllm; print(vllm.__version__)"
```

### Step 2: On GB10 - Start vLLM Server

```bash
# For local access only
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --gpu-memory-utilization 0.90 \
    --max-model-len 8192 \
    --host localhost \
    --port 8000

# For remote access (required for Architecture 2 & 3)
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --gpu-memory-utilization 0.90 \
    --max-model-len 8192 \
    --host 0.0.0.0 \
    --port 8000
```

### Step 3: Configure Firewall (Remote Access Only)

```bash
# On GB10: Allow port 8000
sudo ufw allow 8000/tcp

# Or with firewalld
sudo firewall-cmd --add-port=8000/tcp --permanent
sudo firewall-cmd --reload
```

### Step 4: Get GB10's IP Address

```bash
# On GB10
hostname -I
# Example output: 192.168.1.100

# Or use hostname
hostname
# Example output: gb10.local
```

### Step 5: Configure SAIGEN

**On GB10 (Architecture 1):**
```yaml
# ~/.saigen/config.yaml
llm_providers:
  vllm:
    provider: "vllm"
    base_url: "http://localhost:8000/v1"
    model: "meta-llama/Meta-Llama-3-8B-Instruct"
    temperature: 0.1
    max_tokens: 4096
    timeout: 90
    enabled: true

generation:
  parallel_requests: 15
```

**On Dev Machine (Architecture 2 & 3):**
```yaml
# ~/.saigen/config.yaml
llm_providers:
  vllm:
    provider: "vllm"
    base_url: "http://192.168.1.100:8000/v1"  # GB10's IP
    model: "meta-llama/Meta-Llama-3-8B-Instruct"
    temperature: 0.1
    max_tokens: 4096
    timeout: 120
    enabled: true

generation:
  parallel_requests: 10  # Adjust based on network
```

### Step 6: Test Connection

```bash
# From dev machine
curl http://192.168.1.100:8000/v1/models

# Or use SAIGEN test script
python scripts/development/saigen/test-vllm-provider.py
```

### Step 7: Generate Saidata

```bash
# Single package
saigen generate nginx --llm-provider vllm

# Batch generation
saigen batch generate software-list.txt --llm-provider vllm --max-concurrent 10
```

## Model Recommendations

### Based on GB10's 128GB Unified Memory

| Model | Memory | Speed | Quality | Use Case |
|-------|--------|-------|---------|----------|
| Llama 3 8B | 16GB | ⚡⚡⚡ | ⭐⭐⭐ | Recommended for most workloads |
| Mistral 7B | 16GB | ⚡⚡⚡ | ⭐⭐⭐ | Fast alternative |
| Mixtral 8x7B | 90GB | ⚡⚡ | ⭐⭐⭐⭐ | High quality, leverages unified memory |
| CodeLlama 34B | 70GB | ⚡⚡ | ⭐⭐⭐⭐ | Code generation |
| Llama 3 70B (AWQ) | 40GB | ⚡ | ⭐⭐⭐⭐⭐ | Best quality with quantization |
| Phi-3 Medium | 8GB | ⚡⚡⚡ | ⭐⭐ | Very fast, lower quality |

### Model Selection Command

```bash
# On GB10: Start with different models

# Fast and efficient (recommended)
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --host 0.0.0.0 --port 8000

# High quality (leverages 128GB memory)
python -m vllm.entrypoints.openai.api_server \
    --model mistralai/Mixtral-8x7B-Instruct-v0.1 \
    --gpu-memory-utilization 0.85 \
    --host 0.0.0.0 --port 8000

# Best quality (with quantization)
python -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Meta-Llama-3-70B-Instruct \
    --quantization awq \
    --gpu-memory-utilization 0.80 \
    --host 0.0.0.0 --port 8000
```

## Performance Tuning

### Network-Based Tuning

| Network | Bandwidth | Recommended Concurrency | Timeout |
|---------|-----------|------------------------|---------|
| Local (on GB10) | N/A | 15+ | 90s |
| 10 GbE | 10 Gbps | 10 | 120s |
| ConnectX-7 | 200 Gbps | 20+ | 120s |
| WiFi 7 | ~5 Gbps | 5 | 150s |

### Memory Utilization

```bash
# Conservative (for smaller models)
--gpu-memory-utilization 0.85

# Balanced (recommended)
--gpu-memory-utilization 0.90

# Aggressive (for large models using unified memory)
--gpu-memory-utilization 0.95
```

### Batch Size

```bash
# Adjust based on model size and workload
--max-num-seqs 128  # Default, good for most cases
--max-num-seqs 256  # Higher for small models
--max-num-seqs 64   # Lower for large models
```

## Monitoring

### GPU Utilization

```bash
# On GB10: Monitor GPU usage
nvidia-smi -l 1

# Detailed monitoring
watch -n 1 nvidia-smi
```

### vLLM Metrics

```bash
# vLLM exposes Prometheus metrics
curl http://localhost:8000/metrics
```

### Network Monitoring

```bash
# Monitor network traffic
iftop -i eth0  # For 10 GbE
iftop -i ib0   # For ConnectX-7
```

## Troubleshooting

### Connection Issues

```bash
# On GB10: Verify server is running
curl http://localhost:8000/v1/models

# From dev machine: Test connectivity
curl http://gb10-ip:8000/v1/models

# Check firewall
sudo ufw status

# Verify vLLM is listening on all interfaces
sudo netstat -tulpn | grep 8000
```

### Performance Issues

```bash
# Check GPU utilization
nvidia-smi

# If GPU utilization is low, increase batch size
--max-num-seqs 256

# If out of memory, reduce memory utilization
--gpu-memory-utilization 0.80

# Or use a smaller model
--model mistralai/Mistral-7B-Instruct-v0.2
```

### Network Latency

```bash
# Test latency from dev machine to GB10
ping gb10-ip

# Test bandwidth
iperf3 -c gb10-ip

# If latency is high:
# - Use wired connection (10 GbE or ConnectX-7)
# - Reduce concurrent requests
# - Increase timeout in SAIGEN config
```

## Production Deployment

### Systemd Service (on GB10)

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

### Docker Deployment (on GB10)

```bash
# Pull vLLM Docker image
docker pull vllm/vllm-openai:latest

# Run with GPU support
docker run --gpus all \
    -p 8000:8000 \
    --ipc=host \
    vllm/vllm-openai:latest \
    --model meta-llama/Meta-Llama-3-8B-Instruct \
    --gpu-memory-utilization 0.90 \
    --host 0.0.0.0
```

## Cost Analysis

### API Cost Comparison

For generating 10,000 packages (~5K tokens each):

| Provider | Cost per 1K tokens | Total Cost |
|----------|-------------------|------------|
| OpenAI GPT-4 | $0.03 | $1,500 |
| Anthropic Claude | $0.015 | $750 |
| **vLLM on GB10** | **$0.00** | **$0** |

**ROI**: GB10 pays for itself after ~20,000-40,000 packages compared to cloud APIs.

### Power Consumption

- GB10 TDP: 240W
- Cost per kWh: ~$0.12 (US average)
- Cost per hour: $0.029
- Cost for 10,000 packages (~10 hours): $0.29

**Total cost with vLLM: $0.29 vs. $750-$1,500 with cloud APIs**

## Best Practices

1. **Use wired network** (10 GbE or ConnectX-7) for remote access
2. **Start with Llama 3 8B** for testing, scale up as needed
3. **Monitor GPU utilization** to optimize batch size
4. **Use systemd service** for production deployments
5. **Leverage 128GB unified memory** for larger models
6. **Adjust concurrency** based on network bandwidth
7. **Set appropriate timeouts** for network latency

## Additional Resources

- [vLLM Documentation](https://docs.vllm.ai/)
- [NVIDIA Grace Blackwell](https://www.nvidia.com/en-us/data-center/grace-blackwell-superchip/)
- [SAIGEN Documentation](../README.md)
- [vLLM Setup Guide](vllm-dgx-setup.md)
- [vLLM Quick Start](vllm-quick-start.md)
