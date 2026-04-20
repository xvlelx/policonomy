"""
주간 데이터 수집 모듈
매주 파이프라인 실행 시: 뉴스 sentiment + Kronos 예측 저장
다음 주 실행 시: 지난 주 실제 시장 결과 자동 업데이트

목적: 멀티모달 예측 모델 학습을 위한 데이터 누적
"""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import yfinance as yf
from logger import get_logger
from config import config

logger = get_logger('predictor.weekly_record')

_TICKERS = {
    'kospi': '^KS11',
    'usd_krw': 'KRW=X',
    'samsung': '005930.KS',
    'nasdaq': '^IXIC',
}

_SCHEMA = """
CREATE TABLE IF NOT EXISTS weekly_top_articles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    week        TEXT NOT NULL,              -- 'YYYY-MM-DD'
    rank        INTEGER NOT NULL,           -- 1~10
    title       TEXT,
    link        TEXT,
    category    TEXT,
    sentiment   TEXT,
    importance  INTEGER,
    one_line    TEXT,
    issue       TEXT,
    economic_impact TEXT,
    affected_sectors TEXT,                  -- JSON 배열
    keywords    TEXT                        -- JSON 배열
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_weekly_top_articles ON weekly_top_articles(week, rank);

CREATE TABLE IF NOT EXISTS weekly_records (
    week            TEXT PRIMARY KEY,   -- 'YYYY-MM-DD' (파이프라인 실행일)

    -- 뉴스 sentiment (카테고리별)
    total_articles  INTEGER,
    politics_pos    INTEGER, politics_neg INTEGER, politics_neu INTEGER,
    global_pos      INTEGER, global_neg  INTEGER, global_neu  INTEGER,
    tech_pos        INTEGER, tech_neg    INTEGER, tech_neu    INTEGER,
    realestate_pos  INTEGER, realestate_neg INTEGER, realestate_neu INTEGER,
    top_keywords    TEXT,               -- JSON 배열
    overall_sentiment TEXT,             -- positive / negative / neutral

    -- Kronos 예측 (이번 주 저장)
    kospi_pred_dir      TEXT,
    kospi_pred_change   REAL,
    usdkrw_pred_dir     TEXT,
    usdkrw_pred_change  REAL,
    samsung_pred_dir    TEXT,
    samsung_pred_change REAL,
    nasdaq_pred_dir     TEXT,
    nasdaq_pred_change  REAL,

    -- 실제 시장 결과 (다음 주 실행 시 채워짐)
    kospi_actual_change   REAL,
    usdkrw_actual_change  REAL,
    samsung_actual_change REAL,
    nasdaq_actual_change  REAL,

    -- 적중률 (다음 주 실행 시 채워짐)
    direction_hits  INTEGER,
    direction_total INTEGER,

    created_at  TEXT,
    verified_at TEXT
);
"""


