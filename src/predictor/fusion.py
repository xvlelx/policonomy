import json
import re
import time
import httpx
from logger import get_logger
from config import config
from utils.groq_utils import parse_reset_seconds as _parse_reset_seconds

logger = get_logger('predictor.fusion')

_GROQ_BASE_URL = 'https://api.groq.com/openai/v1'
_MODEL = 'llama-3.3-70b-versatile'
_FALLBACK_MODELS = [
    'llama-3.3-70b-versatile',
    'meta-llama/llama-4-scout-17b-16e-instruct',
    'llama-3.1-8b-instant',
]

_CATEGORY_MARKET_MAP: dict[str, list[str]] = {
    'politics_economy': ['kospi', 'usd_krw'],
    'global_macro': ['nasdaq', 'sp500', 'kospi', 'usd_krw'],
    'tech_industry': ['nasdaq', 'sp500', 'dow', 'nvidia', 'samsung', 'skhynix'],
    'real_estate': ['kospi'],
}

_KOSPI_CATEGORIES = {'politics_economy', 'real_estate'}
_US_CATEGORIES = {'global_macro', 'tech_industry'}
_KOSPI_MARKETS = {'kospi', 'usd_krw', 'samsung', 'skhynix'}
_US_MARKETS = {'nasdaq', 'sp500', 'dow', 'nvidia'}

_CATEGORY_LABELS: dict[str, str] = {
    'politics_economy': '정치·경제',
    'global_macro': '글로벌 매크로',
    'tech_industry': '기술·산업',
    'real_estate': '부동산',
}



