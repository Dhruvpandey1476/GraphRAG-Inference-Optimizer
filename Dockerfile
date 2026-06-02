# Stage 1: Build frontend with Node
# CACHE BUSTER v4: 2026-06-02T22:50:00Z - Environment variable whitespace fix + env var strip
# Commits: 0f25e7de (gemini_client.py + tigergraph_client.py .strip())
FROM node:18-alpine AS frontend-builder

WORKDIR /build/frontend

# Copy frontend files
COPY frontend/package.json frontend/package-lock.json ./
COPY frontend/vite.config.js ./
COPY frontend/index.html ./
COPY frontend/src ./src

# Install and build frontend
RUN npm install --legacy-peer-deps --no-audit && \
    npm run build && \
    echo "✅ Frontend built successfully"

# Stage 2: Runtime with Python + built frontend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt .

# CACHE BUSTER v4: Force complete rebuild - environment variable whitespace fix
RUN echo "🔄 FORCE REBUILD v4 - $(date)" && \
    echo "Fixes: .strip() on all env vars (gemini_client.py, tigergraph_client.py)" && \
    echo "Deployed at: 2026-06-02T22:50:00Z" && \
    echo "BUILD_ID=0f25e7de-env-strip-fix"

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built frontend from stage 1
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# Verify frontend was built
RUN echo "Verifying frontend build..." && \
    ls -la frontend/dist/ && \
    [ -f frontend/dist/index.html ] && echo "✅ index.html exists" || echo "❌ index.html missing" && \
    [ -d frontend/dist/assets ] && echo "✅ assets folder exists" || echo "❌ assets folder missing"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

# Expose port
EXPOSE 7860

# Start command
CMD ["uvicorn", "backend.api.server:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
