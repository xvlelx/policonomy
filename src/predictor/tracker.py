import json
import pandas as pd
from datetime import datetime, timedelta
from logger import get_logger
from config import config
from utils.price_fetcher import fetch_ohlcv

logger = get_logger('predictor.tracker')


class PredictionTracker:
    """
    JSON 파일 기반 예측 추적기. 실시간 파이프라인 기록은 DailyRecord(SQLite)가 담당.
    이 클래스는 Kronos 예측 이력 및 주간 검증에만 사용.
    """
    def __init__(self):
        self.history_path = config.paths.data / 'prediction_history.json'
        self.history = self._load_history()

    def _load_history(self) -> list:
        if self.history_path.exists():
            with open(self.history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save_history(self):
        with open(self.history_path, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def _get_actual_price(self, ticker: str) -> float | None:
        '''지난 주 실제 종가 가져오기 (yfinance → OpenBB fallback)'''
        try:
            end = datetime.now()
            start = end - timedelta(days=7)
            df = fetch_ohlcv(ticker, start, end)
            if df.empty:
                return None
            return float(df['close'].iloc[-1])
        except Exception as e:
            logger.warning(f'{ticker} 실제값 수집 실패: {e}')
            return None

    def verify_last_prediction(self) -> dict | None:
        '''지난 주 예측 검증'''
        if not self.history:
            logger.info('검증할 예측 기록 없음')
            return None

        last = self.history[-1]

        # 이미 검증됐으면 스킵
        if last.get('verified'):
            logger.info('이미 검증된 예측')
            return last

        tickers = {
            'kospi': '^KS11',
            'usd_krw': 'KRW=X',
            'samsung': '005930.KS',
            'nasdaq': '^IXIC',
        }

        results = []
        for name, pred_data in last['predictions'].items():
            ticker = tickers.get(name)
            if not ticker:
                continue

            actual_price = self._get_actual_price(ticker)
            if actual_price is None:
                continue

            pred_close = pred_data['pred_close']
            last_close = pred_data['last_close']

            # 실제 변화율
            actual_change = (actual_price - last_close) / last_close * 100
            actual_direction = '상승' if actual_change > 0 else '하락'

            # 방향 적중 여부
            direction_hit = pred_data['direction'] == actual_direction

            # 범위 적중 여부
            pred_high = pred_data['pred_range']['high']
            pred_low = pred_data['pred_range']['low']
            range_hit = pred_low <= actual_price <= pred_high

            result = {
                'name': name,
                'pred_direction': pred_data['direction'],
                'pred_close': pred_close,
                'actual_close': round(actual_price, 2),
                'actual_change': round(actual_change, 2),
                'actual_direction': actual_direction,
                'direction_hit': direction_hit,
                'range_hit': range_hit,
            }
            results.append(result)
            logger.info(
                f'{name}: 예측 {pred_data["direction"]} → 실제 {actual_direction} '
                f'{"✅ 적중" if direction_hit else "❌ 미스"}'
            )

        last['verified'] = True
        last['verification_date'] = datetime.now().isoformat()
        last['results'] = results
        self._save_history()

        return last

    def save_prediction(self, predictions: dict):
        '''이번 주 예측 저장 (같은 주 재실행 시 덮어쓰기)'''
        week = datetime.now().strftime('%Y-%m-%d')
        for i, record in enumerate(self.history):
            if record.get('week') == week:
                self.history[i] = {**record, 'predictions': predictions}
                self._save_history()
                logger.info(f'예측 기록 갱신: {week}')
                return
        record = {
            'week': week,
            'predictions': predictions,
            'verified': False,
            'results': []
        }
        self.history.append(record)
        self._save_history()
        logger.info(f'예측 기록 저장 완료: {week}')

    def get_accuracy(self) -> dict:
        '''누적 적중률 계산'''
        verified = [h for h in self.history if h.get('verified')]
        if not verified:
            return {'direction_accuracy': 0, 'range_accuracy': 0, 'total_weeks': 0}

        direction_hits = 0
        range_hits = 0
        total = 0

        for record in verified:
            for result in record.get('results', []):
                total += 1
                if result.get('direction_hit'):
                    direction_hits += 1
                if result.get('range_hit'):
                    range_hits += 1

        return {
            'direction_accuracy': round(direction_hits / total * 100, 1) if total > 0 else 0,
            'range_accuracy': round(range_hits / total * 100, 1) if total > 0 else 0,
            'total_weeks': len(verified),
            'total_predictions': total,
        }
