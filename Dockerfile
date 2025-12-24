# RAG Document Generator - Dockerfile
# Production-ready container for the RAG API service

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download tiktoken encoding files (required for offline use)
RUN python -c "import tiktoken; tiktoken.encoding_for_model('gpt-4o-mini')"

# Copy application code
COPY app/ ./app/

# Create directory for Qdrant data (will be mounted as volume)
RUN mkdir -p /app/qdrant_data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

