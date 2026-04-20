# Policonomy — Claude Code 컨텍스트

## Stack
- **Backend**: FastAPI (포트 8000) + SQLite + AWS SES
- **Frontend**: Next.js 16 + Tailwind + recharts (포트 3000)
- **LLM**: Groq API (스코어링: llama-3.1-8b-instant / 분석: llama-3.3-70b-versatile)
- **ML**: Kronos-small + XGBoost 앙상블
- **Scheduler**: crontab (매일 23:30 — 당일 뉴스 수집·분석·발송)
- **Python env**: conda `Policonomy`

## 현재 상태 (2026-04-18)
- [x] 코어 파이프라인 완료 (수집 → 분석 → 예측 → 리포트 → 발송)
- [x] XGBoost 학습 완료 (NASDAQ 82.2%, 삼성 81.9%, USD/KRW 79.3%, KOSPI 74.4%)
- [x] 2년치 backfill 완료 (backfill_records 1,385개)
- [x] 웹 대시보드 완료 (KOSPI / 미국시장 / 비공식지표 / Insights 탭)
- [x] TradingAgents (BullAgent vs BearAgent 토론)
- [x] AWS SES 구독자 이메일 발송
- [ ] 모바일 반응형 최적화 (베타 전 필수)
- [ ] 베타 오픈 (10~20명 → 100명)
- [ ] Google OAuth 구독자 로그인

## 다음 우선순위
1. 웹 모바일 반응형 개선
2. 베타 오픈
3. Google OAuth
4. OpenBB (yfinance 보완)
5. FinRL (강화학습 예측)

## 스킬 규칙
- 프론트엔드 작업: `frontend-dev` + `uxui-design`
- 백엔드/파이프라인 작업: `backend-dev`
- 코드 완성 후: `/simplify` → `qa-review`

## 주요 실행 명령
```bash
# 파이프라인
conda run -n Policonomy python src/pipeline.py

# 백엔드
./run_api.sh

# 프론트엔드
cd frontend && npm run dev
```

## 주의사항
- Stripe 결제는 제거됨 (나중에 재고 가능)
- Kronos는 subprocess 격리 실행 (macOS MPS segfault 방지)
- XGBoost 모델 경로: `data/models/`
- DB 경로: `data/policonomy.db` (루트 `policonomy.db`는 구버전)
