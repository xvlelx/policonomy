FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.prod.txt .
# CPU-only torch 먼저 설치 (CUDA 제외 → 이미지 ~2GB 절약)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.prod.txt

COPY src ./src
COPY templates ./templates
COPY third_party/Kronos ./third_party/Kronos
COPY data ./data_seed

RUN mkdir -p /app/data/models /app/logs

# startup: seed data into volume-mounted /app/data if not already present
RUN printf '#!/bin/sh\n\
for f in /app/data_seed/*.json; do\n\
  [ ! -f "/app/data/$(basename $f)" ] && cp "$f" /app/data/;\n\
done\n\
[ ! -d /app/data/models ] && mkdir -p /app/data/models\n\
for f in /app/data_seed/models/*; do\n\
  [ ! -f "/app/data/models/$(basename $f)" ] && cp "$f" /app/data/models/;\n\
done\n\
exec "$@"\n' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENV PYTHONUNBUFFERED=1
# Kronos has no setup.py — add its directory to PYTHONPATH directly
ENV PYTHONPATH=/app/src:/app/third_party/Kronos

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
