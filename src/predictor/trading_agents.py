"""
TradingAgents — 멀티에이전트 시장 분석 토론 시스템
BullAgent (강세론) vs BearAgent (약세론) 토론 후 Mediator가 균형 분석 생성

fusion.py에서 단일 LLM 판단을 보완하는 교차검증 레이어.
"""
import json
import re
import time
import httpx
from logger import get_logger
from config import config
from utils.groq_utils import parse_reset_seconds as _parse_reset_seconds

logger = get_logger('predictor.agents')

_GROQ_BASE_URL = 'https://api.groq.com/openai/v1'
_AGENT_MODEL = 'llama-3.3-70b-versatile'
_FALLBACK_MODELS = [
    'llama-3.3-70b-versatile',
    'meta-llama/llama-4-scout-17b-16e-instruct',
    'llama-3.1-8b-instant',
]




def _groq_chat(api_key: str, prompt: str, max_tokens: int = 400) -> str:
    for model in _FALLBACK_MODELS:
        for attempt in range(1):
            try:
                resp = httpx.post(
                    f'{_GROQ_BASE_URL}/chat/completions',
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': model,
                        'messages': [{'role': 'user', 'content': prompt}],
                        'max_tokens': max_tokens,
                        'temperature': 0.2,
                    },
                    timeout=30,
                )
                if resp.status_code == 429:
                    logger.warning(f'Groq 429 (model={model}) → 다음 모델로 폴백')
                    break  # retry 없이 즉시 다음 모델로
                resp.raise_for_status()
                content = resp.json()['choices'][0]['message']['content'].strip()
                if model != _AGENT_MODEL:
                    logger.info(f'agents 폴백 성공: {_AGENT_MODEL} → {model}')
                return content
            except httpx.HTTPStatusError as e:
                logger.warning(f'Groq HTTP {e.response.status_code} (model={model})')
            except Exception as e:
                logger.warning(f'Groq agent 실패 (model={model}): {e}')
        logger.warning(f'agents 모델 실패, 다음 폴백으로: {model}')
    raise RuntimeError('Groq agent 모든 폴백 실패')


def _parse_json(text: str) -> dict:
    text = re.sub(r'<think>[\s\S]*?</think>', '', text)
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text).strip()
    s = text.find('{')
    e = text.rfind('}') + 1
    if s != -1 and e > s:
        try:
            return json.loads(text[s:e])
        except json.JSONDecodeError:
            pass
    raise ValueError(f'JSON 파싱 실패: {repr(text[:100])}')


class BullAgent:
    """강세론자 — 긍정적 신호를 발굴하고 상승 근거를 제시"""

    def __init__(self, api_key: str):
        self._key = api_key

    def argue(self, context: str) -> dict:
        prompt = f'''당신은 낙관적 주식 분석가(Bull)입니다. 아래 시장 데이터에서 상승 근거만 찾아 주장하세요.

{context}

confidence는 반드시 데이터 분석에 따라 40~90 범위에서 결정하세요. 예시값을 복사하지 마세요.
JSON만 응답:
{{"bull_case": "상승 근거 2~3문장", "key_catalyst": "핵심 모멘텀 한 가지", "target_markets": ["관련 시장"], "confidence": (40~90 중 분석 결과)}}
JSON:'''
        try:
            text = _groq_chat(self._key, prompt, max_tokens=300)
            result = _parse_json(text)
            logger.info(f'BullAgent: {result.get("key_catalyst", "")} (confidence={result.get("confidence")})')
            return result
        except Exception as e:
            logger.warning(f'BullAgent 실패: {e}')
            return {'bull_case': '', 'key_catalyst': '', 'target_markets': [], 'confidence': 50}


class BearAgent:
    """약세론자 — 리스크와 하락 요인을 발굴해 경고"""

    def __init__(self, api_key: str):
        self._key = api_key

    def argue(self, context: str) -> dict:
        prompt = f'''당신은 비관적 리스크 분석가(Bear)입니다. 아래 시장 데이터에서 하락 위험 요인만 찾아 경고하세요.

{context}

confidence는 반드시 데이터 분석에 따라 40~90 범위에서 결정하세요. 예시값을 복사하지 마세요.
JSON만 응답:
{{"bear_case": "하락 위험 2~3문장", "key_risk": "핵심 리스크 한 가지", "vulnerable_markets": ["관련 시장"], "confidence": (40~90 중 분석 결과)}}
JSON:'''
        try:
            text = _groq_chat(self._key, prompt, max_tokens=300)
            result = _parse_json(text)
            logger.info(f'BearAgent: {result.get("key_risk", "")} (confidence={result.get("confidence")})')
            return result
        except Exception as e:
            logger.warning(f'BearAgent 실패: {e}')
            return {'bear_case': '', 'key_risk': '', 'vulnerable_markets': [], 'confidence': 50}


