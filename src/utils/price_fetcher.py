"""
가격 데이터 수집 유틸리티
yfinance 1차 시도 → OpenBB fallback
"""
import yfinance as yf
import pandas as pd
from datetime import datetime
from logger import get_logger

logger = get_logger('utils.price_fetcher')

# ticker → OpenBB endpoint 분류
_INDEX_TICKERS = {'^KS11', '^IXIC', '^GSPC', '^DJI'}
_CURRENCY_TICKERS = {'KRW=X', 'JPY=X', 'EUR=X'}


def fetch_ohlcv(ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    종가 DataFrame 반환. yfinance 실패 시 OpenBB로 재시도.
    반환: DatetimeIndex + 'Close' 컬럼 (또는 빈 DataFrame)
    """
    df = _fetch_yfinance(ticker, start, end)
    if not df.empty:
        return df

    logger.info(f'{ticker}: yfinance 빈 결과 → OpenBB 재시도')
    return _fetch_openbb(ticker, start, end)


def _fetch_yfinance(ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(
            start=start.strftime('%Y-%m-%d'),
            end=end.strftime('%Y-%m-%d'),
        )
        if df.empty:
            return pd.DataFrame()
        return df[['Close']].rename(columns={'Close': 'close'})
    except Exception as e:
        logger.warning(f'{ticker}: yfinance 오류 ({e})')
        return pd.DataFrame()


def _fetch_openbb(ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
    try:
        from openbb import obb
        start_s = start.strftime('%Y-%m-%d')
        end_s = end.strftime('%Y-%m-%d')

        if ticker in _CURRENCY_TICKERS:
            r = obb.currency.price.historical(ticker, start_date=start_s, end_date=end_s, provider='yfinance')
        elif ticker in _INDEX_TICKERS:
            r = obb.index.price.historical(ticker, start_date=start_s, end_date=end_s, provider='yfinance')
        else:
            r = obb.equity.price.historical(ticker, start_date=start_s, end_date=end_s, provider='yfinance')

        df = r.to_df()
        if df.empty:
            return pd.DataFrame()

        df = df[['close']].copy()
        df.index = pd.to_datetime(df.index)
        logger.info(f'{ticker}: OpenBB fallback 성공 ({len(df)}행)')
        return df
    except Exception as e:
        logger.warning(f'{ticker}: OpenBB 오류 ({e})')
        return pd.DataFrame()
