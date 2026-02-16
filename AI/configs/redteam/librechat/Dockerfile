# Use the official LibreChat image as the base
FROM ghcr.io/danny-avila/librechat:latest

# Switch to root user to install packages
USER root

# Install additional tools and dependencies
# Example: Install Python, pip, and other utilities
RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    git \
    vim \
    ripgrep \
    # Add any other packages you need here
    && rm -rf /var/cache/apk/*

# If you need to install global node packages
# RUN npm install -g some-package

# If you need to install python packages
# RUN pip install some-package --break-system-packages

# Switch back to the non-root user for security (optional but recommended)
# The official image runs as node (uid 1000)
USER node
