FROM python:3.11-slim

WORKDIR /app

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
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
# Copy requirements (build context is repo root)
COPY auth_service/requirements.txt ./requirements.txt

# Copy shared schemas
COPY shared_schemas ./shared_schemas

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY auth_service /app
WORKDIR /app

# Expose port
EXPOSE 8001

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]