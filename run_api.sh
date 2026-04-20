#!/bin/bash
# Policonomy FastAPI 백엔드 실행
set -e

cd "$(dirname "$0")"

# .env 로드
if [ -f .env ]; then
  set -o allexport
  source .env
  set +o allexport
fi

echo "[Policonomy] FastAPI 서버 시작..."
echo "  API: http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo ""

conda run -n Policonomy uvicorn src.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir src
