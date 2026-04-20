"""
과거 데이터 백필: 2013-01-07 ~ 현재
GDELT 주별 뉴스 톤 + yfinance 주별 실제 등락률 → backfill_records 테이블

실행:
    conda run -n Policonomy python src/predictor/backfill.py
"""
import sqlite3
import time
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from logger import get_logger
from config import config

logger = get_logger('predictor.backfill')

_BACKFILL_SCHEMA = """
CREATE TABLE IF NOT EXISTS backfill_records (
    week                  TEXT PRIMARY KEY,  -- 'YYYY-MM-DD' (해당 주 월요일)

    -- GDELT 뉴스 sentiment
    gdelt_tone            REAL,              -- GDELT 평균 톤 (-15 ~ +15)
    sentiment_score       REAL,              -- 정규화 (-1 ~ +1)

    -- 해당 주 실제 등락률
    kospi_actual_change   REAL,
    usdkrw_actual_change  REAL,
    samsung_actual_change REAL,
    nasdaq_actual_change  REAL,

    -- 다음 주 방향 레이블 (학습용)
    kospi_next_dir        TEXT,
    usdkrw_next_dir       TEXT,
    samsung_next_dir      TEXT,
    nasdaq_next_dir       TEXT,

    source     TEXT DEFAULT 'backfill',
    created_at TEXT
);
"""

_TICKERS = {
    'kospi': '^KS11',
    'usd_krw': 'KRW=X',
    'samsung': '005930.KS',
    'nasdaq': '^IXIC',
}

_START_DATE = '2013-01-01'
_GDELT_QUERY = 'economy finance stock market GDP inflation trade interest rate'