class Mediator:
    """중재자 — Bull/Bear 주장을 종합해 최종 균형 판단 생성"""

    def __init__(self, api_key: str):
        self._key = api_key

    def mediate(self, bull: dict, bear: dict, kronos_summary: str, sentiment_score: float) -> dict:
        prompt = f'''당신은 중립적 수석 애널리스트입니다. 아래 강세론과 약세론을 종합해 균형 잡힌 최종 판단을 내리세요.

[강세론]
{bull.get("bull_case", "없음")}
핵심 모멘텀: {bull.get("key_catalyst", "없음")}
자신감: {bull.get("confidence", 50)}%

[약세론]
{bear.get("bear_case", "없음")}
핵심 리스크: {bear.get("key_risk", "없음")}
자신감: {bear.get("confidence", 50)}%

[Kronos 시계열 예측]
{kronos_summary}

[감성 점수] {sentiment_score:+.2f} (-1=극단 부정, +1=극단 긍정)

bull_weight + bear_weight = 100이어야 합니다.
모든 숫자는 데이터 분석에 따라 결정하세요. 예시값(55/45/68)을 그대로 복사하지 마세요.
다음 JSON만 응답:
{{"consensus": "균형 판단 2~3문장", "bull_weight": (30~70), "bear_weight": (30~70), "net_direction": "상승|하락|횡보", "key_risk": "리스크 요약", "key_opportunity": "기회 요약", "agent_confidence": (40~85)}}
JSON:'''
        try:
            time.sleep(6)  # TPM 보호
            text = _groq_chat(self._key, prompt, max_tokens=350)
            result = _parse_json(text)
            logger.info(
                f'Mediator: {result.get("net_direction")} '
                f'(bull={result.get("bull_weight")}% / bear={result.get("bear_weight")}%, '
                f'confidence={result.get("agent_confidence")}%)'
            )
            return result
        except Exception as e:
            logger.warning(f'Mediator 실패: {e}')
            return {
                'consensus': '',
                'bull_weight': 50,
                'bear_weight': 50,
                'net_direction': '횡보',
                'key_risk': bear.get('key_risk', ''),
                'key_opportunity': bull.get('key_catalyst', ''),
                'agent_confidence': 50,
            }


class AgentDebate:
    """Bull-Bear 토론 오케스트레이터"""

    def __init__(self):
        key = config.model.groq_key
        if not key:
            raise RuntimeError('GROQ_API_KEY 미설정 — TradingAgents 사용 불가')
        self.bull = BullAgent(key)
        self.bear = BearAgent(key)
        self.mediator = Mediator(key)

    def run(self, analyzed: list[dict], kronos_predictions: dict,
            sentiment_score: float) -> dict:
        """
        analyzed: LLM 분석 기사 목록
        kronos_predictions: Kronos 시계열 예측값
        sentiment_score: 가중 감성 점수

        Returns: {bull, bear, consensus}
        """
        # 컨텍스트 문자열 구성
        issues_text = '\n'.join(
            f'- {a["issue"]}' for a in analyzed if a.get('issue')
        )[:1200]

        kronos_summary = '\n'.join(
            f'- {name}: {v["direction"]} ({v["change_pct"]:+.2f}%)'
            for name, v in kronos_predictions.items() if v
        )

        context = f'''[이번 주 주요 뉴스 이슈]
{issues_text}

[Kronos 시계열 예측]
{kronos_summary}

[시장 감성 점수] {sentiment_score:+.2f}'''

        logger.info('TradingAgents 토론 시작...')

        # Bull → (6s delay inside mediator) → Bear → Mediator
        bull_result = self.bull.argue(context)
        time.sleep(6)  # TPM
        bear_result = self.bear.argue(context)

        consensus = self.mediator.mediate(
            bull_result, bear_result, kronos_summary, sentiment_score
        )

        return {
            'bull': bull_result,
            'bear': bear_result,
            'consensus': consensus,
        }
