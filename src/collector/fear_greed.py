"""CNN Fear & Greed Index 수집기"""
import json
import time
from datetime import datetime
from pathlib import Path

import httpx

from logger import get_logger

logger = get_logger('collector.fear_greed')

_URL = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata'
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Referer': 'https://edition.cnn.com/',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
    'Origin': 'https://edition.cnn.com',
}

_RATING_KR: dict[str, str] = {
    'extreme fear': '극공포',
    'fear': '공포',
    'neutral': '중립',
    'greed': '탐욕',
    'extreme greed': '극탐욕',
}

_RATING_COLOR: dict[str, str] = {
    'extreme fear': '#ef4444',
    'fear': '#f97316',
    'neutral': '#eab308',
    'greed': '#22c55e',
    'extreme greed': '#16a34a',
}


def _parse_rating(raw: str) -> str:
    return raw.lower().strip() if raw else 'neutral'


class FearGreedCollector:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.cache_path = data_dir / 'fear_greed.json'

    def fetch(self) -> dict:
        for attempt in range(3):
            try:
                resp = httpx.get(_URL, headers=_HEADERS, timeout=15, follow_redirects=True)
                resp.raise_for_status()
                data = resp.json()
                result = self._parse(data)
                self._save(result)
                logger.info(
                    f'Fear & Greed 수집 완료: score={result["score"]}, '
                    f'rating={result["rating_en"]} ({result["rating_kr"]})'
                )
                return result
            except httpx.HTTPStatusError as e:
                logger.warning(f'Fear & Greed HTTP {e.response.status_code} (attempt {attempt+1}/3)')
                if attempt < 2:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f'Fear & Greed 수집 시도 {attempt+1}/3 실패: {e}')
                if attempt < 2:
                    time.sleep(2 ** attempt)

        # 실패 시 캐시 반환
        if self.cache_path.exists():
            logger.warning('Fear & Greed 수집 실패 → 캐시 사용')
            try:
                return json.loads(self.cache_path.read_text(encoding='utf-8'))
            except Exception:
                pass

        return self._empty()

    def _parse(self, data: dict) -> dict:
        fg = data.get('fear_and_greed', {})
        score = round(float(fg.get('score', 50)), 1)
        rating_en = _parse_rating(fg.get('rating', 'neutral'))
        rating_kr = _RATING_KR.get(rating_en, '중립')

        # 이전 값들
        prev_close = fg.get('previous_close')
        prev_1w = fg.get('previous_1_week')
        prev_1m = fg.get('previous_1_month')
        prev_1y = fg.get('previous_1_year')

        # 히스토리 (최근 30일)
        hist_raw = data.get('fear_and_greed_historical', {}).get('data', [])
        history = []
        for point in hist_raw[-30:]:
            ts = point.get('x')
            val = point.get('y')
            r = _parse_rating(point.get('rating', ''))
            if ts and val is not None:
                dt = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d')
                history.append({'date': dt, 'score': round(float(val), 1), 'rating': r})

        return {
            'score': score,
            'rating_en': rating_en,
            'rating_kr': rating_kr,
            'color': _RATING_COLOR.get(rating_en, '#eab308'),
            'previous_close': round(float(prev_close), 1) if prev_close is not None else None,
            'previous_1_week': round(float(prev_1w), 1) if prev_1w is not None else None,
            'previous_1_month': round(float(prev_1m), 1) if prev_1m is not None else None,
            'previous_1_year': round(float(prev_1y), 1) if prev_1y is not None else None,
            'history': history,
            'fetched_at': datetime.now().isoformat(),
        }

    def _save(self, result: dict) -> None:
        self.cache_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    def _empty(self) -> dict:
        return {
            'score': None,
            'rating_en': None,
            'rating_kr': None,
            'color': '#eab308',
            'previous_close': None,
            'previous_1_week': None,
            'previous_1_month': None,
            'previous_1_year': None,
            'history': [],
            'fetched_at': None,
            'error': '데이터를 불러오지 못했습니다',
        }
