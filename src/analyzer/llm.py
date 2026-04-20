import json
import time
import re
import requests
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from logger import get_logger
from config import config
from models import Article
from utils.groq_utils import parse_reset_seconds as _parse_reset_seconds

logger = get_logger('analyzer')

_GROQ_BASE_URL = 'https://api.groq.com/openai/v1'

# 모델별 역할 분리
_SCORE_MODEL = 'llama-3.1-8b-instant'     # 14400 RPM, 6000 TPM - 스코어링
_ANALYZE_MODEL = 'llama-3.3-70b-versatile' # 1000 RPM, 12000 TPM - 심층분석

# 심층분석 폴백 순서: 429 시 다음 모델로 즉시 전환 (성능 높은 순)
_ANALYZE_FALLBACK_MODELS = [
    'llama-3.3-70b-versatile',               # primary — 1000 RPM
    'meta-llama/llama-4-scout-17b-16e-instruct',  # Llama 4 Scout, 별도 버킷
    'llama-3.1-8b-instant',                  # 최후 수단 (8B, 빠름)
]



class ArticleAnalyzer:
    def __init__(self):
        if config.model.use_groq:
            self._api_key = config.model.groq_key
            self._use_groq = True
            logger.info(f'Groq 모드: score={_SCORE_MODEL}, analyze={_ANALYZE_MODEL}')
        else:
            self._ollama_base = config.model.ollama_url.replace('/v1', '')
            self.model = config.model.local_model
            self._use_groq = False
            logger.info(f'Ollama 모드: {self.model}')

    def _chat(self, prompt: str, max_tokens: int = 200, temperature: float = 0.1,
              model: str | None = None) -> str:
        if self._use_groq:
            return self._chat_groq(prompt, max_tokens, temperature, model or _SCORE_MODEL)
        return self._chat_ollama(prompt, max_tokens, temperature)

    def _try_one_model(self, model: str, prompt: str, max_tokens: int, temperature: float) -> str | None:
        """단일 모델 시도. 429면 None 반환, 성공하면 응답 텍스트, 기타 오류면 None."""
        for attempt in range(3):
            try:
                resp = httpx.post(
                    f'{_GROQ_BASE_URL}/chat/completions',
                    headers={
                        'Authorization': f'Bearer {self._api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': model,
                        'messages': [{'role': 'user', 'content': prompt}],
                        'max_tokens': max_tokens,
                        'temperature': temperature,
                    },
                    timeout=30,
                )

                if resp.status_code == 429:
                    reset_req = resp.headers.get('x-ratelimit-reset-requests', '')
                    reset_tok = resp.headers.get('x-ratelimit-reset-tokens', '')
                    wait = max(_parse_reset_seconds(reset_req), _parse_reset_seconds(reset_tok))
                    retry_after = resp.headers.get('retry-after', '')
                    if retry_after:
                        try:
                            wait = max(wait, float(retry_after))
                        except ValueError:
                            pass
                    wait = min(wait, 20.0)  # 최대 20초 대기
                    logger.warning(f'Groq 429 (model={model}, attempt={attempt+1}) → {wait:.1f}s 대기 후 재시도')
                    time.sleep(wait)
                    continue  # 같은 모델 재시도

                resp.raise_for_status()
                data = resp.json()
                raw = data['choices'][0]['message']['content'] or ''

                # 남은 토큰이 20% 미만이면 리셋까지 잠시 대기
                remaining_tok = int(resp.headers.get('x-ratelimit-remaining-tokens', 9999))
                limit_tok = int(resp.headers.get('x-ratelimit-limit-tokens', 9999))
                if limit_tok > 0 and remaining_tok / limit_tok < 0.2:
                    reset_tok_h = resp.headers.get('x-ratelimit-reset-tokens', '500ms')
                    wait = _parse_reset_seconds(reset_tok_h)
                    logger.debug(f'토큰 소진 임박 ({remaining_tok}/{limit_tok}) → {wait:.1f}s 대기')
                    time.sleep(wait)

                logger.debug(f'Groq 응답 ({model}): {repr(raw[:100])}')
                return raw.strip()

            except httpx.HTTPStatusError as e:
                logger.warning(f'Groq HTTP {e.response.status_code} (model={model}, attempt={attempt+1})')
                if attempt < 2:
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f'Groq 시도 {attempt+1}/3 실패 (model={model}): {e}')
                if attempt < 2:
                    time.sleep(2 ** attempt)
        return None

    def _chat_groq(self, prompt: str, max_tokens: int, temperature: float, model: str) -> str:
        if model == _ANALYZE_MODEL:
            candidates = _ANALYZE_FALLBACK_MODELS
        else:
            candidates = [model, model, model]

        for candidate in candidates:
            result = self._try_one_model(candidate, prompt, max_tokens, temperature)
            if result is not None:
                if candidate != model:
                    logger.info(f'폴백 성공 (원래={model} → 사용={candidate})')
                return result

        raise RuntimeError(f'Groq 모든 폴백 실패 (원래 model={model})')

    def _chat_ollama(self, prompt: str, max_tokens: int, temperature: float) -> str:
        url = f'{self._ollama_base}/api/generate'
        for attempt in range(3):
            try:
                response = requests.post(
                    url,
                    json={
                        'model': self.model,
                        'prompt': prompt,
                        'stream': False,
                        'think': False,
                        'options': {
                            'num_predict': max_tokens,
                            'temperature': temperature,
                        }
                    },
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()
                raw = data.get('response', '')
                logger.debug(f'Ollama 응답: {repr(raw[:200])}')
                return raw.strip()
            except Exception as e:
                logger.warning(f'Ollama _chat 시도 {attempt + 1}/3 실패: {e}')
                if attempt < 2:
                    time.sleep(2)
        logger.error('Ollama _chat 3회 모두 실패')
        return ''

    def _parse_json(self, text: str) -> dict:
        if not text:
            raise ValueError('빈 응답')

        text = re.sub(r'<think>[\s\S]*?</think>', '', text)
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        text = text.strip()

        s = text.find('{')
        e = text.rfind('}') + 1
        if s != -1 and e > s:
            try:
                return json.loads(text[s:e])
            except json.JSONDecodeError:
                pass
        raise ValueError(f'JSON 파싱 실패: {repr(text[:100])}')

    def score(self, article: Article) -> dict:
        try:
            prompt = f'''뉴스 기사의 경제적 중요도를 평가해.

Title: {article.title}
Summary: {article.summary[:200] if article.summary else '없음'}

설명 없이 JSON만 답해:
{{"importance": 7, "one_line": "요약", "is_urgent": false, "keywords": ["키워드"]}}

JSON:'''
            response = self._chat(prompt, max_tokens=200, temperature=0.1, model=_SCORE_MODEL)
            return self._parse_json(response)
        except Exception as e:
            logger.warning(f'스코어링 실패 ({article.title[:30]}): {e}')
            return {'importance': 3, 'one_line': article.title, 'is_urgent': False, 'keywords': []}

    def analyze(self, article: Article) -> dict | None:
        try:
            response = self._chat(
                f'''뉴스 기사를 경제 전문가 관점에서 심층 분석해.

Title: {article.title}
Summary: {article.summary[:300]}
Category: {article.category}

다음 JSON 형식으로만 답해:
{{"issue": "핵심 이슈 한 문장", "cause": "배경/원인", "economic_impact": "경제적 파급효과 2~3문장", "affected_sectors": ["섹터"], "sentiment": "positive/negative/neutral", "prediction": "향후 1~2주 예상"}}

JSON:''',
                max_tokens=450,
                temperature=0.1,
                model=_ANALYZE_MODEL,
            )
            result = self._parse_json(response)
            result['title'] = article.title
            result['link'] = article.link
            result['category'] = article.category
            result['importance'] = article.importance  # score() 단계에서 이미 산출된 값 사용
            result['is_urgent'] = article.is_urgent    # score() 단계에서 설정된 긴급 여부
            result['one_line'] = article.one_line      # score() 단계에서 생성된 한줄 요약
            result['keywords'] = article.keywords      # score() 단계에서 추출된 키워드
            return result
        except Exception as e:
            logger.warning(f'분석 실패 ({article.title[:30]}): {e}')
            return None

    def run(self, all_articles: dict) -> list[dict]:
        from collector.rss import ArticleCollector
        articles = []
        for category, items in all_articles.items():
            articles.extend(items)

        unique = ArticleCollector.deduplicate(articles)
        logger.info(f'중복 제거 후: {len(unique)}개')

        # LLM 필터 제거 - 키워드 프리필터가 이미 처리함
        # 카테고리별 최대 30개로 제한 (Groq TPM 보호) — 최신순 정렬
        import email.utils as _eut
        from datetime import timezone as _tz

        def _pub_ts(a) -> float:
            try:
                return _eut.parsedate_to_datetime(a.published).timestamp()
            except Exception:
                return 0.0

        def _time_stratified(arts: list, limit: int) -> list:
            """주간 전체에서 균등 샘플링 — 특정 시간대 편향 방지"""
            if len(arts) <= limit:
                return arts
            arts_asc = sorted(arts, key=_pub_ts)  # 오래된 순
            step = len(arts_asc) / limit
            return [arts_asc[int(i * step)] for i in range(limit)]

        capped = []
        by_cat: dict[str, list] = {}
        for a in unique:
            by_cat.setdefault(a.category, []).append(a)
        SCORE_LIMIT = 50   # 카테고리별 스코어링 상한 (주간 분산 샘플)
        for cat, arts in by_cat.items():
            if len(arts) > SCORE_LIMIT:
                sampled = _time_stratified(arts, SCORE_LIMIT)
                import datetime as _dt
                ts_min = min(_pub_ts(a) for a in sampled)
                ts_max = max(_pub_ts(a) for a in sampled)
                span = _dt.datetime.fromtimestamp(ts_max) - _dt.datetime.fromtimestamp(ts_min)
                logger.info(f'  {cat}: {len(arts)}개 → 주간 분산 {SCORE_LIMIT}개 (커버: {span})')
                arts = sampled
            capped.extend(arts)
        logger.info(f'상한 적용 후: {len(capped)}개 (카테고리별 주간 분산 최대 {SCORE_LIMIT}개)')

        # 스코어링 (llama-3.1-8b-instant)
        logger.info(f'스코어링 시작 ({len(capped)}개, model={_SCORE_MODEL})...')
        for i, a in enumerate(capped):
            logger.info(f'  스코어링 {i+1}/{len(capped)} - {a.title[:40]}')
            scored = self.score(a)
            a.importance = scored.get('importance', 3)
            a.one_line = scored.get('one_line', a.title)
            a.is_urgent = scored.get('is_urgent', False)
            a.keywords = scored.get('keywords', [])

        # 카테고리별 상위 15개 심층분석 (스코어링 후 importance 기준)
        ANALYZE_LIMIT = 15
        top_articles = []
        for category in config.collector.sources.keys():
            cat_arts = sorted(
                [a for a in capped if a.category == category],
                key=lambda x: x.importance,
                reverse=True
            )
            top_articles.extend(cat_arts[:ANALYZE_LIMIT])

        urgent = [a for a in capped if a.is_urgent and a not in top_articles]
        top_articles.extend(urgent)
        logger.info(f'심층분석 대상: {len(top_articles)}개 (긴급 {len(urgent)}개)')

        # 심층분석 (llama-3.3-70b-versatile) — 세미배치 병렬화
        logger.info(f'심층분석 시작 ({len(top_articles)}개, model={_ANALYZE_MODEL})...')
        BATCH_SIZE = 5
        BATCH_DELAY = 2.0  # 배치 간 딜레이 (Groq TPM 버퍼)
        batches = [top_articles[i:i+BATCH_SIZE] for i in range(0, len(top_articles), BATCH_SIZE)]
        logger.info(f'세미배치 모드: {len(batches)}배치 × {BATCH_SIZE}개')
        analyzed = []
        for batch_idx, batch in enumerate(batches):
            if batch_idx > 0:
                time.sleep(BATCH_DELAY)
            logger.info(f'  배치 {batch_idx+1}/{len(batches)} ({len(batch)}개) 시작')
            with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
                futures = {executor.submit(self.analyze, article): article for article in batch}
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        analyzed.append(result)

        logger.info(f'분석 완료: {len(analyzed)}개')
        return analyzed
