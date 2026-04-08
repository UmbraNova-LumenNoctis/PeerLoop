# -------- Base Image --------
FROM python:3.11-slim

# -------- Variables --------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# -------- Working directory --------
WORKDIR /app

# -------- System dependencies --------
RUN apt-get update && apt-get install -y \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# -------- Install Python dependencies --------
COPY file_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# -------- Copy project --------
COPY file_service /app
COPY shared_schemas ./shared_schemas

# -------- Expose (internal only) --------
EXPOSE 8002

# -------- Start server --------
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
