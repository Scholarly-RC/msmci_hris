# Dockerfile
FROM python:3.12-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install LibreOffice (headless mode)
RUN apt-get update && apt-get install -y libreoffice --no-install-recommends

# Install Node.js directly (Option 1 - recommended)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    npm --version && node --version

# Create and set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make scripts executable
RUN chmod +x scripts/entrypoint.sh scripts/wait-for-db.sh scripts/load_initial_data.sh

# Set environment variables for Node (update your .env accordingly)
ENV NPM_BIN_PATH=/usr/bin/npm

# Entrypoint
ENTRYPOINT ["scripts/entrypoint.sh"]