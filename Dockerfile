# Multi-stage build for SAI Software Management Suite
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY pyproject.toml README.md CHANGELOG.md ./
COPY sai/ ./sai/
COPY saigen/ ./saigen/
COPY providers/ ./providers/

COPY schemas/ ./schemas/

# Install the package
RUN pip install --no-cache-dir -e ".[all]"

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.local/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash sai

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY --from=builder /app /app

# Create directories for SAI
RUN mkdir -p /home/sai/.sai/saidata \
    /home/sai/.sai/providers \
    /home/sai/.sai/cache \
    && chown -R sai:sai /home/sai/.sai

# Switch to non-root user
USER sai
WORKDIR /home/sai

# Create default configuration
RUN cat > /home/sai/.sai/config.yaml << 'EOF'
config_version: "0.1.0"
log_level: info

saidata_paths:
  - "/app/saidata"
  - "/home/sai/.sai/saidata"

provider_paths:
  - "/app/providers"
  - "/home/sai/.sai/providers"

provider_priorities:
  apt: 1
  dnf: 2
  apk: 3

max_concurrent_actions: 3
action_timeout: 300
require_confirmation: false
dry_run_default: false
EOF

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sai --version || exit 1

# Default command
CMD ["sai", "--help"]

# Labels
LABEL org.opencontainers.image.title="SAI Software Management Suite"
LABEL org.opencontainers.image.description="Cross-platform software management CLI tool"
LABEL org.opencontainers.image.url="https://sai.software"
LABEL org.opencontainers.image.source="https://github.com/example42/sai"
LABEL org.opencontainers.image.vendor="SAI Team"
LABEL org.opencontainers.image.licenses="MIT"