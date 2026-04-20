FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

COPY src ./src
COPY templates ./templates
COPY third_party/Kronos ./third_party/Kronos

RUN mkdir -p /app/data/models /app/logs

ENV PYTHONUNBUFFERED=1
# Kronos has no setup.py — add its directory to PYTHONPATH directly
ENV PYTHONPATH=/app/src:/app/third_party/Kronos

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
