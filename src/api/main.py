import contextlib
import json
import logging
import math
import os
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('api')

_SRC_DIR = str(Path(__file__).parent.parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from fastapi import FastAPI, Query, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

_ADMIN_KEY = os.environ.get('POLICONOMY_ADMIN_KEY', '')
if not _ADMIN_KEY:
    logger.warning('POLICONOMY_ADMIN_KEY가 설정되지 않았습니다. 관리자 API가 비활성화됩니다.')

from .settings import router as settings_router

# 경로 설정
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'

app = FastAPI(title='Policonomy API', version='1.0.0')
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_CORS_ORIGINS = [o.strip() for o in os.environ.get(
    'CORS_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000'
).split(',') if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization', 'X-Admin-Key'],
)

app.include_router(settings_router)


@app.get('/health')
def health():
    return {'status': 'ok'}


def _db_connect(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.row_factory = sqlite3.Row
    return conn


_ALLOWED_FILES = {'analyzed_articles.json', 'predictions.json', 'raw_articles.json'}
_VALID_CATEGORIES = {'politics_economy', 'global_macro', 'tech_industry', 'real_estate'}
_VALID_SENTIMENTS = {'positive', 'negative', 'neutral', 'cautious', 'mixed'}

def _sanitize_floats(obj):
    """NaN, Infinity를 None으로 변환 (JSON 직렬화 호환)"""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_floats(i) for i in obj]
    return obj


def _load_json(filename: str):
    if filename not in _ALLOWED_FILES:
        raise ValueError(f'허용되지 않은 파일: {filename}')
    resolved = (DATA_DIR / filename).resolve()
    if not resolved.is_relative_to(DATA_DIR.resolve()) or resolved != DATA_DIR.resolve() / filename:
        raise ValueError('경로 이탈 감지')
    path = resolved
    if not path.exists():
        return None
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    return _sanitize_floats(data)


def _parse_pipeline_status() -> dict:
    status_path = DATA_DIR / 'pipeline_status.json'
    if status_path.exists():
        try:
            data = json.loads(status_path.read_text(encoding='utf-8'))
            progress = data.get('progress')
            total = data.get('total')
            pct = round(progress / total * 100, 1) if progress is not None and total and total > 0 else None
            return {
                'status': data.get('status', 'unknown'),
                'stage': data.get('stage'),
                'progress': progress,
                'total': total,
                'progress_pct': pct,
                'last_updated': data.get('last_updated'),
            }
        except Exception:
            pass
    return {
        'status': 'unknown',
        'stage': None,
        'progress': None,
        'total': None,
        'progress_pct': None,
        'last_updated': None,
    }


@app.get('/api/articles')
def get_articles(
    category: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    min_importance: int = Query(4, ge=1, le=10),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query('importance'),  # importance | latest
    is_urgent: Optional[bool] = Query(None),
):
    if category and category not in _VALID_CATEGORIES:
        raise HTTPException(status_code=422, detail=f'유효하지 않은 카테고리: {category}')
    if sentiment and sentiment not in _VALID_SENTIMENTS:
        raise HTTPException(status_code=422, detail=f'유효하지 않은 감성: {sentiment}')

    articles = _load_json('analyzed_articles.json')
    if articles is None:
        return {'items': [], 'total': 0, 'page': page, 'pages': 0}

    # 필터
    if category:
        articles = [a for a in articles if a.get('category') == category]
    if sentiment:
        articles = [a for a in articles if a.get('sentiment') == sentiment]
    if is_urgent is not None:
        articles = [a for a in articles if bool(a.get('is_urgent')) == is_urgent]
    articles = [a for a in articles if a.get('importance', 0) >= min_importance]

    # 정렬
    if sort == 'importance':
        articles = sorted(articles, key=lambda x: x.get('importance', 0), reverse=True)

    total = len(articles)
    pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size

    return {
        'items': articles[start:end],
        'total': total,
        'page': page,
        'pages': pages,
    }


@app.get('/api/articles/stats')
def get_article_stats():
    articles = _load_json('analyzed_articles.json')
    if articles is None:
        return {}

    categories = {}
    sentiments = {'positive': 0, 'negative': 0, 'neutral': 0}
    sectors = {}

    for a in articles:
        cat = a.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

        sent = a.get('sentiment', 'neutral')
        sentiments[sent] = sentiments.get(sent, 0) + 1

        for s in a.get('affected_sectors', []):
            sectors[s] = sectors.get(s, 0) + 1

    top_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:8]

    return {
        'total_articles': len(articles),
        'by_category': categories,
        'by_sentiment': sentiments,
        'top_sectors': [{'name': s, 'count': c} for s, c in top_sectors],
    }


