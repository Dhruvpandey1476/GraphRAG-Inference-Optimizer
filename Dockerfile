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

# Increase Node memory for builds
ENV NODE_OPTIONS=--max-old-space-size=1024

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Build frontend with detailed output and error handling
RUN cd frontend && \
    echo "Node version:" && node --version && \
    echo "NPM version:" && npm --version && \
    echo "Installing npm dependencies..." && \
    npm install --legacy-peer-deps --no-audit 2>&1 && \
    echo "NPM install completed successfully" && \
    echo "Running vite build..." && \
    npm run build 2>&1 && \
    echo "Vite build completed successfully" && \
    if [ -d "dist" ]; then echo "✅ dist/ exists"; ls -la dist/ | head -20; else echo "❌ dist/ does not exist"; fi && \
    cd .. && \
    echo "Frontend build process complete"


# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Expose port
EXPOSE 7860

# Start command
CMD ["uvicorn", "backend.api.server:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
