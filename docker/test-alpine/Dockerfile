# Alpine test environment for saidata validation
FROM alpine:3.19

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash \
    curl

# Install saigen
RUN pip3 install --break-system-packages saigen

# Set working directory
WORKDIR /data

# Default command
CMD ["saigen", "test-system", "--help"]