@app.get('/api/predictions')
def get_predictions():
    data = _load_json('predictions.json')
    return data if data is not None else {}


@app.get('/api/pipeline/status')
def get_pipeline_status():
    return _parse_pipeline_status()


@app.get('/api/newsletter', response_class=HTMLResponse)
def get_newsletter():
    path = DATA_DIR / 'newsletter.html'
    if not path.exists():
        raise HTTPException(status_code=404, detail='뉴스레터 없음')
    return HTMLResponse(content=path.read_text(encoding='utf-8'))


@app.get('/api/stats/summary')
def get_summary():
    """대시보드 상단 요약 카드용"""
    articles = _load_json('analyzed_articles.json') or []
    predictions = _load_json('predictions.json') or {}
    pipeline = _parse_pipeline_status()

    fused = predictions.get('fused_analysis', {})
    kronos = predictions.get('kronos_predictions', {})

    kospi = kronos.get('kospi', {})
    usd_krw = kronos.get('usd_krw', {})

    # 누적 적중률 (daily_records)
    accuracy = {'days': 0, 'direction_accuracy': 0, 'total_predictions': 0}
    db_path = DATA_DIR / 'policonomy.db'
    if db_path.exists():
        try:
            with contextlib.closing(_db_connect(db_path)) as conn:
                tables = [r[0] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()]
                if 'daily_records' in tables:
                    row = conn.execute("""
                        SELECT COUNT(*) AS days,
                               SUM(direction_hits) AS hits,
                               SUM(direction_total) AS total
                        FROM daily_records WHERE verified_at IS NOT NULL
                    """).fetchone()
                    if row and row[2]:
                        accuracy = {
                            'days': row[0],
                            'direction_accuracy': round((row[1] or 0) / row[2] * 100, 1),
                            'total_predictions': row[2],
                        }
        except Exception as e:
            logger.warning(f'누적 적중률 조회 실패: {e}')

    return {
        'pipeline': pipeline,
        'articles_analyzed': len(articles),
        'generated_at': predictions.get('generated_at'),
        'overall_sentiment': fused.get('overall_sentiment'),
        'weekly_summary': fused.get('weekly_summary'),
        'accuracy': accuracy,
        'kospi': {
            'last_close': kospi.get('last_close'),
            'pred_close': kospi.get('pred_close'),
            'change_pct': kospi.get('change_pct'),
            'direction': kospi.get('direction'),
        },
        'usd_krw': {
            'last_close': usd_krw.get('last_close'),
            'pred_close': usd_krw.get('pred_close'),
            'change_pct': usd_krw.get('change_pct'),
            'direction': usd_krw.get('direction'),
        },
    }


