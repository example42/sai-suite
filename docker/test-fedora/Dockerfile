# Fedora test environment for saidata validation
FROM fedora:40

# Install system dependencies
RUN dnf install -y \
    python3 \
    python3-pip \
    systemd \
    curl \
    && dnf clean all

# Install saigen
RUN pip3 install saigen

# Set working directory
WORKDIR /data

# Default command
CMD ["saigen", "test-system", "--help"]
