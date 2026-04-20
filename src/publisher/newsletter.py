from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
from logger import get_logger
from config import config

logger = get_logger('publisher')


class NewsletterPublisher:
    def __init__(self):
        self.template_path = config.paths.templates / 'newsletter.html'
        self.output_path = config.paths.data / 'newsletter.html'

    def _load_template(self):
        if not self.template_path.exists():
            raise FileNotFoundError(f'뉴스레터 템플릿 없음: {self.template_path}')
        env = Environment(
            loader=FileSystemLoader(str(self.template_path.parent)),
            autoescape=select_autoescape(['html']),
        )
        return env.get_template(self.template_path.name)

    def _build_data(self, analyzed: list[dict], predictions: dict) -> dict:
        today = datetime.now()
        weekday_kr = ['월', '화', '수', '목', '금', '토', '일'][today.weekday()]
        week_label = f'{today.year}년 {today.month}월 {today.day}일 ({weekday_kr})'

        categories = {
            'politics_economy': '정치/경제',
            'global_macro': '글로벌 매크로',
            'tech_industry': '산업/테크',
            'real_estate': '부동산',
        }

        sections = []
        for cat_key, cat_name in categories.items():
            articles = sorted(
                [a for a in analyzed if a.get('category') == cat_key],
                key=lambda x: x.get('importance', 0),
                reverse=True
            )
            if articles:
                sections.append({'category': cat_name, 'articles': articles})

        fused = predictions.get('fused_analysis', {})
        # is_urgent 플래그 기준 — 전체 긴급 기사 노출 (상한 없음)
        urgent = [a for a in analyzed if a.get('is_urgent')]
        return {
            'date': week_label,
            'sections': sections,
            'urgent': urgent,
            'prediction': fused,
            'kronos': predictions.get('kronos_predictions', {}),
            'weekly_summary': fused.get('weekly_summary', ''),
            'last_verification': predictions.get('last_verification'),
            'accuracy': predictions.get('accuracy', {}),
        }

    def publish(self, analyzed: list[dict], predictions: dict) -> str:
        try:
            template = self._load_template()
            data = self._build_data(analyzed, predictions)
            html = template.render(**data)

            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(html)

            logger.info(f'뉴스레터 저장 완료: {self.output_path}')
            return str(self.output_path)

        except Exception as e:
            logger.error(f'뉴스레터 생성 실패: {e}')
            raise