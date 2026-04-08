FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  gcc \
  libc-dev \
  libjpeg-dev \
  zlib1g-dev \
  libfreetype6-dev \
  liblcms2-dev \
  libwebp-dev \
  libopenjp2-7-dev \
  tcl-dev \
  tk-dev \
  curl \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching (context is repo root)
COPY api-gateway/requirements.txt ./requirements.txt

# Copy shared schemas into image
COPY shared_schemas ./shared_schemas

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (api-gateway folder)
COPY api-gateway /app
WORKDIR /app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
