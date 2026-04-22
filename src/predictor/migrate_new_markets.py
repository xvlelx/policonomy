"""
backfill_records / weekly_records에 sp500/dow/nvidia/skhynix 컬럼 추가 및 데이터 채우기

실행:
    conda run -n Policonomy python src/predictor/migrate_new_markets.py
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import config
from logger import get_logger

logger = get_logger('predictor.migrate_new_markets')

_NEW_TICKERS = {
    'sp500': '^GSPC',
    'dow': '^DJI',
    'nvidia': 'NVDA',
    'skhynix': '000660.KS',
}

_DB_PATH = config.paths.data / 'policonomy.db'


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(_DB_PATH, timeout=30)
    c.execute('PRAGMA journal_mode=WAL')
    c.row_factory = sqlite3.Row
    return c


def _add_columns():
    with _conn() as conn:
        for market in _NEW_TICKERS:
            for table, extra_cols in [
                ('backfill_records', [f'{market}_actual_change', f'{market}_next_dir']),
                ('weekly_records',   [f'{market}_actual_change']),
                ('daily_records',    []),  # already has these columns
            ]:
                for col in extra_cols:
                    col_type = 'TEXT' if col.endswith('_dir') else 'REAL'
                    try:
                        conn.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_type}')
                        logger.info(f'Added {table}.{col}')
                    except sqlite3.OperationalError:
                        pass  # column already exists
    logger.info('컬럼 추가 완료')


def _fetch_weekly_returns(start: str = '2012-12-01') -> pd.DataFrame:
    logger.info('yfinance 주별 데이터 다운로드 중...')
    tickers = list(_NEW_TICKERS.values())
    df = yf.download(tickers, start=start, interval='1wk',
                     auto_adjust=True, progress=False)
    closes = df['Close'].copy()
    closes.columns = list(_NEW_TICKERS.keys())
    returns = closes.pct_change() * 100
    returns.index = pd.DatetimeIndex(returns.index).tz_localize(None).normalize()
    logger.info(f'다운로드 완료: {len(returns)}주')
    return returns


def _date_to_monday(date_str: str) -> str:
    """DB에 저장된 날짜를 해당 주 월요일로 정규화"""
    import datetime
    d = datetime.date.fromisoformat(date_str)
    monday = d - datetime.timedelta(days=d.weekday())
    return monday.isoformat()


def _update_backfill(returns: pd.DataFrame):
    with _conn() as conn:
        weeks = [r[0] for r in conn.execute(
            'SELECT week FROM backfill_records ORDER BY week'
        ).fetchall()]

    updates: list[tuple] = []
    for week_str in weeks:
        row: dict[str, float | None] = {}
        # yfinance 주간 데이터는 월요일 기준 — ±3일 이내 가장 가까운 날 찾기
        import datetime
        target = pd.Timestamp(week_str)
        for delta in range(0, 4):
            for sign in (0, 1, -1):
                candidate = target + pd.Timedelta(days=sign * delta)
                if candidate in returns.index:
                    for market in _NEW_TICKERS:
                        val = returns.at[candidate, market]
                        row[market] = None if pd.isna(val) else round(float(val), 4)
                    break
            if row:
                break
        if not row:
            row = {m: None for m in _NEW_TICKERS}

        updates.append((
            row.get('sp500'), row.get('dow'), row.get('nvidia'), row.get('skhynix'),
            week_str
        ))

    with _conn() as conn:
        conn.executemany(
            '''UPDATE backfill_records
               SET sp500_actual_change=?, dow_actual_change=?,
                   nvidia_actual_change=?, skhynix_actual_change=?
               WHERE week=?''',
            updates
        )
    logger.info(f'backfill_records {len(updates)}행 업데이트 완료')


def _compute_next_dirs():
    """현재 주의 actual_change를 보고 다음 주 방향 레이블 계산"""
    with _conn() as conn:
        rows = conn.execute(
            'SELECT week, sp500_actual_change, dow_actual_change, '
            'nvidia_actual_change, skhynix_actual_change '
            'FROM backfill_records ORDER BY week'
        ).fetchall()

    weeks = [dict(r) for r in rows]
    updates = []
    for i in range(len(weeks) - 1):
        cur = weeks[i]
        nxt = weeks[i + 1]
        dirs: dict[str, str | None] = {}
        for market in _NEW_TICKERS:
            val = nxt.get(f'{market}_actual_change')
            if val is None:
                dirs[market] = None
            else:
                dirs[market] = '상승' if val >= 0 else '하락'
        updates.append((
            dirs['sp500'], dirs['dow'], dirs['nvidia'], dirs['skhynix'],
            cur['week']
        ))

    with _conn() as conn:
        conn.executemany(
            '''UPDATE backfill_records
               SET sp500_next_dir=?, dow_next_dir=?,
                   nvidia_next_dir=?, skhynix_next_dir=?
               WHERE week=?''',
            updates
        )
    logger.info(f'next_dir 레이블 {len(updates)}행 계산 완료')


def _update_weekly_records(returns: pd.DataFrame):
    with _conn() as conn:
        weeks = [r[0] for r in conn.execute(
            'SELECT week FROM weekly_records ORDER BY week'
        ).fetchall()]

    if not weeks:
        logger.info('weekly_records 데이터 없음 — 건너뜀')
        return

    updates = []
    for week_str in weeks:
        import datetime
        target = pd.Timestamp(week_str)
        row: dict[str, float | None] = {}
        for delta in range(0, 4):
            for sign in (0, 1, -1):
                candidate = target + pd.Timedelta(days=sign * delta)
                if candidate in returns.index:
                    for market in _NEW_TICKERS:
                        val = returns.at[candidate, market]
                        row[market] = None if pd.isna(val) else round(float(val), 4)
                    break
            if row:
                break
        if not row:
            row = {m: None for m in _NEW_TICKERS}
        updates.append((
            row.get('sp500'), row.get('dow'), row.get('nvidia'), row.get('skhynix'),
            week_str
        ))

    with _conn() as conn:
        conn.executemany(
            '''UPDATE weekly_records
               SET sp500_actual_change=?, dow_actual_change=?,
                   nvidia_actual_change=?, skhynix_actual_change=?
               WHERE week=?''',
            updates
        )
    logger.info(f'weekly_records {len(updates)}행 업데이트 완료')


if __name__ == '__main__':
    logger.info('=== 신규 마켓 마이그레이션 시작 ===')
    _add_columns()
    returns = _fetch_weekly_returns()
    _update_backfill(returns)
    _compute_next_dirs()
    _update_weekly_records(returns)
    logger.info('=== 마이그레이션 완료 ===')
