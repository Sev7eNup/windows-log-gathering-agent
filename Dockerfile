# Windows Log Gathering Agent - Backend Container
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application source
COPY src/ ./src/
COPY mcp_servers/ ./mcp_servers/
COPY setup.py .
COPY pyproject.toml* .

# Install the application in development mode
RUN pip install -e .

# Create directories for configuration and logs
RUN mkdir -p /app/config /app/logs /app/data

# Copy default configuration
COPY config/ ./config/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "src.loggatheringagent.api.main", "--host", "0.0.0.0", "--port", "8000"]