class Backfiller:
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
            conn.executescript(_BACKFILL_SCHEMA)
        logger.info(f'backfill_records 테이블 초기화: {self.db_path}')

    # ------------------------------------------------------------------ #
    # 1. yfinance 주별 가격 데이터                                          #
    # ------------------------------------------------------------------ #
    def _fetch_price_data(self) -> pd.DataFrame:
        """2013 ~ 현재 주별 등락률 DataFrame 반환"""
        logger.info('yfinance 주별 가격 데이터 다운로드 중...')
        tickers = list(_TICKERS.values())
        end_date = datetime.now().strftime('%Y-%m-%d')

        df = yf.download(tickers, start=_START_DATE, end=end_date,
                         interval='1wk', auto_adjust=True, progress=False)

        closes = df['Close'].copy()
        closes.columns = list(_TICKERS.keys())

        # 주별 등락률 (%)
        returns = closes.pct_change() * 100
        returns.index = returns.index.tz_localize(None)
        returns.index = returns.index.normalize()

        logger.info(f'가격 데이터: {len(returns)}주 ({returns.index[0].date()} ~ {returns.index[-1].date()})')
        return returns

    # ------------------------------------------------------------------ #
    # 2. GDELT 주별 뉴스 톤                                                #
    # ------------------------------------------------------------------ #
    def _fetch_gdelt_year(self, year: int) -> dict[str, float]:
        """연도 단위로 GDELT timelinetone 조회"""
        url = 'https://api.gdeltproject.org/api/v2/doc/doc'
        params = {
            'query': _GDELT_QUERY,
            'startdatetime': f'{year}0101000000',
            'enddatetime': f'{year}1231235959',
            'mode': 'timelinetone',
            'timezoom': 'week',
            'format': 'json',
        }
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            result = {}
            for series in data.get('timeline', []):
                # 각 시리즈: {'data': [{'date': '20130107000000', 'value': -2.34}, ...]}
                for item in series.get('data', []):
                    raw_date = str(item.get('date', ''))[:8]
                    if len(raw_date) == 8:
                        week_str = f'{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}'
                        tone = float(item.get('value', 0))
                        result[week_str] = tone
            return result
        except Exception as e:
            logger.warning(f'GDELT {year}년 조회 실패: {e}')
            return {}

    def _fetch_all_gdelt(self) -> dict[str, float]:
        """2013 ~ 현재 연도별 GDELT 톤 일괄 수집"""
        start_year = 2013
        end_year = datetime.now().year
        all_tone: dict[str, float] = {}

        for year in range(start_year, end_year + 1):
            logger.info(f'GDELT {year}년 수집 중...')
            tone = self._fetch_gdelt_year(year)
            all_tone.update(tone)
            logger.info(f'  → {len(tone)}주 데이터')
            time.sleep(1.0)  # API 과부하 방지

        logger.info(f'GDELT 총 {len(all_tone)}주 데이터 수집 완료')
        return all_tone

    # ------------------------------------------------------------------ #
    # 3. 데이터 정렬 및 DB 저장                                             #
    # ------------------------------------------------------------------ #
    def _normalize_tone(self, tone: float) -> float:
        """GDELT 톤 → -1 ~ +1 정규화"""
        return max(-1.0, min(1.0, tone / 15.0))

    def run(self):
        logger.info('=== 백필 시작 ===')

        # 이미 저장된 주 확인
        with self._conn() as conn:
            existing = {r[0] for r in conn.execute(
                'SELECT week FROM backfill_records'
            ).fetchall()}
        logger.info(f'기존 백필 레코드: {len(existing)}주')

        # 가격 데이터
        price_df = self._fetch_price_data()

        # GDELT 톤
        gdelt_tone = self._fetch_all_gdelt()

        # 주 목록 (가격 데이터 기준)
        weeks = [str(idx.date()) for idx in price_df.index]
        inserted = skipped = 0

        for i, week in enumerate(weeks[1:], 1):  # 첫 주는 등락률 없음
            if week in existing:
                skipped += 1
                continue

            # 해당 주 가격 등락률
            row = price_df.iloc[i]
            if row.isna().any():
                continue

            # 다음 주 방향 레이블 (마지막 주는 레이블 없음)
            if i + 1 < len(weeks):
                next_row = price_df.iloc[i + 1]
            else:
                continue

            tone = gdelt_tone.get(week)
            score = self._normalize_tone(tone) if tone is not None else None

            record = {
                'week': week,
                'gdelt_tone': tone,
                'sentiment_score': score,
                'kospi_actual_change': float(row['kospi']) if not pd.isna(row['kospi']) else None,
                'usdkrw_actual_change': float(row['usd_krw']) if not pd.isna(row['usd_krw']) else None,
                'samsung_actual_change': float(row['samsung']) if not pd.isna(row['samsung']) else None,
                'nasdaq_actual_change': float(row['nasdaq']) if not pd.isna(row['nasdaq']) else None,
                'kospi_next_dir': '상승' if not pd.isna(next_row['kospi']) and next_row['kospi'] > 0 else '하락',
                'usdkrw_next_dir': '상승' if not pd.isna(next_row['usd_krw']) and next_row['usd_krw'] > 0 else '하락',
                'samsung_next_dir': '상승' if not pd.isna(next_row['samsung']) and next_row['samsung'] > 0 else '하락',
                'nasdaq_next_dir': '상승' if not pd.isna(next_row['nasdaq']) and next_row['nasdaq'] > 0 else '하락',
                'created_at': datetime.now().isoformat(),
            }

            with self._conn() as conn:
                cols = ', '.join(record.keys())
                placeholders = ', '.join(':' + k for k in record.keys())
                conn.execute(
                    f'INSERT OR REPLACE INTO backfill_records ({cols}) VALUES ({placeholders})',
                    record
                )
            inserted += 1

        logger.info(f'=== 백필 완료: {inserted}개 삽입, {skipped}개 스킵 ===')
        return {'inserted': inserted, 'skipped': skipped, 'total': inserted + skipped}


if __name__ == '__main__':
    bf = Backfiller()
    result = bf.run()
    print(result)
