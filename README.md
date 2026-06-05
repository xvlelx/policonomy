# Policonomy

경제 뉴스를 매일 자동으로 수집·분석·예측하고, 구독자에게 이메일로 발송하는 파이프라인 서비스.

## 핵심 기능

- **자동 뉴스 수집**: 국내외 경제 RSS 피드에서 매일 뉴스 수집
- **LLM 중요도 분석**: Groq API(LLaMA)로 기사별 중요도 스코어링 + 심층 분석
- **시장 예측**: Kronos(시계열 트랜스포머) + XGBoost 앙상블 — KOSPI·나스닥·환율 방향 예측
- **대시보드**: Next.js 기반 실시간 웹 대시보드 (KOSPI / 미국시장 / 비공식지표 / Insights)
- **이메일 발송**: AWS SES로 구독자에게 HTML 뉴스레터 자동 발송

## 예측 정확도 (방향 적중률)

| 지표 | 모델 | 적중률 |
|------|------|--------|
| NASDAQ | XGBoost | 82.2% |
| 삼성전자 | XGBoost | 81.9% |
| USD/KRW | XGBoost | 79.3% |
| KOSPI | XGBoost | 74.4% |

## 아키텍처

```
RSS 수집 → LLM 스코어링 (llama-3.1-8b) → 심층분석 (llama-3.3-70b)
       → XGBoost + Kronos 앙상블 예측
       → FastAPI 백엔드 → Next.js 대시보드
       → AWS SES 이메일 발송
```

## 스택

| 레이어 | 기술 |
|--------|------|
| Backend | FastAPI · Python · SQLite |
| Frontend | Next.js 16 · Tailwind · recharts |
| LLM | Groq API (LLaMA 3.1 8B / 3.3 70B) |
| ML | Kronos-small · XGBoost |
| Deploy | Railway (backend) · Vercel (frontend) |
| Email | AWS SES |

## 실행 방법

```bash
# 환경 설정
cp .env.example .env
# .env에 GROQ_API_KEY, AWS 키 등 입력

# 파이프라인 실행 (뉴스 수집 → 분석 → 예측 → 발송)
conda run -n Policonomy python src/pipeline.py

# API 서버
./run_api.sh

# 프론트엔드
cd frontend && npm install && npm run dev
```

## 환경변수

```
GROQ_API_KEY=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SES_REGION=
ADMIN_KEY=
```

## 파이프라인 흐름

```
pipeline.py
  ├── collector/rss.py          # RSS 수집 + 키워드 필터
  ├── analyzer/llm.py           # LLM 스코어링 + 심층분석
  ├── predictor/kronos.py       # Kronos 시계열 예측
  ├── predictor/tracker.py      # XGBoost 예측 + 앙상블
  ├── predictor/fusion.py       # TradingAgents (Bull vs Bear 토론)
  ├── analyzer/report_generator.py  # 리포트 생성
  └── publisher/email.py        # AWS SES 발송
```
