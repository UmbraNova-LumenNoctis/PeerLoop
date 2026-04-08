
FROM python:3.11-slim

WORKDIR /code

# Install system dependencies required to build some Python wheels (Pillow, etc.)
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
	curl \
	&& rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY search-service/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and shared schemas
COPY search-service /code
COPY shared_schemas /code/shared_schemas

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
