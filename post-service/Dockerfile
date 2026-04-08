FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  gcc \
  libc-dev \
  libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY post-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY post-service /app
COPY shared_schemas ./shared_schemas

EXPOSE 8005

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8005/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
