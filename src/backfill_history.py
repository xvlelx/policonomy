"""
역사 데이터 백필 스크립트
historical_news + historical_prices → daily_records + weekly_records

Usage:
    python3 src/backfill_history.py            # 전체 백필
    python3 src/backfill_history.py --stats    # 현황만 조회
    python3 src/backfill_history.py --dry-run  # 실제 저장 없이 미리보기
"""
import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'data' / 'policonomy.db'   # 파이프라인 DB (daily/weekly_records)
HISTORY_DB_PATH = Path(__file__).parent.parent / 'policonomy.db'   # 수집 DB (historical_news/prices)

# 중요도 높은 키워드 (스코어 가중치)
IMPORTANT_KEYWORDS = [
    '금리', '연준', 'Fed', '기준금리', '인플레이션', '경기침체', '긴축', '파산',
    '탄핵', '대통령', '총선', '전쟁', '제재', '관세', '무역전쟁',
    '반도체', '엔비디아', '삼성전자', '코스피', '나스닥', '달러', '환율',
    '부동산', '금감원', '국토부', '가계부채', '대출규제',
    '실적', '영업이익', '매출', 'IPO', '상장', '상폐',
    'AI', '인공지능', 'ChatGPT', '오픈AI',
]

# naver category → weekly_top_articles category
CAT_TO_API = {
    '경제': 'politics_economy',
    '정치': 'politics_economy',
    '세계': 'global_macro',
    'IT과학': 'tech_industry',
    '부동산': 'real_estate',
}

# ─── 키워드 기반 감성 분류 ──────────────────────────────────────────────────────
POS_KEYWORDS = [
    '상승', '호조', '성장', '증가', '긍정', '강세', '흑자', '개선', '회복', '반등',
    '확대', '호실적', '급등', '사상최고', '최고치', '기대', '낙관', '호황', '활성화',
    '수출 증가', '무역흑자', '고용 증가', '투자 확대', '실적 개선', '영업이익 증가',
    '주가 상승', '코스피 상승', '나스닥 상승', '원화 강세', '달러 약세',
]

NEG_KEYWORDS = [
    '하락', '부진', '감소', '위기', '약세', '적자', '악화', '침체', '폭락', '급락',
    '우려', '불안', '위험', '경고', '비관', '둔화', '위축', '손실', '파산', '구조조정',
    '실업', '고용 감소', '무역적자', '수출 감소', '물가 상승', '인플레이션',
    '금리 인상', '긴축', '하향 조정', '실적 악화', '영업손실',
    '주가 하락', '코스피 하락', '나스닥 하락', '원화 약세', '달러 강세',
    '관세', '무역전쟁', '제재', '분쟁', '갈등',
]

# naver category → daily_records column prefix
CAT_MAP = {
    '경제': 'politics',   # 경제 뉴스 → politics_economy 그룹
    '정치': 'politics',
    '세계': 'global',
    'IT과학': 'tech',
}

# daily_records, weekly_records 스키마 (없으면 생성)
_DDL = """
CREATE TABLE IF NOT EXISTS daily_records (
    day             TEXT PRIMARY KEY,
    total_articles  INTEGER,
    politics_pos    INTEGER, politics_neg INTEGER, politics_neu INTEGER,
    global_pos      INTEGER, global_neg  INTEGER, global_neu  INTEGER,
    tech_pos        INTEGER, tech_neg    INTEGER, tech_neu    INTEGER,
    realestate_pos  INTEGER, realestate_neg INTEGER, realestate_neu INTEGER,
    top_keywords    TEXT,
    overall_sentiment TEXT,
    kospi_pred_dir      TEXT, kospi_pred_change   REAL,
    usdkrw_pred_dir     TEXT, usdkrw_pred_change  REAL,
    samsung_pred_dir    TEXT, samsung_pred_change REAL,
    nasdaq_pred_dir     TEXT, nasdaq_pred_change  REAL,
    kospi_actual_change   REAL,
    usdkrw_actual_change  REAL,
    samsung_actual_change REAL,
    nasdaq_actual_change  REAL,
    direction_hits  INTEGER, direction_total INTEGER,
    created_at  TEXT, verified_at TEXT
);

CREATE TABLE IF NOT EXISTS weekly_records (
    week            TEXT PRIMARY KEY,
    total_articles  INTEGER,
    politics_pos    INTEGER, politics_neg INTEGER, politics_neu INTEGER,
    global_pos      INTEGER, global_neg  INTEGER, global_neu  INTEGER,
    tech_pos        INTEGER, tech_neg    INTEGER, tech_neu    INTEGER,
    realestate_pos  INTEGER, realestate_neg INTEGER, realestate_neu INTEGER,
    top_keywords    TEXT,
    overall_sentiment TEXT,
    kospi_pred_dir      TEXT, kospi_pred_change   REAL,
    usdkrw_pred_dir     TEXT, usdkrw_pred_change  REAL,
    samsung_pred_dir    TEXT, samsung_pred_change REAL,
    nasdaq_pred_dir     TEXT, nasdaq_pred_change  REAL,
    kospi_actual_change   REAL,
    usdkrw_actual_change  REAL,
    samsung_actual_change REAL,
    nasdaq_actual_change  REAL,
    direction_hits  INTEGER, direction_total INTEGER,
    created_at  TEXT, verified_at TEXT
);
"""


