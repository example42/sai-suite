# Debian test environment for saidata validation
FROM debian:12

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    systemctl \
    && rm -rf /var/lib/apt/lists/*

# Install saigen
RUN pip3 install --break-system-packages saigen

# Set working directory
WORKDIR /data

# Default command
CMD ["saigen", "test-system", "--help"]
