"""
/reports 브리핑 생성기
기존 analyzed_articles + predictions를 조합해 6개 섹션 리포트 생성
"""
import json
import re
from datetime import datetime
from pathlib import Path
from logger import get_logger

logger = get_logger('report_generator')

# ──────────────────────────────────────────────
# URL → outlet 매핑
# ──────────────────────────────────────────────
_OUTLET_MAP = {
    'chosun.com':       ('조선일보', 'KR'),
    'yna.co.kr':        ('연합뉴스', 'KR'),
    'hankyung.com':     ('한국경제', 'KR'),
    'sedaily.com':      ('서울경제', 'KR'),
    'mk.co.kr':         ('매일경제', 'KR'),
    'etnews.com':       ('전자신문', 'KR'),
    'hani.co.kr':       ('한겨레', 'KR'),
    'donga.com':        ('동아일보', 'KR'),
    'asiae.co.kr':      ('아시아경제', 'KR'),
    'news.sbs.co.kr':   ('SBS', 'KR'),
    'apnews.com':       ('AP', 'US'),
    'reuters.com':      ('Reuters', 'US'),
    'wsj.com':          ('WSJ', 'US'),
    'dowjones.io':      ('WSJ', 'US'),
    'nytimes.com':      ('NYT', 'US'),
    'bloomberg.com':    ('Bloomberg', 'US'),
    'ft.com':           ('FT', 'UK'),
    'theguardian.com':  ('Guardian', 'UK'),
    'bbc.co.uk':        ('BBC', 'UK'),
    'bbc.com':          ('BBC', 'UK'),
    'economist.com':    ('Economist', 'UK'),
    'businessinsider.com': ('Business Insider', 'US'),
    'cnbc.com':         ('CNBC', 'US'),
    'marketwatch.com':  ('MarketWatch', 'US'),
    'asia.nikkei.com':  ('Nikkei', 'JP'),
    'scmp.com':         ('SCMP', 'CN'),
    'caixin.com':       ('Caixin', 'CN'),
}

def _detect_outlet(url: str) -> tuple[str, str]:
    """URL에서 (outlet_name, region) 추출. 미매핑 시 도메인 반환."""
    if not url:
        return ('Unknown', 'XX')
    for domain, info in _OUTLET_MAP.items():
        if domain in url:
            return info
    # 구글 뉴스 경유 기사는 원본 도메인 추출 시도
    m = re.search(r'articles/([A-Za-z0-9_-]+)', url)
    if 'news.google.com' in url:
        return ('Google News', 'XX')
    try:
        from urllib.parse import urlparse
        host = urlparse(url).netloc.replace('www.', '')
        return (host[:30], 'XX')
    except Exception:
        return ('Unknown', 'XX')


def _group_by_outlet(articles: list[dict]) -> dict[str, list[dict]]:
    """기사를 outlet별로 그룹핑"""
    groups: dict[str, list[dict]] = {}
    for a in articles:
        outlet, _ = _detect_outlet(a.get('link', ''))
        groups.setdefault(outlet, []).append(a)
    return groups


def _top_by_outlet(articles: list[dict], max_per_outlet: int = 2) -> list[dict]:
    """outlet당 중요도 최상위 기사 추출 → ① 섹션용"""
    groups = _group_by_outlet(articles)
    result = []
    for outlet, arts in groups.items():
        sorted_arts = sorted(arts, key=lambda x: x.get('importance') or 0, reverse=True)
        for a in sorted_arts[:max_per_outlet]:
            outlet_name, region = _detect_outlet(a.get('link', ''))
            result.append({
                'outlet': outlet_name,
                'region': region,
                'title': a.get('title', ''),
                'link': a.get('link', ''),
                'sentiment': a.get('sentiment', 'neutral'),
                'importance': a.get('importance', 0),
                'category': a.get('category', ''),
                'one_line': a.get('one_line', ''),
            })
    # 중요도 + region 정렬 (KR → US → UK → JP → CN → XX)
    region_order = {'KR': 0, 'US': 1, 'UK': 2, 'JP': 3, 'CN': 4, 'XX': 5}
    result.sort(key=lambda x: (region_order.get(x['region'], 9), -(x['importance'] or 0)))
    return result