class WeeklyRecorder:
    def __init__(self):
        self.db_path = config.paths.data / 'policonomy.db'
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(_SCHEMA)
        logger.info(f'DB 초기화: {self.db_path}')

    # ------------------------------------------------------------------ #
    # 1. 이번 주 기록 저장                                                 #
    # ------------------------------------------------------------------ #
    def save_week(self, analyzed: list[dict], predictions: dict) -> str:
        """파이프라인 완료 시 호출 — sentiment + 예측값 저장"""
        week = datetime.now().strftime('%Y-%m-%d')

        sentiment = self._calc_sentiment(analyzed)
        pred_row = self._flatten_predictions(predictions)

        row = {
            'week': week,
            'total_articles': len(analyzed),
            **sentiment,
            **pred_row,
            'created_at': datetime.now().isoformat(),
        }

        cols = ', '.join(row.keys())
        placeholders = ', '.join(':' + k for k in row.keys())
        with self._conn() as conn:
            conn.execute(
                f'INSERT OR REPLACE INTO weekly_records ({cols}) VALUES ({placeholders})',
                row
            )
        logger.info(f'주간 레코드 저장: {week} (기사 {len(analyzed)}개, sentiment={sentiment["overall_sentiment"]})')

        self._save_top_articles(week, analyzed)
        return week

    def _save_top_articles(self, week: str, analyzed: list[dict], top_n: int = 10) -> None:
        """importance 상위 N개 기사를 weekly_top_articles에 저장"""
        sorted_articles = sorted(analyzed, key=lambda a: a.get('importance', 0), reverse=True)
        top = sorted_articles[:top_n]

        with self._conn() as conn:
            conn.execute('DELETE FROM weekly_top_articles WHERE week = ?', (week,))
            for rank, a in enumerate(top, start=1):
                conn.execute("""
                    INSERT INTO weekly_top_articles
                        (week, rank, title, link, category, sentiment, importance,
                         one_line, issue, economic_impact, affected_sectors, keywords)
                    VALUES
                        (:week, :rank, :title, :link, :category, :sentiment, :importance,
                         :one_line, :issue, :economic_impact, :affected_sectors, :keywords)
                """, {
                    'week': week,
                    'rank': rank,
                    'title': a.get('title'),
                    'link': a.get('link'),
                    'category': a.get('category'),
                    'sentiment': a.get('sentiment'),
                    'importance': a.get('importance'),
                    'one_line': a.get('one_line'),
                    'issue': a.get('issue'),
                    'economic_impact': a.get('economic_impact'),
                    'affected_sectors': json.dumps(a.get('affected_sectors', []), ensure_ascii=False),
                    'keywords': json.dumps(a.get('keywords', []), ensure_ascii=False),
                })
        logger.info(f'주간 TOP {top_n} 기사 저장 완료: {week}')

    def _calc_sentiment(self, analyzed: list[dict]) -> dict:
        cats = {
            'politics_economy': ('politics_pos', 'politics_neg', 'politics_neu'),
            'global_macro':     ('global_pos',   'global_neg',   'global_neu'),
            'tech_industry':    ('tech_pos',      'tech_neg',     'tech_neu'),
            'real_estate':      ('realestate_pos','realestate_neg','realestate_neu'),
        }
        result = {}
        total_pos = total_neg = total_neu = 0

        for cat, (pk, nk, uk) in cats.items():
            articles = [a for a in analyzed if a.get('category') == cat]
            pos = sum(1 for a in articles if a.get('sentiment') == 'positive')
            neg = sum(1 for a in articles if a.get('sentiment') == 'negative')
            neu = len(articles) - pos - neg
            result[pk] = pos
            result[nk] = neg
            result[uk] = neu
            total_pos += pos; total_neg += neg; total_neu += neu

        # 전체 키워드 집계
        all_kw: dict[str, int] = {}
        for a in analyzed:
            for kw in a.get('keywords', []):
                all_kw[kw] = all_kw.get(kw, 0) + 1
        top_kw = sorted(all_kw, key=lambda k: all_kw[k], reverse=True)[:20]
        result['top_keywords'] = json.dumps(top_kw, ensure_ascii=False)

        # 전체 sentiment
        if total_neg > total_pos + total_neu:
            overall = 'negative'
        elif total_pos > total_neg + total_neu:
            overall = 'positive'
        else:
            overall = 'neutral'
        result['overall_sentiment'] = overall

        return result

    def _flatten_predictions(self, predictions: dict) -> dict:
        mapping = {
            'kospi': ('kospi_pred_dir', 'kospi_pred_change'),
            'usd_krw': ('usdkrw_pred_dir', 'usdkrw_pred_change'),
            'samsung': ('samsung_pred_dir', 'samsung_pred_change'),
            'nasdaq': ('nasdaq_pred_dir', 'nasdaq_pred_change'),
        }
        result = {}
        for name, (dk, ck) in mapping.items():
            p = predictions.get(name, {})
            result[dk] = p.get('direction')
            result[ck] = p.get('change_pct')
        return result

    # ------------------------------------------------------------------ #
    # 2. 지난 주 실제 결과 업데이트                                         #
    # ------------------------------------------------------------------ #
    def verify_last_week(self) -> dict | None:
        """파이프라인 시작 시 호출 — 지난 주 레코드에 실제 시장 결과 채우기"""
        with self._conn() as conn:
            row = conn.execute(
                'SELECT * FROM weekly_records WHERE verified_at IS NULL ORDER BY week DESC LIMIT 1'
            ).fetchone()

        if not row:
            logger.info('검증할 이전 주 레코드 없음')
            return None

        week = row['week']
        # 파이프라인 실행일 기준 7일 안 지났으면 아직 결과 집계 안 됨
        run_date = datetime.strptime(week, '%Y-%m-%d')
        if datetime.now() - run_date < timedelta(days=5):
            logger.info(f'{week} 레코드: 아직 5일 미경과, 검증 스킵')
            return None

        logger.info(f'{week} 레코드 실제 결과 수집 중...')
        actuals = self._fetch_actuals(run_date)
        if not actuals:
            return None

        hits = total = 0
        pred_dirs = {
            'kospi': row['kospi_pred_dir'],
            'usd_krw': row['usdkrw_pred_dir'],
            'samsung': row['samsung_pred_dir'],
            'nasdaq': row['nasdaq_pred_dir'],
        }
        for name, actual_change in actuals.items():
            actual_dir = '상승' if actual_change > 0 else '하락'
            pred_dir = pred_dirs.get(name)
            if pred_dir:
                total += 1
                if pred_dir == actual_dir:
                    hits += 1
                logger.info(f'  {name}: 예측 {pred_dir} → 실제 {actual_dir} {"✅" if pred_dir == actual_dir else "❌"} ({actual_change:+.2f}%)')

        with self._conn() as conn:
            conn.execute("""
                UPDATE weekly_records SET
                    kospi_actual_change   = :kospi,
                    usdkrw_actual_change  = :usd_krw,
                    samsung_actual_change = :samsung,
                    nasdaq_actual_change  = :nasdaq,
                    direction_hits  = :hits,
                    direction_total = :total,
                    verified_at = :ts
                WHERE week = :week
            """, {**actuals, 'hits': hits, 'total': total,
                  'ts': datetime.now().isoformat(), 'week': week})

        logger.info(f'{week} 검증 완료: {hits}/{total} 적중')
        return dict(row) | actuals | {'direction_hits': hits, 'direction_total': total}

    def _fetch_actuals(self, run_date: datetime) -> dict | None:
        """실행일 이후 실제 주간 등락률 계산"""
        try:
            end = run_date + timedelta(days=8)
            result = {}
            for name, ticker in _TICKERS.items():
                stock = yf.Ticker(ticker)
                df = stock.history(start=run_date.strftime('%Y-%m-%d'),
                                   end=end.strftime('%Y-%m-%d'))
                if len(df) < 2:
                    logger.warning(f'{ticker}: 데이터 부족')
                    return None
                start_price = float(df['Close'].iloc[0])
                end_price = float(df['Close'].iloc[-1])
                result[name] = round((end_price - start_price) / start_price * 100, 2)
            return result
        except Exception as e:
            logger.error(f'실제 결과 수집 실패: {e}')
            return None

    # ------------------------------------------------------------------ #
    # 3. 누적 통계 조회                                                    #
    # ------------------------------------------------------------------ #
    def get_stats(self) -> dict:
        with self._conn() as conn:
            rows = conn.execute(
                'SELECT * FROM weekly_records WHERE verified_at IS NOT NULL ORDER BY week'
            ).fetchall()

        if not rows:
            return {'weeks': 0, 'direction_accuracy': 0}

        total_hits = sum(r['direction_hits'] or 0 for r in rows)
        total_preds = sum(r['direction_total'] or 0 for r in rows)

        return {
            'weeks': len(rows),
            'direction_accuracy': round(total_hits / total_preds * 100, 1) if total_preds else 0,
            'total_predictions': total_preds,
            'records': [dict(r) for r in rows],
        }
