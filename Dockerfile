# Use Python 3.11 slim image
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    nodejs \
    npm \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Build frontend with detailed output and error handling
RUN cd frontend && \
    echo "Installing npm dependencies..." && \
    npm install --legacy-peer-deps --verbose && \
    echo "Building frontend with Vite..." && \
    npm run build && \
    echo "Build output:" && \
    ls -la . && \
    echo "Dist folder:" && \
    ls -la dist/ || echo "WARNING: dist folder not created" && \
    echo "Static folder:" && \
    ls -la dist/static/ || echo "WARNING: static folder not created" && \
    cd ..


# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Expose port
EXPOSE 7860

# Start command
CMD ["uvicorn", "backend.api.server:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