class ReportGenerator:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.reports_dir = self.data_dir / 'reports'
        self.reports_dir.mkdir(exist_ok=True)

    def _load_articles(self) -> list[dict]:
        path = self.data_dir / 'analyzed_articles.json'
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return []

    def _load_predictions(self) -> dict:
        path = self.data_dir / 'predictions.json'
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return {}

    def _llm_analyze(self, prompt: str, max_tokens: int = 2000) -> dict:
        """LLM 호출 후 JSON 파싱. 실패 시 빈 dict."""
        try:
            from analyzer.llm import ArticleAnalyzer
            analyzer = ArticleAnalyzer()
            raw = analyzer._chat(prompt, max_tokens=max_tokens, temperature=0.3,
                                 model='llama-3.3-70b-versatile')
            # JSON 블록 추출
            m = re.search(r'\{[\s\S]+\}', raw)
            if m:
                return json.loads(m.group())
        except Exception as e:
            logger.warning(f'LLM 분석 실패: {e}')
        return {}

    # ──────────────────────────────────────────
    # 섹션별 생성 메서드
    # ──────────────────────────────────────────

    def _build_section1(self, articles: list[dict]) -> list[dict]:
        """① 언론사별 헤드라인"""
        return _top_by_outlet(articles, max_per_outlet=1)

    def _build_section2(self, articles: list[dict], predictions: dict) -> list[dict]:
        """② TOP 5 이슈 4축 입체 분석"""
        top = sorted(articles, key=lambda x: x.get('importance') or 0, reverse=True)[:15]
        summaries = [
            f"[{a.get('category','')}][중요도{a.get('importance',0)}] {a.get('title','')} — {a.get('one_line','')}"
            for a in top
        ]
        agent_debate = predictions.get('fused_analysis', {}).get('agent_debate', {})
        bull = agent_debate.get('bull', {}).get('bull_case', '')
        bear = agent_debate.get('bear', {}).get('bear_case', '')

        prompt = f"""당신은 글로벌 정치경제 분석관입니다. 아래 뉴스 헤드라인과 AI 분석을 기반으로 오늘의 핵심 이슈 TOP 5를 선별하고 각각을 4축으로 분석하세요.

뉴스 목록:
{chr(10).join(summaries)}

AI 분석 (강세론): {bull}
AI 분석 (약세론): {bear}

아래 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
  "issues": [
    {{
      "rank": 1,
      "title": "이슈 제목",
      "summary": "2-3문장 심층 요약",
      "political_intent": "정치적 의도 분석",
      "economic_interest": "경제적 실리 분석",
      "framing": "언론 프레이밍 분석",
      "security_angle": "안보적 함의",
      "market_impact": "시장 영향 분석",
      "sentiment": "positive/negative/neutral/cautious"
    }}
  ]
}}"""

        result = self._llm_analyze(prompt, max_tokens=3000)
        return result.get('issues', [])

    def _build_section3(self, top_issues: list[dict]) -> list[dict]:
        """③ 핵심 이슈별 주요국 입장 대조"""
        if not top_issues:
            return []

        issues_text = '\n'.join(
            f"{i+1}. {iss.get('title','')} — {iss.get('summary','')}"
            for i, iss in enumerate(top_issues[:3])
        )

        prompt = f"""아래 핵심 이슈들에 대해 주요국 입장을 분석하세요.

이슈:
{issues_text}

각 이슈별로 가장 직접적으로 연관된 3~4개국을 선정하고 공식 입장과 실제 속내를 분석하세요.

아래 JSON 형식으로만 응답하세요:
{{
  "stances": [
    {{
      "issue_title": "이슈 제목",
      "countries": [
        {{
          "country": "국가명",
          "flag": "🇰🇷",
          "official_position": "공식 입장 (1-2문장)",
          "real_intent": "실제 속내 분석 (1-2문장)",
          "stance_type": "지지/반대/중립/관망"
        }}
      ]
    }}
  ]
}}"""

        result = self._llm_analyze(prompt, max_tokens=2500)
        return result.get('stances', [])

    def _build_section4(self, predictions: dict) -> dict:
        """④ 데이터 통합 분석 — 기존 predictions 재가공"""
        kronos = predictions.get('kronos_predictions', {})
        xgb = predictions.get('xgb_predictions', {})
        fused = predictions.get('fused_analysis', {})
        news_impact = fused.get('news_impact', [])

        items = []
        for key, pred in kronos.items():
            label = {'kospi': 'KOSPI', 'usd_krw': 'USD/KRW', 'nasdaq': 'NASDAQ', 'samsung': '삼성전자'}.get(key, key)
            xgb_data = xgb.get(key, {})
            fused_key = fused.get(key, {}) if key in ('kospi', 'usd_krw') else {}
            items.append({
                'market': label,
                'last_close': pred.get('last_close'),
                'pred_close': pred.get('pred_close'),
                'change_pct': pred.get('change_pct'),
                'pred_range': pred.get('pred_range', {}),
                'xgb_direction': xgb_data.get('direction'),
                'xgb_confidence': xgb_data.get('confidence'),
                'ai_confidence': fused_key.get('confidence'),
                'ai_reason': fused_key.get('reason'),
            })

        return {
            'market_items': items,
            'news_impact': news_impact,
            'key_sector': fused.get('key_sector'),
            'overall_sentiment': fused.get('overall_sentiment'),
        }

    def _build_section5(self, articles: list[dict], predictions: dict) -> list[dict]:
        """⑤ 48시간 리스크 Watchlist"""
        urgent = [a for a in articles if a.get('is_urgent')]
        high_imp = sorted(articles, key=lambda x: x.get('importance') or 0, reverse=True)[:10]
        fused = predictions.get('fused_analysis', {})
        bear = fused.get('agent_debate', {}).get('bear', {})

        items_text = '\n'.join(
            f"- [{a.get('sentiment','')}] {a.get('title','')} (중요도:{a.get('importance',0)})"
            for a in (urgent + high_imp)[:12]
        )
        key_risk = bear.get('key_risk', '')

        prompt = f"""아래 뉴스와 리스크 요인을 바탕으로 향후 48시간 내 주목해야 할 리스크 이벤트 5개를 작성하세요.

주요 뉴스:
{items_text}

AI 약세 분석 핵심 리스크: {key_risk}

아래 JSON 형식으로만 응답하세요:
{{
  "watchlist": [
    {{
      "event": "이벤트/일정명",
      "scenario": "예상 시나리오 (2-3문장 상세 분석)",
      "expected_trend": "상승/하락/변동성확대/안정",
      "risk_level": "HIGH/MEDIUM/LOW",
      "affected_markets": ["KOSPI", "USD/KRW"]
    }}
  ]
}}"""

        result = self._llm_analyze(prompt, max_tokens=2000)
        return result.get('watchlist', [])

    def _build_section6(self, articles: list[dict], predictions: dict) -> dict:
        """⑥ 6카테고리 Summary Matrix"""
        fused = predictions.get('fused_analysis', {})
        weekly = fused.get('weekly_summary', '')
        overall_sent = fused.get('overall_sentiment', '')
        consensus = fused.get('agent_debate', {}).get('consensus', {})

        # 카테고리별 감성 집계
        cats = {}
        for a in articles:
            c = a.get('category', 'unknown')
            s = a.get('sentiment', 'neutral')
            cats.setdefault(c, {'positive': 0, 'negative': 0, 'neutral': 0, 'cautious': 0})
            cats[c][s] = cats[c].get(s, 0) + 1

        summaries_text = weekly or '데이터 없음'
        consensus_text = consensus.get('consensus', '')

        prompt = f"""아래 데이터를 바탕으로 글로벌 이슈 Summary Matrix를 작성하세요.

주간 요약: {summaries_text}
AI 컨센서스: {consensus_text}
전체 감성: {overall_sent}
카테고리별 기사 감성: {json.dumps(cats, ensure_ascii=False)}

기술(Technology), 경제(Economy), 정치(Politics), 안보(Security), 금융(Finance), 시장(Market) 6개 축으로 분석하세요.
마지막에 전체 정세를 관통하는 구조적 대전환과 생존 전략을 담은 심층 분석을 포함하세요.

아래 JSON 형식으로만 응답하세요:
{{
  "matrix": [
    {{
      "category": "기술",
      "category_en": "Technology",
      "status": "긍정/부정/중립/불안정",
      "key_trend": "핵심 트렌드 1-2문장",
      "risk": "주요 리스크",
      "opportunity": "기회 요인"
    }}
  ],
  "structural_analysis": "전체 정세 구조적 분석 (최소 5문장 이상, 대전환과 생존 전략 포함)"
}}"""

        result = self._llm_analyze(prompt, max_tokens=3000)
        return result

    # ──────────────────────────────────────────
    # 메인 생성 진입점
    # ──────────────────────────────────────────

    def generate(self, date: str | None = None, run_type: str = 'morning') -> dict:
        """전체 리포트 생성 후 캐시 저장. date = 'YYYY-MM-DD', run_type = 'morning'|'afternoon'"""
        date = date or datetime.now().strftime('%Y-%m-%d')
        logger.info(f'리포트 생성 시작: {date}')

        articles = self._load_articles()
        predictions = self._load_predictions()

        if not articles:
            logger.warning('기사 데이터 없음 — 빈 리포트 반환')
            return self._empty(date)

        logger.info(f'기사 {len(articles)}개 로드')

        sec1 = self._build_section1(articles)
        logger.info('① 헤드라인 완료')

        sec2 = self._build_section2(articles, predictions)
        logger.info('② TOP 5 이슈 완료')

        sec3 = self._build_section3(sec2)
        logger.info('③ 국가 입장 완료')

        sec4 = self._build_section4(predictions)
        logger.info('④ 데이터 연계 완료')

        sec5 = self._build_section5(articles, predictions)
        logger.info('⑤ 리스크 워치리스트 완료')

        sec6 = self._build_section6(articles, predictions)
        logger.info('⑥ Summary Matrix 완료')

        report = {
            'date': date,
            'run_type': run_type,
            'generated_at': datetime.now().isoformat(),
            'articles_count': len(articles),
            'sections': {
                'headlines': sec1,
                'top_issues': sec2,
                'country_stances': sec3,
                'market_data': sec4,
                'risk_watchlist': sec5,
                'summary_matrix': sec6,
            }
        }

        # 저장
        out_path = self.reports_dir / f'{date}_{run_type}.json'
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        # latest.json도 갱신
        latest_path = self.reports_dir / 'latest.json'
        latest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

        logger.info(f'리포트 저장 완료: {out_path}')
        return report

    def load_latest(self) -> dict | None:
        """최신 캐시 리포트 반환"""
        latest = self.reports_dir / 'latest.json'
        if latest.exists():
            try:
                return json.loads(latest.read_text(encoding='utf-8'))
            except Exception:
                pass
        return None

    def list_sessions(self) -> list[dict]:
        """저장된 리포트 세션 목록 (최신순) — {date, run_type} 반환"""
        sessions = []
        seen = set()
        # 신포맷: YYYY-MM-DD_morning.json / YYYY-MM-DD_afternoon.json
        for f in self.reports_dir.glob('????-??-??_*.json'):
            parts = f.stem.rsplit('_', 1)
            if len(parts) == 2 and parts[1] in ('morning', 'afternoon'):
                key = (parts[0], parts[1])
                if key not in seen:
                    seen.add(key)
                    sessions.append({'date': parts[0], 'run_type': parts[1]})
        # 구포맷: YYYY-MM-DD.json → morning으로 처리
        for f in self.reports_dir.glob('????-??-??.json'):
            if f.stem in ('latest',):
                continue
            key = (f.stem, 'morning')
            if key not in seen:
                seen.add(key)
                sessions.append({'date': f.stem, 'run_type': 'morning'})
        return sorted(sessions, key=lambda x: (x['date'], x['run_type']), reverse=True)

    def list_dates(self) -> list[str]:
        """하위호환: 날짜 목록만 반환"""
        return sorted({s['date'] for s in self.list_sessions()}, reverse=True)

    def load_by_date(self, date: str, run_type: str = 'morning') -> dict | None:
        candidates = [
            self.reports_dir / f'{date}_{run_type}.json',  # 신포맷
            self.reports_dir / f'{date}.json',              # 구포맷 (morning fallback)
        ]
        # 다른 run_type도 fallback 후보에 추가
        for rt in ('morning', 'afternoon'):
            if rt != run_type:
                candidates.append(self.reports_dir / f'{date}_{rt}.json')

        for path in candidates:
            if path.exists():
                try:
                    return json.loads(path.read_text(encoding='utf-8'))
                except Exception:
                    continue
        return None

    def _empty(self, date: str) -> dict:
        return {
            'date': date,
            'generated_at': datetime.now().isoformat(),
            'articles_count': 0,
            'sections': {
                'headlines': [],
                'top_issues': [],
                'country_stances': [],
                'market_data': {},
                'risk_watchlist': [],
                'summary_matrix': {},
            }
        }