def _classify(title: str, summary: str) -> str:
    text = (title + ' ' + (summary or '')).lower()
    pos = sum(1 for kw in POS_KEYWORDS if kw in text)
    neg = sum(1 for kw in NEG_KEYWORDS if kw in text)
    if pos > neg:
        return 'positive'
    if neg > pos:
        return 'negative'
    return 'neutral'


def _week_start(date_str: str) -> str:
    """YYYY-MM-DD → 해당 주 월요일 YYYY-MM-DD"""
    d = datetime.strptime(date_str, '%Y-%m-%d').date()
    return (d - timedelta(days=d.weekday())).strftime('%Y-%m-%d')


def _overall(pos: int, neg: int, neu: int) -> str:
    if pos > neg and pos > neu:
        return 'positive'
    if neg > pos and neg > neu:
        return 'negative'
    return 'neutral'


def load_historical_news(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    """날짜별로 그룹핑된 historical_news 반환"""
    try:
        rows = conn.execute(
            'SELECT date, category, title, summary, link FROM historical_news ORDER BY date'
        ).fetchall()
    except Exception as e:
        print(f'historical_news 로딩 실패: {e}')
        return {}

    by_date: dict[str, list[dict]] = defaultdict(list)
    for date, category, title, summary, link in rows:
        by_date[date].append({
            'category': category,
            'title': title or '',
            'summary': summary or '',
            'link': link or '',
        })
    return dict(by_date)


def load_market_changes(conn: sqlite3.Connection) -> dict[str, dict]:
    """
    historical_prices에서 일별 등락률 계산
    date → {kospi, usdkrw, samsung, nasdaq} 변화율(%)
    """
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    if 'historical_prices' not in tables:
        return {}

    rows = conn.execute(
        'SELECT date, ticker, close FROM historical_prices ORDER BY ticker, date'
    ).fetchall()

    # ticker별 날짜순 close 정리
    by_ticker: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for date, ticker, close in rows:
        if close is not None:
            by_ticker[ticker].append((date, float(close)))

    changes: dict[str, dict] = defaultdict(dict)
    ticker_col = {
        'kospi': 'kospi_actual_change',
        'usd_krw': 'usdkrw_actual_change',
        'samsung': 'samsung_actual_change',
        'nasdaq': 'nasdaq_actual_change',
    }

    for ticker, col in ticker_col.items():
        prices = by_ticker.get(ticker, [])
        for i in range(1, len(prices)):
            prev_date, prev_close = prices[i - 1]
            curr_date, curr_close = prices[i]
            if prev_close and prev_close != 0:
                pct = round((curr_close - prev_close) / prev_close * 100, 4)
                changes[curr_date][col] = pct

    return dict(changes)


def build_daily_records(
    by_date: dict[str, list[dict]],
    market_changes: dict[str, dict],
) -> list[dict]:
    records = []
    for date_str in sorted(by_date.keys()):
        articles = by_date[date_str]
        counts: dict[str, dict[str, int]] = {
            'politics': {'pos': 0, 'neg': 0, 'neu': 0},
            'global':   {'pos': 0, 'neg': 0, 'neu': 0},
            'tech':     {'pos': 0, 'neg': 0, 'neu': 0},
            'realestate': {'pos': 0, 'neg': 0, 'neu': 0},
        }
        keyword_freq: dict[str, int] = defaultdict(int)

        for art in articles:
            col_prefix = CAT_MAP.get(art['category'], 'politics')
            sentiment = _classify(art['title'], art['summary'])
            key = 'pos' if sentiment == 'positive' else 'neg' if sentiment == 'negative' else 'neu'
            counts[col_prefix][key] += 1

            # 키워드 빈도 (제목 단어)
            for word in art['title'].split():
                if len(word) >= 2:
                    keyword_freq[word] += 1

        top_kw = sorted(keyword_freq.items(), key=lambda x: -x[1])[:10]
        top_kw_list = [w for w, _ in top_kw]

        total_pos = sum(counts[c]['pos'] for c in counts)
        total_neg = sum(counts[c]['neg'] for c in counts)
        total_neu = sum(counts[c]['neu'] for c in counts)
        overall = _overall(total_pos, total_neg, total_neu)

        market = market_changes.get(date_str, {})

        record = {
            'day': date_str,
            'total_articles': len(articles),
            'politics_pos': counts['politics']['pos'],
            'politics_neg': counts['politics']['neg'],
            'politics_neu': counts['politics']['neu'],
            'global_pos':   counts['global']['pos'],
            'global_neg':   counts['global']['neg'],
            'global_neu':   counts['global']['neu'],
            'tech_pos':     counts['tech']['pos'],
            'tech_neg':     counts['tech']['neg'],
            'tech_neu':     counts['tech']['neu'],
            'realestate_pos': counts['realestate']['pos'],
            'realestate_neg': counts['realestate']['neg'],
            'realestate_neu': counts['realestate']['neu'],
            'top_keywords': json.dumps(top_kw_list, ensure_ascii=False),
            'overall_sentiment': overall,
            'kospi_actual_change':   market.get('kospi_actual_change'),
            'usdkrw_actual_change':  market.get('usdkrw_actual_change'),
            'samsung_actual_change': market.get('samsung_actual_change'),
            'nasdaq_actual_change':  market.get('nasdaq_actual_change'),
            'verified_at': datetime.now().isoformat() if market else None,
            'created_at': datetime.now().isoformat(),
        }
        records.append(record)
    return records


def aggregate_weekly(daily_records: list[dict]) -> list[dict]:
    """일별 → 주별 집계"""
    by_week: dict[str, list[dict]] = defaultdict(list)
    for r in daily_records:
        week = _week_start(r['day'])
        by_week[week].append(r)

    weekly = []
    for week in sorted(by_week.keys()):
        days = by_week[week]
        cols = ['politics_pos', 'politics_neg', 'politics_neu',
                'global_pos', 'global_neg', 'global_neu',
                'tech_pos', 'tech_neg', 'tech_neu',
                'realestate_pos', 'realestate_neg', 'realestate_neu']
        sums = {c: sum(d.get(c) or 0 for d in days) for c in cols}

        total_pos = sums['politics_pos'] + sums['global_pos'] + sums['tech_pos'] + sums['realestate_pos']
        total_neg = sums['politics_neg'] + sums['global_neg'] + sums['tech_neg'] + sums['realestate_neg']
        total_neu = sums['politics_neu'] + sums['global_neu'] + sums['tech_neu'] + sums['realestate_neu']
        overall = _overall(total_pos, total_neg, total_neu)

        # 주간 시장 평균 등락률
        def _avg(col):
            vals = [d[col] for d in days if d.get(col) is not None]
            return round(sum(vals) / len(vals), 4) if vals else None

        # 키워드 합산
        kw_freq: dict[str, int] = defaultdict(int)
        for d in days:
            for kw in json.loads(d.get('top_keywords') or '[]'):
                kw_freq[kw] += 1
        top_kw = [w for w, _ in sorted(kw_freq.items(), key=lambda x: -x[1])[:10]]

        has_market = any(d.get('kospi_actual_change') is not None for d in days)

        weekly.append({
            'week': week,
            'total_articles': sum(d.get('total_articles') or 0 for d in days),
            **sums,
            'top_keywords': json.dumps(top_kw, ensure_ascii=False),
            'overall_sentiment': overall,
            'kospi_actual_change':   _avg('kospi_actual_change'),
            'usdkrw_actual_change':  _avg('usdkrw_actual_change'),
            'samsung_actual_change': _avg('samsung_actual_change'),
            'nasdaq_actual_change':  _avg('nasdaq_actual_change'),
            'verified_at': datetime.now().isoformat() if has_market else None,
            'created_at': datetime.now().isoformat(),
        })
    return weekly


def save_records(conn: sqlite3.Connection, daily: list[dict], weekly: list[dict], dry_run: bool = False):
    if dry_run:
        print(f'\n[DRY RUN] 저장 예정: daily {len(daily)}건, weekly {len(weekly)}건')
        if daily:
            d = daily[0]
            print(f'  일별 샘플 ({d["day"]}): 정치{d["politics_pos"]}+/{d["politics_neg"]}- '
                  f'글로벌{d["global_pos"]}+/{d["global_neg"]}- '
                  f'테크{d["tech_pos"]}+/{d["tech_neg"]}- '
                  f'감성={d["overall_sentiment"]} '
                  f'코스피={d.get("kospi_actual_change")}%')
        return

    daily_cols = [
        'day', 'total_articles',
        'politics_pos', 'politics_neg', 'politics_neu',
        'global_pos', 'global_neg', 'global_neu',
        'tech_pos', 'tech_neg', 'tech_neu',
        'realestate_pos', 'realestate_neg', 'realestate_neu',
        'top_keywords', 'overall_sentiment',
        'kospi_actual_change', 'usdkrw_actual_change',
        'samsung_actual_change', 'nasdaq_actual_change',
        'verified_at', 'created_at',
    ]
    ph = ', '.join('?' * len(daily_cols))
    cols_str = ', '.join(daily_cols)

    conn.executemany(
        f'INSERT OR IGNORE INTO daily_records ({cols_str}) VALUES ({ph})',
        [[r.get(c) for c in daily_cols] for r in daily]
    )

    weekly_cols = [c.replace('day', 'week') if c == 'day' else c for c in daily_cols]
    weekly_cols[0] = 'week'
    ph_w = ', '.join('?' * len(weekly_cols))
    cols_w = ', '.join(weekly_cols)
    conn.executemany(
        f'INSERT OR IGNORE INTO weekly_records ({cols_w}) VALUES ({ph_w})',
        [[r.get(c) for c in weekly_cols] for r in weekly]
    )
    conn.commit()


def _score_article(title: str, summary: str) -> int:
    """키워드 기반 중요도 점수 계산 (1~10)"""
    text = title + ' ' + (summary or '')
    score = 3  # 기본값
    for kw in IMPORTANT_KEYWORDS:
        if kw in text:
            score += 1
    # 제목 길이가 적당하면 가산
    if 10 <= len(title) <= 60:
        score += 1
    return min(10, score)


def build_weekly_top_articles(
    by_date: dict[str, list[dict]],
) -> list[dict]:
    """주별 top 10 기사 생성"""
    by_week: dict[str, list[dict]] = defaultdict(list)
    for date_str, articles in by_date.items():
        week = _week_start(date_str)
        for art in articles:
            sentiment = _classify(art['title'], art['summary'])
            score = _score_article(art['title'], art['summary'])
            by_week[week].append({
                'week': week,
                'date': date_str,
                'title': art['title'],
                'link': art.get('link', ''),
                'category': CAT_TO_API.get(art['category'], 'politics_economy'),
                'sentiment': sentiment,
                'importance': score,
                'one_line': '',
                'issue': '',
                'economic_impact': '',
                'affected_sectors': json.dumps([], ensure_ascii=False),
                'keywords': json.dumps([], ensure_ascii=False),
            })

    result = []
    for week in sorted(by_week.keys()):
        articles = by_week[week]
        # 중요도 내림차순 정렬 후 top 10
        top10 = sorted(articles, key=lambda x: -x['importance'])[:10]
        for rank, art in enumerate(top10, 1):
            result.append({**art, 'rank': rank})
    return result


def save_weekly_top_articles(conn: sqlite3.Connection, tops: list[dict], dry_run: bool = False):
    if dry_run:
        print(f'[DRY RUN] weekly_top_articles 저장 예정: {len(tops)}건')
        return

    # 스키마 확인 후 생성
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_top_articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            week        TEXT NOT NULL,
            rank        INTEGER NOT NULL,
            title       TEXT,
            link        TEXT,
            category    TEXT,
            sentiment   TEXT,
            importance  INTEGER,
            one_line    TEXT,
            issue       TEXT,
            economic_impact TEXT,
            affected_sectors TEXT,
            keywords    TEXT
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_weekly_top_articles
        ON weekly_top_articles(week, rank)
    """)

    cols = ['week', 'rank', 'title', 'link', 'category', 'sentiment',
            'importance', 'one_line', 'issue', 'economic_impact',
            'affected_sectors', 'keywords']
    ph = ', '.join('?' * len(cols))
    conn.executemany(
        f'INSERT OR IGNORE INTO weekly_top_articles ({", ".join(cols)}) VALUES ({ph})',
        [[r.get(c) for c in cols] for r in tops]
    )
    conn.commit()


def show_stats(conn: sqlite3.Connection):
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]

    print('\n=== 백필 현황 ===')
    for tbl in ['historical_news', 'historical_prices', 'daily_records', 'weekly_records']:
        if tbl not in tables:
            print(f'  {tbl}: 테이블 없음')
            continue
        row = conn.execute(f'SELECT COUNT(*) FROM {tbl}').fetchone()
        print(f'  {tbl}: {row[0]:,}건')

    if 'daily_records' in tables:
        row = conn.execute(
            'SELECT MIN(day), MAX(day), COUNT(*) FROM daily_records'
        ).fetchone()
        if row[0]:
            print(f'\n  daily_records 기간: {row[0]} ~ {row[1]} ({row[2]}일)')
            mkt = conn.execute(
                'SELECT COUNT(*) FROM daily_records WHERE kospi_actual_change IS NOT NULL'
            ).fetchone()
            print(f'  시장 데이터 있는 날: {mkt[0]}일')

    if 'weekly_records' in tables:
        row = conn.execute(
            'SELECT MIN(week), MAX(week), COUNT(*) FROM weekly_records'
        ).fetchone()
        if row[0]:
            print(f'  weekly_records 기간: {row[0]} ~ {row[1]} ({row[2]}주)')

    if 'weekly_top_articles' in tables:
        row = conn.execute(
            'SELECT COUNT(DISTINCT week), COUNT(*) FROM weekly_top_articles'
        ).fetchone()
        print(f'  weekly_top_articles: {row[1]:,}건 ({row[0]}주)')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stats', action='store_true', help='현황 조회')
    parser.add_argument('--dry-run', action='store_true', help='저장 없이 미리보기')
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f'파이프라인 DB 없음: {DB_PATH}')
        return

    conn = sqlite3.connect(DB_PATH)          # 파이프라인 DB (쓰기)
    hist_db = HISTORY_DB_PATH if HISTORY_DB_PATH.exists() else DB_PATH
    hist_conn = sqlite3.connect(hist_db)     # 수집 DB (읽기)

    if args.stats:
        show_stats(conn)
        print(f'\n  [수집DB: {hist_db}]')
        show_stats(hist_conn)
        conn.close()
        hist_conn.close()
        return

    # 스키마 초기화
    conn.executescript(_DDL)
    conn.commit()

    print('historical_news 로딩 중...')
    by_date = load_historical_news(hist_conn)
    if not by_date:
        print('historical_news 데이터 없음. collect_history.py --news 먼저 실행하세요.')
        conn.close()
        hist_conn.close()
        return
    print(f'  {len(by_date)}일치 뉴스 로딩 완료 (총 {sum(len(v) for v in by_date.values()):,}건)')

    print('historical_prices 로딩 중...')
    market_changes = load_market_changes(hist_conn)
    print(f'  {len(market_changes)}일치 시장 데이터 로딩 완료')

    print('일별 감성 집계 중...')
    daily = build_daily_records(by_date, market_changes)
    print(f'  {len(daily)}일 레코드 생성')

    print('주별 집계 중...')
    weekly = aggregate_weekly(daily)
    print(f'  {len(weekly)}주 레코드 생성')

    save_records(conn, daily, weekly, dry_run=args.dry_run)

    print('주간 TOP 10 기사 생성 중...')
    tops = build_weekly_top_articles(by_date)
    print(f'  {len(tops)}건 생성 ({len(set(t["week"] for t in tops))}주)')
    save_weekly_top_articles(conn, tops, dry_run=args.dry_run)

    if not args.dry_run:
        print(f'\n완료: daily_records {len(daily)}건, weekly_records {len(weekly)}건, weekly_top_articles {len(tops)}건 저장')
        show_stats(conn)

    conn.close()
    hist_conn.close()


if __name__ == '__main__':
    main()
