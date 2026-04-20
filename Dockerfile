FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

# Kronos local package
COPY third_party/Kronos ./third_party/Kronos
RUN pip install --no-cache-dir ./third_party/Kronos

COPY src ./src
COPY templates ./templates

RUN mkdir -p /app/data/models /app/logs

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
