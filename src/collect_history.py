"""
역사 데이터 수집 실행 스크립트
Usage:
    python3 src/collect_history.py             # 뉴스 2년치 수집
    python3 src/collect_history.py --stocks    # 주식 데이터만
    python3 src/collect_history.py --stats     # 수집 현황 조회
    python3 src/collect_history.py --days 90   # 최근 90일만
"""
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

DB_PATH = Path(__file__).parent.parent / 'policonomy.db'


def collect_stocks(days: int = 730):
    """2년치 주가 데이터 수집 → historical_prices 테이블"""
    import yfinance as yf

    TICKERS = {
        'kospi':   '^KS11',
        'usd_krw': 'KRW=X',
        'nasdaq':  '^IXIC',
        'samsung': '005930.KS',
    }

    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS historical_prices (
            date   TEXT NOT NULL,
            ticker TEXT NOT NULL,
            open   REAL,
            high   REAL,
            low    REAL,
            close  REAL,
            volume REAL,
            PRIMARY KEY (date, ticker)
        )
    ''')
    conn.commit()

    start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    total = 0

    for name, symbol in TICKERS.items():
        print(f'  {name} ({symbol}) 수집 중...')
        try:
            df = yf.download(symbol, start=start, progress=False, auto_adjust=True)
            if df.empty:
                print(f'    데이터 없음')
                continue

            # yfinance 최신 버전은 MultiIndex 컬럼 사용 — 평탄화
            if isinstance(df.columns, __import__('pandas').MultiIndex):
                df.columns = df.columns.get_level_values(0)

            saved = 0
            for ts, row in df.iterrows():
                date_str = ts.strftime('%Y-%m-%d')

                def _v(col):
                    val = row.get(col)
                    if val is None:
                        return None
                    try:
                        f = float(val)
                        return None if __import__('math').isnan(f) else f
                    except Exception:
                        return None

                conn.execute(
                    'INSERT OR REPLACE INTO historical_prices VALUES (?,?,?,?,?,?,?)',
                    (date_str, name, _v('Open'), _v('High'), _v('Low'), _v('Close'), _v('Volume'))
                )
                saved += 1
            conn.commit()
            print(f'    {saved}일치 저장 완료')
            total += saved
        except Exception as e:
            print(f'    실패: {e}')

    conn.close()
    print(f'\n주식 데이터: 총 {total}행 저장')


def show_stats():
    from collector.naver_history import get_stats
    s = get_stats()
    print('\n=== 역사 뉴스 수집 현황 ===')
    print(f'총 기사: {s["total"]:,}건')
    print(f'기간: {s["oldest"]} ~ {s["newest"]} ({s["days"]}일)')
    print('카테고리별:')
    for cat, cnt in s['by_category'].items():
        print(f'  {cat}: {cnt:,}건')

    # 주식 현황
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute('''
            SELECT ticker, COUNT(*), MIN(date), MAX(date)
            FROM historical_prices GROUP BY ticker
        ''').fetchall()
        if rows:
            print('\n=== 주식 데이터 현황 ===')
            for ticker, cnt, oldest, newest in rows:
                print(f'  {ticker}: {cnt}일 ({oldest} ~ {newest})')
    except Exception:
        pass
    conn.close()


def main():
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    parser = argparse.ArgumentParser()
    parser.add_argument('--stocks', action='store_true', help='주식 데이터만 수집')
    parser.add_argument('--news', action='store_true', help='뉴스만 수집')
    parser.add_argument('--stats', action='store_true', help='현황 조회')
    parser.add_argument('--days', type=int, default=730, help='수집할 일수 (기본 730)')
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    if not args.news:
        print(f'=== 주식 데이터 수집 ({args.days}일치) ===')
        collect_stocks(args.days)

    if not args.stocks:
        from collector.naver_history import scrape_range
        print(f'\n=== Naver 뉴스 수집 ({args.days}일치) ===')
        print('예상 시간: 약 2~4시간 (백그라운드 실행 권장)')
        print('Ctrl+C로 중단 가능, 재실행 시 이어서 진행\n')
        scrape_range(days=args.days)


if __name__ == '__main__':
    main()
