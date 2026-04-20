from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).parent.parent

@dataclass
class PathConfig:
    base: Path = BASE_DIR
    data: Path = BASE_DIR / 'data'
    templates: Path = BASE_DIR / 'templates'
    logs: Path = BASE_DIR / 'logs'

    def __post_init__(self):
        self.data.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)


@dataclass
class ModelConfig:
    local_model: str = 'gemma4:e4b'
    ollama_url: str = 'http://localhost:11434/v1'
    anthropic_key: str = field(default_factory=lambda: os.getenv('ANTHROPIC_API_KEY', ''))
    groq_key: str = field(default_factory=lambda: os.getenv('GROQ_API_KEY', ''))
    groq_model: str = 'openai/gpt-oss-120b'  # 레거시 (현재는 llm.py에서 직접 지정)
    use_local: bool = False  # True면 Ollama, False면 Groq
    use_groq: bool = True    # True면 Groq API 사용

    def __post_init__(self):
        import logging as _logging
        if self.use_groq and not self.groq_key:
            _logging.getLogger('config').warning(
                'GROQ_API_KEY 미설정 — Groq 모드 활성화 상태이나 API 호출이 실패합니다'
            )


@dataclass
class CollectorConfig:
    collect_days: int = 1
    sources: dict = field(default_factory=lambda: {
        'politics_economy': [
            # 경제
            'https://www.hankyung.com/feed/economy',
            'https://www.yna.co.kr/rss/economy.xml',
            'https://rss.donga.com/economy.xml',
            'https://www.asiae.co.kr/rss/economy.htm',
            'https://www.mk.co.kr/rss/30100041/',       # 매경 경제
            'https://www.mk.co.kr/rss/30200030/',       # 매경 증시
            # 정치 (주가 영향)
            'https://www.yna.co.kr/rss/politics.xml',
            'https://rss.donga.com/politics.xml',
            'https://www.khan.co.kr/rss/rssdata/politic_news.xml',
            'https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=01',
            'https://www.hani.co.kr/rss/politics',        # 한겨레 정치
            'https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml',  # 조선일보 전체
            'https://www.hani.co.kr/rss/economy',        # 한겨레 경제
        ],
        'global_macro': [
            'https://feeds.feedburner.com/businessinsider',
            'https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml',
            'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
            'https://feeds.marketwatch.com/marketwatch/topstories/',
            'https://feeds.content.dowjones.io/public/rss/mw_marketpulse',  # WSJ MarketPulse
            'https://www.cnbc.com/id/100003114/device/rss/rss.html',
            'https://www.cnbc.com/id/10000664/device/rss/rss.html',
            'https://finance.yahoo.com/news/rssindex',    # Yahoo Finance
            'https://seekingalpha.com/feed.xml',          # Seeking Alpha
            'https://feeds.bloomberg.com/markets/news.rss',  # Bloomberg Markets
            'https://www.hankyung.com/feed/international',
            'https://www.yna.co.kr/rss/international.xml',
        ],
        'tech_industry': [
            'https://techcrunch.com/feed/',
            'https://feeds.feedburner.com/venturebeat/SZYF',
            'https://rss.etnews.com/Section901.xml',
            'https://rss.etnews.com/Section902.xml',
            'https://rss.etnews.com/Section903.xml',
            'https://feeds.arstechnica.com/arstechnica/index',
            'https://www.hankyung.com/feed/it',
            'https://feeds.feedburner.com/TheHackersNews',  # 사이버보안/테크
        ],
        'real_estate': [
            'https://www.hankyung.com/feed/realestate',
            'https://www.asiae.co.kr/rss/realestate.htm',
            'https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId=07',
            'https://www.mk.co.kr/rss/50200011/',
            'https://www.mk.co.kr/rss/50100032/',
            'https://www.mk.co.kr/rss/50300009/',        # 매경 부동산
        ],
    })
    # Google News RSS 키워드 (카테고리별, 주가 영향 중심)
    google_news_keywords: dict = field(default_factory=lambda: {
        'politics_economy': [
            '코스피 경제', '금리 기준금리', '대통령 경제정책',
            '국회 예산 법안', '환율 달러', '정치 주가 증시',
            '정부 규제 정책', '선거 경제', '관세 무역',
        ],
        'global_macro': [
            'Fed interest rate economy', 'US economy tariff trade',
            'global recession inflation', 'China economy market',
            '미국 연준 금리', '글로벌 경제 위기', '원유 유가 OPEC',
            'Trump economy policy', 'IMF World Bank growth',
        ],
        'tech_industry': [
            '반도체 삼성 SK하이닉스 주가', 'AI 인공지능 투자 주가',
            '빅테크 실적 나스닥', '배터리 2차전지 전기차',
            'Nvidia Apple Microsoft earnings stock',
        ],
        'real_estate': [
            '부동산 정책 규제', '아파트 가격 매매',
            '전세 월세 금리', '재건축 재개발 허가',
            '주택 공급 청약',
        ],
    })


@dataclass
class PredictorConfig:
    market_targets: dict = field(default_factory=lambda: {
        'kospi': '^KS11',
        'usd_krw': 'KRW=X',
        'samsung': '005930.KS',
        'skhynix': '000660.KS',
        'nasdaq': '^IXIC',
        'sp500': '^GSPC',
        'dow': '^DJI',
        'nvidia': 'NVDA',
    })
    pred_days: int = 5
    lookback: int = 400
    kronos_model: str = 'NeoQuasar/Kronos-small'
    kronos_tokenizer: str = 'NeoQuasar/Kronos-Tokenizer-base'


@dataclass
class Config:
    paths: PathConfig = field(default_factory=PathConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    collector: CollectorConfig = field(default_factory=CollectorConfig)
    predictor: PredictorConfig = field(default_factory=PredictorConfig)


# 싱글톤
config = Config()