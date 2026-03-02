# Dockerfile for CLI Tools (Python)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tk \
    tcl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Set display environment
ENV DISPLAY=:0

# Default command
CMD ["python", "task_manager_gui.py"]