@app.get('/api/articles/daily-top')
def get_daily_top_articles(day: Optional[str] = Query(None)):
    """일간 TOP 10 기사 조회 — day 미지정 시 최신 날짜 반환"""
    db_path = DATA_DIR / 'policonomy.db'
    if not db_path.exists():
        raise HTTPException(status_code=404, detail='DB 없음')
    try:
        with contextlib.closing(_db_connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if day:
                datetime.strptime(day, '%Y-%m-%d')
                rows = conn.execute(
                    'SELECT * FROM daily_top_articles WHERE day = ? ORDER BY rank',
                    (day,)
                ).fetchall()
            else:
                latest = conn.execute(
                    'SELECT MAX(day) AS d FROM daily_top_articles'
                ).fetchone()['d']
                if not latest:
                    return {'day': None, 'articles': []}
                rows = conn.execute(
                    'SELECT * FROM daily_top_articles WHERE day = ? ORDER BY rank',
                    (latest,)
                ).fetchall()
                day = latest
    except ValueError:
        raise HTTPException(status_code=422, detail='day 형식 오류 (YYYY-MM-DD)')
    except Exception as e:
        logger.error(f'daily-top 조회 오류: {e}')
        raise HTTPException(status_code=500, detail='데이터 조회 중 오류가 발생했습니다')

    articles = []
    for r in rows:
        a = dict(r)
        for field in ('affected_sectors', 'keywords'):
            try:
                a[field] = json.loads(a[field]) if a[field] else []
            except Exception:
                a[field] = []
        articles.append(a)

    return {'day': day, 'articles': articles}


@app.get('/api/articles/daily-top/days')
def get_daily_top_days():
    """daily_top_articles에 존재하는 날짜 목록 반환"""
    db_path = DATA_DIR / 'policonomy.db'
    if not db_path.exists():
        raise HTTPException(status_code=404, detail='DB 없음')
    try:
        with contextlib.closing(_db_connect(db_path)) as conn:
            days = [r[0] for r in conn.execute(
                'SELECT DISTINCT day FROM daily_top_articles ORDER BY day DESC'
            ).fetchall()]
    except Exception as e:
        logger.error(f'daily-top/days 조회 오류: {e}')
        raise HTTPException(status_code=500, detail='데이터 조회 중 오류가 발생했습니다')
    return {'days': days}


@app.get('/api/articles/weekly-top')
def get_weekly_top_articles(week: Optional[str] = Query(None)):
    """주간 TOP 10 기사 조회 — week 미지정 시 최신 주 반환"""
    db_path = DATA_DIR / 'policonomy.db'
    if not db_path.exists():
        raise HTTPException(status_code=404, detail='DB 없음')
    try:
        with contextlib.closing(_db_connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            if week:
                # 입력 검증: YYYY-MM-DD 형식만 허용
                datetime.strptime(week, '%Y-%m-%d')
                rows = conn.execute(
                    'SELECT * FROM weekly_top_articles WHERE week = ? ORDER BY rank',
                    (week,)
                ).fetchall()
            else:
                latest = conn.execute(
                    'SELECT MAX(week) AS w FROM weekly_top_articles'
                ).fetchone()['w']
                if not latest:
                    return {'week': None, 'articles': []}
                rows = conn.execute(
                    'SELECT * FROM weekly_top_articles WHERE week = ? ORDER BY rank',
                    (latest,)
                ).fetchall()
                week = latest
    except ValueError:
        raise HTTPException(status_code=422, detail='week 형식 오류 (YYYY-MM-DD)')
    except Exception as e:
        logger.error(f'weekly-top 조회 오류: {e}')
        raise HTTPException(status_code=500, detail='데이터 조회 중 오류가 발생했습니다')

    articles = []
    for r in rows:
        a = dict(r)
        for field in ('affected_sectors', 'keywords'):
            try:
                a[field] = json.loads(a[field]) if a[field] else []
            except Exception:
                a[field] = []
        articles.append(a)

    return {'week': week, 'articles': articles}


@app.get('/api/articles/weekly-top/weeks')
def get_weekly_top_weeks():
    """weekly_top_articles에 존재하는 주 목록 반환"""
    db_path = DATA_DIR / 'policonomy.db'
    if not db_path.exists():
        raise HTTPException(status_code=404, detail='DB 없음')
    try:
        with contextlib.closing(_db_connect(db_path)) as conn:
            weeks = [r[0] for r in conn.execute(
                'SELECT DISTINCT week FROM weekly_top_articles ORDER BY week DESC'
            ).fetchall()]
    except Exception as e:
        logger.error(f'weekly-top/weeks 조회 오류: {e}')
        raise HTTPException(status_code=500, detail='데이터 조회 중 오류가 발생했습니다')
    return {'weeks': weeks}


class SubscribeRequest(BaseModel):
    email: EmailStr
    name: str = ''


@app.post('/api/subscribe')
@limiter.limit('5/hour')
def subscribe(request: Request, req: SubscribeRequest):
    from publisher.email import EmailSender
    sender = EmailSender()
    email = req.email.strip().lower()
    name = req.name.strip()
    token = sender.subscribe(email, name)
    if token is None:
        raise HTTPException(status_code=500, detail='구독 등록 실패')
    sender.send_confirmation_email(email, name, token)
    return {'success': True, 'email': req.email, 'pending_confirmation': True}


@app.get('/api/confirm')
def confirm_subscription(token: str = Query(...)):
    from publisher.email import EmailSender
    sender = EmailSender()
    ok = sender.confirm(token)
    if not ok:
        raise HTTPException(status_code=400, detail='유효하지 않거나 만료된 토큰')
    return {'success': True}


@app.post('/api/unsubscribe')
def unsubscribe(req: SubscribeRequest):
    from publisher.email import EmailSender
    sender = EmailSender()
    sender.unsubscribe(req.email.strip().lower())
    return {'success': True}


@app.get('/api/subscribers')
@limiter.limit('20/hour')
def get_subscribers(request: Request, x_admin_key: str = Header(default='')):
    if not _ADMIN_KEY or x_admin_key != _ADMIN_KEY:
        raise HTTPException(status_code=403, detail='인증 실패')
    from publisher.email import EmailSender
    sender = EmailSender()
    return {'subscribers': sender.list_subscribers()}


@app.get('/api/insights/weekly')
def get_weekly_insights():
    """daily_records를 7일 단위로 집계해서 주간 인사이트 반환"""
    db_path = DATA_DIR / 'policonomy.db'
    if not db_path.exists():
        return {'weeks': []}
    try:
        with contextlib.closing(_db_connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            # daily_records 테이블 존재 확인
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            if 'daily_records' not in tables:
                return {'weeks': []}

            rows = conn.execute("""
                SELECT
                    strftime('%Y-W%W', day) AS week_label,
                    MIN(day) AS week_start,
                    MAX(day) AS week_end,
                    COUNT(*) AS days_count,
                    SUM(total_articles) AS total_articles,
                    AVG(CAST(politics_pos - politics_neg AS REAL) / NULLIF(total_articles,0)) AS avg_politics_sentiment,
                    AVG(CAST(global_pos - global_neg AS REAL) / NULLIF(total_articles,0)) AS avg_global_sentiment,
                    AVG(CAST(tech_pos - tech_neg AS REAL) / NULLIF(total_articles,0)) AS avg_tech_sentiment,
                    AVG(CAST(realestate_pos - realestate_neg AS REAL) / NULLIF(total_articles,0)) AS avg_realestate_sentiment,
                    SUM(CASE WHEN verified_at IS NOT NULL THEN direction_hits ELSE 0 END) AS total_hits,
                    SUM(CASE WHEN verified_at IS NOT NULL THEN direction_total ELSE 0 END) AS total_preds,
                    AVG(CASE WHEN verified_at IS NOT NULL THEN kospi_actual_change END) AS avg_kospi_change,
                    AVG(CASE WHEN verified_at IS NOT NULL THEN nasdaq_actual_change END) AS avg_nasdaq_change
                FROM daily_records
                GROUP BY week_label
                ORDER BY week_start DESC
                LIMIT 12
            """).fetchall()
    except Exception as e:
        logger.error(f'weekly-insights 조회 오류: {e}')
        raise HTTPException(status_code=500, detail='데이터 조회 중 오류가 발생했습니다')

    weeks = []
    for r in rows:
        d = dict(r)
        hits = d.get('total_hits') or 0
        preds = d.get('total_preds') or 0
        d['accuracy'] = round(hits / preds * 100, 1) if preds > 0 else None
        weeks.append(d)
    return {'weeks': weeks}


@app.get('/api/predictions/history')
def get_predictions_history():
    """일별 예측 vs 실제 결과 히스토리 (차트용)"""
    db_path = DATA_DIR / 'policonomy.db'
    if not db_path.exists():
        return {'records': []}
    try:
        with contextlib.closing(_db_connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            if 'daily_records' not in tables:
                return {'records': []}
            rows = conn.execute("""
                SELECT
                    day,
                    kospi_pred_dir, kospi_actual_change,
                    usdkrw_pred_dir, usdkrw_actual_change,
                    samsung_pred_dir, samsung_actual_change,
                    skhynix_pred_dir, skhynix_actual_change,
                    nasdaq_pred_dir, nasdaq_actual_change,
                    sp500_pred_dir, sp500_actual_change,
                    dow_pred_dir, dow_actual_change,
                    nvidia_pred_dir, nvidia_actual_change,
                    direction_hits, direction_total,
                    verified_at
                FROM daily_records
                ORDER BY day DESC
                LIMIT 90
            """).fetchall()
            rows = list(reversed(rows))
    except Exception as e:
        logger.error(f'predictions-history 조회 오류: {e}')
        raise HTTPException(status_code=500, detail='데이터 조회 중 오류가 발생했습니다')

    records = []
    cumulative_hits = 0
    cumulative_total = 0
    for r in rows:
        d = dict(r)
        hits = d.get('direction_hits') or 0
        total = d.get('direction_total') or 0
        cumulative_hits += hits
        cumulative_total += total
        d['cumulative_accuracy'] = round(cumulative_hits / cumulative_total * 100, 1) if cumulative_total > 0 else None
        d['daily_accuracy'] = round(hits / total * 100, 1) if total > 0 else None
        records.append(d)
    return {'records': records}


@app.get('/api/insights/market-correlation')
def get_market_correlation(days: int = Query(default=60, ge=7, le=365)):
    """뉴스 감성 vs 실제 시장 등락 상관 데이터"""
    db_path = DATA_DIR / 'policonomy.db'
    if not db_path.exists():
        return {'data': []}
    try:
        with contextlib.closing(_db_connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT
                    day,
                    politics_pos, politics_neg, politics_neu,
                    global_pos, global_neg, global_neu,
                    tech_pos, tech_neg, tech_neu,
                    overall_sentiment,
                    kospi_actual_change,
                    usdkrw_actual_change,
                    samsung_actual_change,
                    skhynix_actual_change,
                    nasdaq_actual_change,
                    sp500_actual_change,
                    dow_actual_change,
                    nvidia_actual_change
                FROM daily_records
                WHERE kospi_actual_change IS NOT NULL
                ORDER BY day DESC
                LIMIT ?
            """, (days,)).fetchall()
    except Exception as e:
        logger.error(f'market-correlation 조회 오류: {e}')
        raise HTTPException(status_code=500, detail='데이터 조회 중 오류가 발생했습니다')

    result = []
    for r in reversed(rows):
        d = dict(r)
        # 카테고리별 감성 점수 계산 (-1 ~ +1)
        def _score(pos, neg, neu):
            total = (pos or 0) + (neg or 0) + (neu or 0)
            if total == 0:
                return None
            return round(((pos or 0) - (neg or 0)) / total, 3)

        politics_score = _score(d.get('politics_pos'), d.get('politics_neg'), d.get('politics_neu'))
        global_score = _score(d.get('global_pos'), d.get('global_neg'), d.get('global_neu'))
        tech_score = _score(d.get('tech_pos'), d.get('tech_neg'), d.get('tech_neu'))
        combined = None
        scores = [s for s in [politics_score, global_score, tech_score] if s is not None]
        if scores:
            combined = round(sum(scores) / len(scores), 3)

        result.append({
            'day': d['day'],
            'politics_score': politics_score,
            'global_score': global_score,
            'tech_score': tech_score,
            'combined_sentiment': combined,
            'overall_sentiment': d.get('overall_sentiment'),
            'kospi_change': d.get('kospi_actual_change'),
            'usdkrw_change': d.get('usdkrw_actual_change'),
            'samsung_change': d.get('samsung_actual_change'),
            'skhynix_change': d.get('skhynix_actual_change'),
            'nasdaq_change': d.get('nasdaq_actual_change'),
            'sp500_change': d.get('sp500_actual_change'),
            'dow_change': d.get('dow_actual_change'),
            'nvidia_change': d.get('nvidia_actual_change'),
        })
    return {'data': result}


@app.get('/api/insights/sector-trends')
def get_sector_trends():
    """최근 7일 vs 이전 7일 섹터별 감성 비교"""
    db_path = DATA_DIR / 'policonomy.db'
    if not db_path.exists():
        return {'trends': []}
    try:
        with contextlib.closing(_db_connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT
                    day,
                    politics_pos, politics_neg, politics_neu,
                    global_pos, global_neg, global_neu,
                    tech_pos, tech_neg, tech_neu,
                    realestate_pos, realestate_neg, realestate_neu
                FROM daily_records
                ORDER BY day DESC
                LIMIT 14
            """).fetchall()
    except Exception as e:
        logger.error(f'sector-trends 조회 오류: {e}')
        raise HTTPException(status_code=500, detail='데이터 조회 중 오류가 발생했습니다')

    if len(rows) < 2:
        return {'trends': [], 'has_data': False}

    recent = list(rows[:7])
    prev = list(rows[7:14])

    def _avg_score(records, pos_col, neg_col, neu_col):
        scores = []
        for r in records:
            d = dict(r)
            total = (d.get(pos_col) or 0) + (d.get(neg_col) or 0) + (d.get(neu_col) or 0)
            if total > 0:
                scores.append(((d.get(pos_col) or 0) - (d.get(neg_col) or 0)) / total)
        return round(sum(scores) / len(scores), 3) if scores else None

    sectors = [
        {'key': 'politics', 'label': '정치·경제', 'pos': 'politics_pos', 'neg': 'politics_neg', 'neu': 'politics_neu'},
        {'key': 'global', 'label': '글로벌', 'pos': 'global_pos', 'neg': 'global_neg', 'neu': 'global_neu'},
        {'key': 'tech', 'label': '테크', 'pos': 'tech_pos', 'neg': 'tech_neg', 'neu': 'tech_neu'},
        {'key': 'realestate', 'label': '부동산', 'pos': 'realestate_pos', 'neg': 'realestate_neg', 'neu': 'realestate_neu'},
    ]

    trends = []
    for s in sectors:
        recent_score = _avg_score(recent, s['pos'], s['neg'], s['neu'])
        prev_score = _avg_score(prev, s['pos'], s['neg'], s['neu'])
        if recent_score is None:
            direction = 'flat'
            delta = None
        elif prev_score is None:
            direction = 'flat'
            delta = None
        else:
            delta = round(recent_score - prev_score, 3)
            if delta > 0.05:
                direction = 'up'
            elif delta < -0.05:
                direction = 'down'
            else:
                direction = 'flat'
        trends.append({
            'key': s['key'],
            'label': s['label'],
            'recent_score': recent_score,
            'prev_score': prev_score,
            'delta': delta,
            'direction': direction,
        })
    return {'trends': trends, 'has_data': True, 'recent_days': len(recent), 'prev_days': len(prev)}


@app.get('/api/articles/related')
def get_related_articles(market: str = Query(...)):
    """시장별 관련 기사"""
    MARKET_KEYWORDS: dict[str, list[str]] = {
        'kospi': ['코스피', '주가', '증시', '한국 주식', '삼성', 'SK하이닉스', '현대차'],
        'usd_krw': ['환율', '달러', '원화', '달러/원', '외환'],
        'nasdaq': ['나스닥', '미국 증시', '미국 주식', '실리콘밸리', 'AI', '빅테크'],
        'samsung': ['삼성전자', '삼성', '반도체', 'HBM', '스마트폰'],
    }
    MARKET_CATEGORIES: dict[str, list[str]] = {
        'kospi': ['politics_economy', 'tech_industry'],
        'usd_krw': ['politics_economy', 'global_macro'],
        'nasdaq': ['global_macro', 'tech_industry'],
        'samsung': ['tech_industry', 'politics_economy'],
    }

    if market not in MARKET_KEYWORDS:
        raise HTTPException(status_code=400, detail=f'지원하지 않는 마켓: {market}. 허용: {list(MARKET_KEYWORDS.keys())}')

    keywords = [kw.lower() for kw in MARKET_KEYWORDS[market]]
    target_cats = MARKET_CATEGORIES[market]

    data = _load_json('analyzed_articles.json')
    if not data:
        return {'articles': []}

    articles = data if isinstance(data, list) else data.get('articles', [])

    scored = []
    for art in articles:
        title = (art.get('title') or '').lower()
        summary = (art.get('summary') or '').lower()
        cat = art.get('category', '')
        text = title + ' ' + summary

        score = sum(1 for kw in keywords if kw in text)
        if cat in target_cats:
            score += 1
        if score > 0:
            scored.append((score, art))

    scored.sort(key=lambda x: (-x[0], -(x[1].get('importance', 0) or 0)))
    top = [a for _, a in scored[:5]]

    return {'articles': top, 'market': market}


@app.post('/api/pipeline/run')
@limiter.limit('5/hour')
def run_pipeline(request: Request, x_admin_key: str = Header(default='')):
    if not _ADMIN_KEY or x_admin_key != _ADMIN_KEY:
        raise HTTPException(status_code=403, detail='인증 실패')

    import subprocess
    import sys

    # 락파일로 중복 실행 방지
    lock_path = DATA_DIR / '.pipeline.lock'
    status_path = DATA_DIR / 'pipeline_status.json'

    if lock_path.exists():
        try:
            pid = int(lock_path.read_text().strip())
            import os as _os
            _os.kill(pid, 0)
            raise HTTPException(status_code=409, detail='파이프라인이 이미 실행 중입니다')
        except (ValueError, ProcessLookupError, PermissionError):
            lock_path.unlink(missing_ok=True)

    runner_path = BASE_DIR / 'src' / 'pipeline_runner.py'
    env = os.environ.copy()
    env['PYTHONPATH'] = str(BASE_DIR / 'src')

    proc = subprocess.Popen(
        [sys.executable, str(runner_path)],
        cwd=str(BASE_DIR),
        env=env,
        start_new_session=True,
    )
    return {'started': True, 'pid': proc.pid}


@app.get('/api/fear-greed')
def get_fear_greed(refresh: bool = Query(False)):
    """CNN Fear & Greed Index 반환. refresh=true 시 실시간 수집"""
    from collector.fear_greed import FearGreedCollector

    collector = FearGreedCollector(DATA_DIR)

    if refresh:
        return collector.fetch()

    # 캐시 우선 반환
    cache_path = DATA_DIR / 'fear_greed.json'
    if cache_path.exists():
        try:
            data = json.loads(cache_path.read_text(encoding='utf-8'))
            return data
        except Exception:
            pass

    # 캐시 없으면 실시간 수집
    return collector.fetch()


@app.get('/api/reports')
def get_reports_list():
    """저장된 리포트 세션 목록 — {dates: [...], sessions: [{date, run_type}]}"""
    from analyzer.report_generator import ReportGenerator
    gen = ReportGenerator(DATA_DIR)
    sessions = gen.list_sessions()
    return {'dates': gen.list_dates(), 'sessions': sessions}


@app.get('/api/reports/latest')
def get_latest_report(generate: bool = Query(False)):
    """최신 리포트 반환. generate=true 시 새로 생성"""
    from analyzer.report_generator import ReportGenerator
    gen = ReportGenerator(DATA_DIR)

    if generate:
        return gen.generate()

    report = gen.load_latest()
    if report is None:
        return gen.generate()
    return report


@app.get('/api/reports/{date}')
def get_report_by_date(date: str, run_type: str = Query('morning')):
    """날짜별 리포트 조회. run_type = morning | afternoon"""
    import re
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date):
        raise HTTPException(status_code=422, detail='날짜 형식 오류 (YYYY-MM-DD)')
    if run_type not in ('morning', 'afternoon'):
        raise HTTPException(status_code=422, detail='run_type은 morning 또는 afternoon')
    from analyzer.report_generator import ReportGenerator
    gen = ReportGenerator(DATA_DIR)
    report = gen.load_by_date(date, run_type)
    if report is None:
        raise HTTPException(status_code=404, detail=f'{date} {run_type} 리포트 없음')
    return report


@app.get('/api/hedge-funds')
def get_hedge_funds(force: bool = Query(False)):
    """SEC 13F 기반 헤지펀드 포지션 조회. force=true 시 캐시 무시하고 새로 수집"""
    from collector.sec_13f import HedgeFund13FCollector
    collector = HedgeFund13FCollector(DATA_DIR)
    return collector.collect(force=force)


@app.get('/api/health')
def health():
    return {'status': 'ok', 'timestamp': datetime.now().isoformat()}
