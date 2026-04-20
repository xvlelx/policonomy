import hashlib
import urllib.parse
import feedparser
from datetime import datetime, timedelta
from typing import Optional
from logger import get_logger
from config import config
from models import Article

logger = get_logger('collector')

# 수집 단계 프리필터 키워드 (LLM 호출 전 사전 제거)
_RELEVANT_KW = [
    # 금융/경제
    '주가', '코스피', '코스닥', '환율', '금리', '기준금리', '인플레이션',
    '경제', '성장률', 'GDP', '무역', '수출', '수입', '관세', '물가',
    '증시', '주식', '채권', '펀드', '투자', '외국인', '공매도',
    '실적', '매출', '영업이익', '적자', '흑자',
    # 정치/정책 (주가 연관)
    '대통령', '국회', '정부', '정책', '법안', '예산', '규제',
    '선거', '장관', '총리', '청와대', '개혁', '공약',
    # 기업/산업
    '반도체', '삼성', 'SK', '현대', 'LG', '카카오', '네이버', '배터리',
    'AI', '인공지능', '빅테크', '스타트업', '상장', 'IPO',
    # 부동산
    '부동산', '아파트', '전세', '청약', '재건축', '주택', '분양',
    # 글로벌
    'Fed', '연준', '트럼프', '관세', '중국', '미국', '일본', '유럽',
    'OPEC', '유가', '달러', '위안', '엔화',
    # 영문
    'economy', 'market', 'stock', 'trade', 'inflation', 'rate',
    'GDP', 'recession', 'tariff', 'policy', 'Fed', 'earnings',
    'revenue', 'profit', 'growth', 'interest', 'bond', 'crypto',
]
_RELEVANT_KW_LOWER = [k.lower() for k in _RELEVANT_KW]


def _is_relevant(title: str, summary: str) -> bool:
    """제목/요약에 경제·정치·시장 관련 키워드가 하나라도 있으면 True"""
    text = (title + ' ' + summary).lower()
    return any(kw in text for kw in _RELEVANT_KW_LOWER)


def _google_news_url(keyword: str, lang: str = 'ko') -> str:
    q = urllib.parse.quote(keyword)
    if lang == 'en':
        return f'https://news.google.com/rss/search?q={q}&hl=en&gl=US&ceid=US:en'
    return f'https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko'


class ArticleCollector:
    def __init__(self):
        self.sources = config.collector.sources
        self.collect_days = config.collector.collect_days

    def _fetch_feed(self, url: str, since: datetime) -> list[Article]:
        articles = []
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                published = entry.get('published_parsed')
                if published:
                    pub_date = datetime(*published[:6])
                    if pub_date < since:
                        continue

                url_hash = hashlib.sha256(entry.get('link', '').encode()).hexdigest()
                articles.append(Article(
                    hash=url_hash,
                    category='',
                    title=entry.get('title', ''),
                    link=entry.get('link', ''),
                    summary=entry.get('summary', ''),
                    published=entry.get('published', ''),
                ))
            logger.info(f'{url} → {len(articles)}개 수집')
        except Exception as e:
            logger.warning(f'{url} 수집 실패: {e}')
        return articles

    def _collect_google_news(self, category: str, days: Optional[int] = None) -> list[Article]:
        days = days or self.collect_days
        since = datetime.now() - timedelta(days=days)
        articles = []
        keywords = config.collector.google_news_keywords.get(category, [])

        for keyword in keywords:
            # 영문 키워드는 US 엔드포인트 사용
            lang = 'en' if all(c.isascii() for c in keyword) else 'ko'
            url = _google_news_url(keyword, lang)
            fetched = self._fetch_feed(url, since)
            for a in fetched:
                a.category = category
            articles.extend(fetched)

        logger.info(f'  Google News [{category}]: 키워드 {len(keywords)}개 → {len(articles)}개')
        return articles

    def collect_all(self, days: Optional[int] = None) -> dict[str, list[Article]]:
        all_articles = {}
        total_raw = 0
        total_filtered = 0
        dead_sources = []

        for category in self.sources.keys():
            # RSS 수집 (소스별 0개 감지)
            rss_articles = []
            for url in self.sources.get(category, []):
                since = datetime.now() - timedelta(days=days or self.collect_days)
                fetched = self._fetch_feed(url, since)
                if not fetched:
                    dead_sources.append(url)
                for a in fetched:
                    a.category = category
                rss_articles.extend(fetched)

            # Google News 수집
            gnews_articles = self._collect_google_news(category, days)
            combined = rss_articles + gnews_articles

            # 프리필터: 키워드 미해당 기사 제거
            before = len(combined)
            filtered = [a for a in combined if _is_relevant(a.title, a.summary)]
            dropped = before - len(filtered)
            if dropped:
                logger.info(f'  [{category}] 프리필터: {before}개 → {len(filtered)}개 ({dropped}개 제거)')

            all_articles[category] = filtered
            total_raw += before
            total_filtered += len(filtered)

        logger.info(f'총 수집: {total_raw}개 → 프리필터 후 {total_filtered}개')

        if dead_sources:
            logger.warning(f'[소스 점검 필요] 0개 반환 소스 {len(dead_sources)}개:')
            for url in dead_sources:
                logger.warning(f'  DEAD: {url}')

        # 정부·공공기관 보도자료 수집 (Crawl4AI)
        try:
            from collector.gov_crawler import collect_gov_articles
            gov_days = max(days or self.collect_days, 7)  # 보도자료는 최소 7일
            gov_articles = collect_gov_articles(days=gov_days)
            added = 0
            for cat, arts in gov_articles.items():
                existing = all_articles.setdefault(cat, [])
                existing.extend(arts)
                added += len(arts)
            if added:
                logger.info(f'정부 보도자료 추가: {added}건')
        except Exception as e:
            logger.warning(f'정부 보도자료 수집 실패 (무시): {e}')

        return all_articles

    @staticmethod
    def deduplicate(articles: list[Article]) -> list[Article]:
        seen = set()
        unique = []
        for a in articles:
            if a.hash not in seen:
                seen.add(a.hash)
                unique.append(a)
        logger.info(f'중복 제거: {sum(1 for _ in articles)}개 → {len(unique)}개')
        return unique