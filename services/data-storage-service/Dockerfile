FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including comprehensive Snappy support
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    libsnappy-dev \
    libsnappy1v5 \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Explicitly install python-snappy for Kafka compression support
RUN pip install python-snappy

# Copy source code
COPY src/ ./src/

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]