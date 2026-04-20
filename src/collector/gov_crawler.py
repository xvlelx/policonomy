"""
정부·공공기관 보도자료 크롤러 (Crawl4AI 기반)
대상: 국토부, 금감원, 한국은행, 통계청, 금융위원회
"""
import asyncio
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional
from logger import get_logger
from models import Article

logger = get_logger('collector.gov')

# 크롤링 대상 사이트 정의
# (name, category, press_release_url, base_url)
GOV_SOURCES = [
    {
        'name': '금융위원회',
        'category': 'politics_economy',
        'url': 'https://www.fsc.go.kr/po040200',   # 보도자료 목록
        'base': 'https://www.fsc.go.kr',
    },
    {
        'name': '금감원',
        'category': 'politics_economy',
        'url': 'https://www.fss.or.kr/fss/kr/promo/bodobbs_list.jsp',
        'base': 'https://www.fss.or.kr',
    },
    {
        'name': '한국은행',
        'category': 'global_macro',
        'url': 'https://www.bok.or.kr/portal/bbs/P0002353/list.do?menuNo=200433',
        'base': 'https://www.bok.or.kr',
    },
    {
        'name': '통계청',
        'category': 'politics_economy',
        'url': 'https://kostat.go.kr/board.es?mid=a10301010000&bid=10820&list_no=&act=list',
        'base': 'https://kostat.go.kr',
    },
    {
        'name': '국토부',
        'category': 'real_estate',
        'url': 'https://www.molit.go.kr/USR/NEWS/m_72/lst.jsp?srch_dept_nm=&srch_usr_nm=&srch_usr_titl=&srch_usr_ctnt=&bbsId=BBSMasterInfo_000000000008',
        'base': 'https://www.molit.go.kr',
    },
]

# 경제 관련 키워드 (프리필터용)
_GOV_KEYWORDS = [
    '금리', '부동산', '주택', '경제', '정책', '규제', '시장', '금융',
    '투자', '세금', '예산', '수출', '물가', '고용', '성장', '전세',
    '청약', '재건축', '대출', '기준금리', '유동성', '신용', '보험',
]


def _is_gov_relevant(title: str) -> bool:
    title_lower = title.lower()
    return any(kw in title_lower for kw in _GOV_KEYWORDS)


def _make_article(title: str, link: str, category: str, source_name: str) -> Article:
    url_hash = hashlib.sha256(link.encode()).hexdigest()
    return Article(
        hash=url_hash,
        category=category,
        title=f'[{source_name}] {title}',
        link=link,
        summary=title,  # 보도자료는 제목이 요약 역할
        published=datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0900'),
    )


def _extract_links_from_markdown(markdown: str, base_url: str) -> list[tuple[str, str]]:
    """마크다운에서 (title, url) 목록 추출"""
    results = []
    # [텍스트](url) 패턴
    for m in re.finditer(r'\[([^\[\]]+)\]\(([^)]+)\)', markdown):
        text = m.group(1).strip()
        href = m.group(2).strip()
        if not text or len(text) < 5:
            continue
        # 상대경로 → 절대경로
        if href.startswith('/'):
            href = base_url + href
        elif not href.startswith('http'):
            continue
        results.append((text, href))
    return results


async def _crawl_site(source: dict, days: int = 7) -> list[Article]:
    """단일 사이트 크롤링"""
    try:
        from crawl4ai import AsyncWebCrawler, CacheMode
    except ImportError:
        logger.warning('crawl4ai 미설치 — pip install crawl4ai')
        return []

    articles = []
    since = datetime.now() - timedelta(days=days)

    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                url=source['url'],
                cache_mode=CacheMode.BYPASS,
                word_count_threshold=20,
                exclude_external_links=True,
                timeout=30,
            )
            if not result.success or not result.markdown:
                logger.warning(f'{source["name"]} 크롤링 실패: {result.error_message}')
                return []

            links = _extract_links_from_markdown(result.markdown, source['base'])
            seen_titles: set[str] = set()

            for title, href in links:
                if title in seen_titles:
                    continue
                if not _is_gov_relevant(title):
                    continue
                seen_titles.add(title)
                art = _make_article(title, href, source['category'], source['name'])
                articles.append(art)
                if len(articles) >= 10:  # 사이트당 최대 10건
                    break

        logger.info(f'{source["name"]}: {len(articles)}건 수집')
    except Exception as e:
        logger.warning(f'{source["name"]} 크롤링 오류: {e}')

    return articles


async def _crawl_all_async(days: int = 7) -> dict[str, list[Article]]:
    tasks = [_crawl_site(src, days) for src in GOV_SOURCES]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    by_category: dict[str, list[Article]] = {}
    for src, res in zip(GOV_SOURCES, results):
        if isinstance(res, Exception):
            logger.warning(f'{src["name"]} 오류: {res}')
            continue
        for art in res:
            by_category.setdefault(art.category, []).append(art)

    return by_category


def collect_gov_articles(days: int = 7) -> dict[str, list[Article]]:
    """동기 래퍼 — pipeline에서 직접 호출 가능"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 이미 이벤트 루프가 실행 중인 경우 (Jupyter 등)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _crawl_all_async(days))
                return future.result(timeout=120)
        else:
            return loop.run_until_complete(_crawl_all_async(days))
    except Exception as e:
        logger.error(f'정부 사이트 수집 전체 실패: {e}')
        return {}
