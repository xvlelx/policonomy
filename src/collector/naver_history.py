"""
Naver 뉴스 날짜별 역사 수집기
- 리스트 페이지만 긁음 (개별 기사 방문 없음 → 빠름)
- 경제/정치/세계/IT 카테고리
- SQLite historical_news 테이블에 저장
"""
import sqlite3
import time
import re
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DB_PATH = Path(__file__).parent.parent.parent / 'policonomy.db'

CATEGORIES = {
    '경제': '101',
    '정치': '100',
    '세계': '104',
    'IT과학': '105',
}

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'ko-KR,ko;q=0.9',
    'Referer': 'https://news.naver.com/',
}

# 관련 키워드 필터 (이게 없으면 너무 많아짐)
KEYWORDS = [
    '금리', '환율', '주가', '코스피', '나스닥', '달러', '원화',
    '경제', '물가', '인플레', '부동산', '증시', '수출', '무역',
    '반도체', '삼성', 'SK하이닉스', '현대차', '배터리',
    '정책', '예산', '세금', '금융', '은행', '대출', '채권',
    '미국', '중국', '연준', 'Fed', '기준금리', 'GDP',
    '실업', '고용', '임금', '파업', '산업', '기업',
]


def _init_db(conn: sqlite3.Connection):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS historical_news (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            date       TEXT NOT NULL,
            category   TEXT NOT NULL,
            title      TEXT NOT NULL,
            summary    TEXT,
            link       TEXT,
            scraped_at TEXT DEFAULT (datetime('now')),
            UNIQUE(date, link)
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_hn_date ON historical_news(date)')
    conn.commit()


def _is_relevant(title: str, summary: str) -> bool:
    text = (title + ' ' + (summary or '')).lower()
    return any(kw.lower() in text for kw in KEYWORDS)


def _scrape_day_category(date_str: str, sid: str, max_pages: int = 5) -> list[dict]:
    """date_str: 'YYYYMMDD' 형식"""
    articles = []
    for page in range(1, max_pages + 1):
        url = (
            f'https://news.naver.com/main/list.naver'
            f'?mode=LSD&mid=sec&sid1={sid}&date={date_str}&page={page}'
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f'    요청 실패 ({date_str} sid={sid} p={page}): {e}')
            break

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Naver 뉴스 리스트 구조: ul.type06_headline, ul.type06
        items = soup.select('ul.type06_headline li, ul.type06 li')
        if not items:
            break

        found = 0
        for item in items:
            # 제목 + 링크
            a_tag = item.select_one('dt:not(.photo) a') or item.select_one('dt a')
            if not a_tag:
                continue
            title = a_tag.get_text(strip=True)
            link = a_tag.get('href', '')

            # 요약 (있는 경우)
            summary_el = item.select_one('dd.txt_inline') or item.select_one('.lede')
            summary = summary_el.get_text(strip=True) if summary_el else ''

            if title:
                articles.append({
                    'title': title,
                    'summary': summary,
                    'link': link,
                })
                found += 1

        if found == 0:
            break  # 더 이상 기사 없음

        time.sleep(0.3)  # 서버 부하 방지

    return articles


def scrape_range(days: int = 730, delay_between_days: float = 0.5):
    """
    오늘부터 days일 전까지 수집.
    이미 수집된 날짜는 건너뜀 (재시작 가능).
    """
    conn = sqlite3.connect(DB_PATH)
    _init_db(conn)

    # 이미 수집된 날짜 캐시
    scraped = set(
        row[0] for row in conn.execute('SELECT DISTINCT date FROM historical_news')
    )

    today = datetime.now().date()
    dates = [
        (today - timedelta(days=i)).strftime('%Y%m%d')
        for i in range(1, days + 1)  # 어제부터 과거로
    ]

    total_saved = 0
    skipped_days = 0

    for i, date_str in enumerate(dates):
        # DB 형식(YYYY-MM-DD)으로 변환해서 중복 확인
        db_date = f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}'
        if db_date in scraped:
            skipped_days += 1
            continue

        day_articles = []
        for cat_name, sid in CATEGORIES.items():
            arts = _scrape_day_category(date_str, sid)
            for a in arts:
                if _is_relevant(a['title'], a['summary']):
                    a['date'] = db_date
                    a['category'] = cat_name
                    day_articles.append(a)

        # 저장
        saved = 0
        for a in day_articles:
            try:
                conn.execute(
                    'INSERT OR IGNORE INTO historical_news (date, category, title, summary, link) VALUES (?,?,?,?,?)',
                    (a['date'], a['category'], a['title'], a['summary'], a['link'])
                )
                saved += 1
            except Exception:
                pass
        conn.commit()
        total_saved += saved

        progress = (i + 1 - skipped_days)
        remaining = days - skipped_days - progress
        print(
            f'[{i+1}/{days}] {db_date} — 저장 {saved}건 '
            f'(누적 {total_saved}건, 잔여 ~{remaining}일)'
        )

        time.sleep(delay_between_days)

    conn.close()
    print(f'\n완료: 총 {total_saved}건 저장, {skipped_days}일 스킵(기수집)')
    return total_saved


def get_stats() -> dict:
    """수집 현황 조회"""
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute('''
            SELECT
                COUNT(*) as total,
                MIN(date) as oldest,
                MAX(date) as newest,
                COUNT(DISTINCT date) as days
            FROM historical_news
        ''').fetchone()
        by_cat = dict(conn.execute(
            'SELECT category, COUNT(*) FROM historical_news GROUP BY category'
        ).fetchall())
        return {
            'total': rows[0],
            'oldest': rows[1],
            'newest': rows[2],
            'days': rows[3],
            'by_category': by_cat,
        }
    finally:
        conn.close()
