import sys
import time
from pathlib import Path
import torch
import pandas as pd
from logger import get_logger
from config import config
from utils.price_fetcher import fetch_ohlcv

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'third_party' / 'Kronos'))
from model import Kronos, KronosTokenizer, KronosPredictor

logger = get_logger('predictor.kronos')


class MarketPredictor:
    def __init__(self):
        self._predictor = None
        self._device = None

    def _load(self):
        if self._predictor is not None:
            return self._predictor

        # MPS 우선, 실패하면 CPU
        for device_str in (['mps', 'cpu'] if torch.backends.mps.is_available() else ['cpu']):
            try:
                self._device = torch.device(device_str)
                logger.info(f'Kronos 모델 로딩... (device={self._device})')
                tokenizer = KronosTokenizer.from_pretrained(config.predictor.kronos_tokenizer)
                model = Kronos.from_pretrained(config.predictor.kronos_model).to(self._device)
                self._predictor = KronosPredictor(model, tokenizer, max_context=512)
                logger.info(f'Kronos 로드 완료 (device={self._device})')
                return self._predictor
            except Exception as e:
                logger.warning(f'Kronos 로드 실패 (device={device_str}): {e}')
                self._predictor = None

        raise RuntimeError('Kronos 모델 로드 실패 (MPS/CPU 모두 시도)')

    def _get_ohlcv(self, ticker: str, period: str = '2y', retries: int = 3) -> pd.DataFrame:
        from datetime import datetime, timedelta
        import yfinance as yf

        # period → start/end 변환 (OpenBB fallback용)
        if period.endswith('mo'):
            months = int(period[:-2])
        elif period.endswith('y'):
            months = int(period[:-1]) * 12
        else:
            months = 24
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=months * 31)

        last_err = None
        for attempt in range(retries):
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(period=period)
                if df.empty:
                    raise ValueError(f'{ticker}: 빈 데이터')
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
                df.columns = ['open', 'high', 'low', 'close', 'volume']
                df.index = pd.to_datetime(df.index)
                df = df.dropna()
                if len(df) < 30:
                    raise ValueError(f'{ticker}: 데이터 부족 ({len(df)}행)')
                return df
            except Exception as e:
                last_err = e
                logger.warning(f'{ticker} yfinance 실패 (attempt {attempt+1}/{retries}): {e}')
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)

        # OpenBB fallback
        logger.info(f'{ticker}: OpenBB fallback 시도')
        df = fetch_ohlcv(ticker, start_dt, end_dt)
        if not df.empty and len(df) >= 30:
            for col in ['open', 'high', 'low', 'volume']:
                if col not in df.columns:
                    df[col] = df['close']
            return df[['open', 'high', 'low', 'close', 'volume']] if 'volume' in df.columns else df[['close']].assign(open=df['close'], high=df['close'], low=df['close'], volume=0)[['open', 'high', 'low', 'close', 'volume']]
        raise RuntimeError(f'{ticker} OHLCV 수신 불가: {last_err}')

    def predict(self, name: str, ticker: str) -> dict:
        predictor = self._load()
        pred_days = config.predictor.pred_days
        lookback = config.predictor.lookback

        df = self._get_ohlcv(ticker)
        # 가장 최근 lookback 거래일을 입력으로, 마지막 거래일 이후 pred_days 영업일을 예측
        lookback = min(lookback, len(df))
        if lookback < 10:
            raise ValueError(f'{name}: lookback={lookback} 너무 짧음 (데이터 {len(df)}행)')

        hist = df.iloc[-lookback:]
        hist_index = pd.to_datetime(hist.index)
        if hist_index.tz is not None:
            hist_index = hist_index.tz_localize(None)
        future_index = pd.bdate_range(
            start=hist_index[-1] + pd.Timedelta(days=1), periods=pred_days
        )

        for attempt in range(2):
            try:
                x_df = hist[['open', 'high', 'low', 'close', 'volume']].reset_index(drop=True)
                x_ts = pd.Series(hist_index)
                y_ts = pd.Series(future_index)

                pred_df = predictor.predict(
                    df=x_df, x_timestamp=x_ts, y_timestamp=y_ts,
                    pred_len=pred_days, T=1.0, top_p=0.9, sample_count=3
                )

                last_close = float(hist['close'].iloc[-1])
                pred_close = float(pred_df['close'].iloc[-1])
                if last_close == 0:
                    raise ValueError(f'{name}: last_close=0, 등락률 계산 불가')
                change_pct = (pred_close - last_close) / last_close * 100

                result = {
                    'name': name,
                    'last_close': round(last_close, 2),
                    'pred_close': round(pred_close, 2),
                    'change_pct': round(change_pct, 2),
                    'direction': '상승' if change_pct > 0 else '하락',
                    'pred_range': {
                        'high': round(float(pred_df['high'].max()), 2),
                        'low': round(float(pred_df['low'].min()), 2),
                    }
                }
                logger.info(f'{name}: {result["direction"]} ({change_pct:+.2f}%)')
                return result

            except Exception as e:
                if attempt == 0 and self._device and self._device.type == 'mps':
                    # MPS 연산 오류 → CPU로 재시도
                    logger.warning(f'{name} MPS 예측 오류, CPU로 재시도: {e}')
                    self._device = torch.device('cpu')
                    self._predictor.model = self._predictor.model.to(self._device)
                else:
                    raise

        raise RuntimeError(f'{name} 예측 실패')

    def run(self) -> dict:
        predictions = {}
        failed = []
        for name, ticker in config.predictor.market_targets.items():
            try:
                result = self.predict(name, ticker)
                predictions[name] = result
            except Exception as e:
                logger.error(f'{name} ({ticker}) 예측 실패: {e}')
                failed.append(name)

        if len(predictions) < 2:
            raise RuntimeError(
                f'예측 성공 {len(predictions)}개 — 최소 2개 필요 (실패: {failed})'
            )
        if failed:
            logger.warning(f'일부 예측 실패 ({len(failed)}개): {failed} — 나머지 {len(predictions)}개로 진행')

        logger.info(f'예측 완료: {len(predictions)}개 지수')
        return predictions
