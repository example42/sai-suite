FROM ubuntu:24.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    sudo \
    zsh \
    vim \
    nano \
    less \
    jq \
    tree \
    htop \
    python3 \
    ca-certificates \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with sudo access
RUN useradd --create-home --shell /bin/zsh sai && \
    echo "sai ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Install Oh My Zsh for better terminal experience
USER sai
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# Switch back to root for final setup
USER root

# Install Python development tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Set working directory
WORKDIR /workspace

# Set default user
USER sai

# Default command
CMD ["/bin/zsh"]