class PredictionFusion:
    def __init__(self):
        self._api_key = config.model.groq_key

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
            except json.JSONDecodeError as err:
                raise ValueError(f'JSON 파싱 실패: {repr(text[:100])}') from err
        raise ValueError(f'JSON 없음: {repr(text[:100])}')

    def _chat(self, prompt: str) -> str:
        for model in _FALLBACK_MODELS:
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
                        'max_tokens': 1024,
                        'temperature': 0.1,
                    },
                    timeout=30,
                )

                if resp.status_code == 429:
                    logger.warning(f'Groq 429 (model={model}) → 다음 모델로 폴백')
                    continue

                resp.raise_for_status()
                content = resp.json()['choices'][0]['message']['content'].strip()
                if model != _MODEL:
                    logger.info(f'fusion 폴백 성공: {_MODEL} → {model}')
                return content

            except httpx.HTTPStatusError as e:
                logger.warning(f'Groq HTTP {e.response.status_code} (model={model})')
            except Exception as e:
                logger.warning(f'Groq fusion 실패 (model={model}): {e}')
            logger.warning(f'fusion 모델 실패, 다음 폴백으로: {model}')

        raise RuntimeError('Groq fusion 모든 폴백 실패')

    def _compute_sentiment_score(self, analyzed: list[dict]) -> float:
        """분석 기사에서 가중 sentiment 점수 계산 (-1 ~ +1)"""
        sentiment_map = {'positive': 1, 'negative': -1, 'neutral': 0}
        total_weight = 0
        weighted_sum = 0.0
        for a in analyzed:
            val = sentiment_map.get(a.get('sentiment', 'neutral'), 0)
            importance = float(a.get('importance', 5))
            weighted_sum += val * importance
            total_weight += importance
        if total_weight == 0:
            return 0.0
        return weighted_sum / total_weight

    def _apply_sentiment_correction(self, predictions: dict, score: float) -> dict:
        """sentiment 점수로 Kronos 예측값 보정 (|score| > 0.2 일 때만 적용)"""
        if abs(score) <= 0.2:
            return predictions  # 중립 구간 — 보정 없음

        corrected = {}
        factor = 1.0 + (score * 0.3)  # score=-1 → 0.7배, score=+1 → 1.3배

        for name, v in predictions.items():
            if not v:
                corrected[name] = v
                continue

            orig_pct = v['change_pct']
            if orig_pct >= 0:
                adj_pct = orig_pct * factor
            else:
                adj_pct = orig_pct * (2.0 - factor)  # 음수엔 반전 적용

            if adj_pct > 0.1:
                new_dir = '상승'
            elif adj_pct < -0.1:
                new_dir = '하락'
            else:
                new_dir = '횡보'

            corrected[name] = {
                **v,
                'change_pct': round(adj_pct, 2),
                'direction': new_dir,
                'original_change_pct': orig_pct,
                'original_direction': v['direction'],
                'sentiment_correction': round(score, 3),
            }
            if new_dir != v['direction']:
                logger.info(f'  {name}: {v["direction"]}({orig_pct:+.2f}%) → {new_dir}({adj_pct:+.2f}%) [score={score:+.2f}]')
            else:
                logger.info(f'  {name}: {v["direction"]} {orig_pct:+.2f}% → {adj_pct:+.2f}% [score={score:+.2f}]')

        return corrected

    def _build_news_impact(self, analyzed: list[dict]) -> list[dict]:
        """카테고리별 뉴스 감성 분포 + 영향 시장 매핑"""
        from collections import defaultdict
        cats: dict = defaultdict(lambda: {'positive': 0, 'negative': 0, 'neutral': 0, 'imp_sum': 0.0})
        for a in analyzed:
            cat = a.get('category', 'unknown')
            s = a.get('sentiment', 'neutral')
            imp = float(a.get('importance', 5))
            cats[cat][s if s in ('positive', 'negative', 'neutral') else 'neutral'] += 1
            cats[cat]['imp_sum'] += imp

        result = []
        for cat_key, counts in cats.items():
            total = counts['positive'] + counts['negative'] + counts['neutral']
            net = (counts['positive'] - counts['negative']) / total if total > 0 else 0.0
            result.append({
                'category': cat_key,
                'label': _CATEGORY_LABELS.get(cat_key, cat_key),
                'positive': counts['positive'],
                'negative': counts['negative'],
                'neutral': counts['neutral'],
                'total': total,
                'net_score': round(net, 2),
                'markets': _CATEGORY_MARKET_MAP.get(cat_key, []),
            })
        result.sort(key=lambda x: -abs(x['net_score']))
        return result

    def fuse(self, predictions: dict, analyzed: list[dict]) -> dict:
        try:
            # sentiment 보정
            score = self._compute_sentiment_score(analyzed)
            corrected = self._apply_sentiment_correction(predictions, score)
            logger.info(f'sentiment 보정 점수: {score:+.3f} ({"적용" if abs(score) > 0.2 else "중립 — 미적용"})')

            # 분석된 기사 전체 이슈 활용 (전체)
            issues = [a['issue'] for a in analyzed if a.get('issue')]
            issues_text = '\n'.join(f'- {issue}' for issue in issues)

            kronos_summary = '\n'.join([
                f'- {name}: {v["direction"]} ({v["change_pct"]:+.2f}%)'
                + (f' [보정 전: {v["original_direction"]} {v["original_change_pct"]:+.2f}%]' if 'original_change_pct' in v else '')
                for name, v in corrected.items() if v
            ])

            prompt = f'''You are a financial analyst. Based on the sentiment-adjusted predictions and this week's key news, provide a fused market outlook.

Predictions (Kronos + sentiment correction, score={score:+.2f}):
{kronos_summary}

Key news issues this week:
{issues_text}

Respond ONLY with valid JSON, no markdown:
{{"kospi": {{"direction": "상승", "reason": "근거 한 문장", "confidence": 72}}, "usd_krw": {{"direction": "약세", "reason": "근거 한 문장", "confidence": 65}}, "samsung": {{"direction": "상승", "reason": "근거 한 문장", "confidence": 68}}, "nasdaq": {{"direction": "상승", "reason": "근거 한 문장", "confidence": 70}}, "key_sector": {{"name": "반도체", "direction": "강세", "reason": "근거 한 문장"}}, "overall_sentiment": "positive", "weekly_summary": "이번 주 시장 종합 요약 2~3문장"}}

JSON:'''

            text = self._chat(prompt)
            result = self._parse_json(text)
            result['sentiment_score'] = round(score, 3)
            result['corrected_predictions'] = corrected
            result['news_impact'] = self._build_news_impact(analyzed)
            logger.info(f'예측 융합 완료 (기사 {len(issues)}개 활용, overall={result.get("overall_sentiment")}, sentiment_score={score:+.3f})')

            # TradingAgents 멀티에이전트 토론 (국장 / 미장 분리)
            try:
                from predictor.trading_agents import AgentDebate
                debate = AgentDebate()

                # 국장 토론: 정치·경제, 부동산 기사 + 국장 종목 예측
                kospi_articles = [a for a in analyzed if a.get('category') in _KOSPI_CATEGORIES]
                kospi_preds = {k: v for k, v in corrected.items() if k in _KOSPI_MARKETS}
                if not kospi_articles:
                    kospi_articles = analyzed  # fallback
                kospi_debate = debate.run(kospi_articles, kospi_preds, score)
                result['kospi_debate'] = kospi_debate
                logger.info(
                    f'국장 TradingAgents 완료 — net_direction={kospi_debate["consensus"].get("net_direction")}, '
                    f'confidence={kospi_debate["consensus"].get("agent_confidence")}%'
                )

                import time as _time
                _time.sleep(8)  # 두 번째 토론 전 TPM 보호

                # 미장 토론: 글로벌 매크로, 테크 기사 + 미장 종목 예측
                us_articles = [a for a in analyzed if a.get('category') in _US_CATEGORIES]
                us_preds = {k: v for k, v in corrected.items() if k in _US_MARKETS}
                if not us_articles:
                    us_articles = analyzed  # fallback
                us_debate = debate.run(us_articles, us_preds, score)
                result['us_debate'] = us_debate
                logger.info(
                    f'미장 TradingAgents 완료 — net_direction={us_debate["consensus"].get("net_direction")}, '
                    f'confidence={us_debate["consensus"].get("agent_confidence")}%'
                )

                # 하위호환: agent_debate도 국장 토론으로 설정
                result['agent_debate'] = kospi_debate

            except RuntimeError as e:
                logger.warning(f'TradingAgents 건너뜀 (Groq 한도 초과 또는 모델 미응답): {e}')
                result['kospi_debate'] = None
                result['us_debate'] = None
                result['agent_debate'] = None
            except Exception as e:
                logger.error(f'TradingAgents 예외 발생 (무시하고 계속): {type(e).__name__}: {e}')
                result['kospi_debate'] = None
                result['us_debate'] = None
                result['agent_debate'] = None

            return result

        except Exception as e:
            logger.error(f'예측 융합 실패: {e}')
            return {}
