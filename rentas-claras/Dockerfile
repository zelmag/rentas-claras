# Use Python 3.12 slim image with SQLite3 support
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies (SQLite3 is included in python:slim, but let's ensure it)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY database.py .
COPY src/ ./src/
COPY routes/ ./routes/
COPY services/ ./services/
COPY templates/ ./templates/
COPY static/ ./static/

# Create data directory for SQLite database persistence
RUN mkdir -p /data

# Expose port
EXPOSE 8080

# Run with gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120"]
