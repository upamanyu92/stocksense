FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libhdf5-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy all requirements files first to leverage Docker cache
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script first and make it executable
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

# Copy application code
COPY . .

# Ensure data directory exists
RUN mkdir -p /app/data /app/app/db

# Set Python path
ENV PYTHONPATH=/app

ENTRYPOINT ["/app/entrypoint.sh"]
