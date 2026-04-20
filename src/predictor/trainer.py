"""
XGBoost 학습 모듈
backfill_records + weekly_records → 모델 학습 → data/models/ 저장
파이프라인에서 매주 자동 재학습

실행 (단독):
    conda run -n Policonomy python src/predictor/trainer.py
"""
import json
import joblib
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).parent.parent))
from logger import get_logger
from config import config

logger = get_logger('predictor.trainer')

_TARGETS = ['kospi', 'usdkrw', 'samsung', 'nasdaq']
_MODEL_DIR = config.paths.data / 'models'


class WeeklyTrainer:
    def __init__(self):
        self.db_path = config.paths.data / 'policonomy.db'
        _MODEL_DIR.mkdir(parents=True, exist_ok=True)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------ #
    # 1. 데이터 로드                                                        #
    # ------------------------------------------------------------------ #
    def _load_data(self) -> pd.DataFrame:
        """backfill_records + weekly_records 통합 로드"""
        with self._conn() as conn:
            # 백필 데이터
            bf = pd.DataFrame([dict(r) for r in conn.execute(
                '''SELECT week, sentiment_score,
                          kospi_actual_change, usdkrw_actual_change,
                          samsung_actual_change, nasdaq_actual_change,
                          kospi_next_dir, usdkrw_next_dir,
                          samsung_next_dir, nasdaq_next_dir
                   FROM backfill_records
                   WHERE kospi_actual_change IS NOT NULL
                   ORDER BY week'''
            ).fetchall()])

            # 실시간 수집 데이터 (검증 완료된 것만) — weekly_records + daily_records 통합
            _rt_sql = '''
                SELECT week AS week,
                       (politics_pos - politics_neg + global_pos - global_neg +
                        tech_pos - tech_neg + realestate_pos - realestate_neg) * 1.0 /
                       NULLIF(total_articles, 0) AS sentiment_score,
                       (politics_pos - politics_neg) * 1.0 / NULLIF(total_articles, 0) AS politics_ratio,
                       (global_pos - global_neg) * 1.0 / NULLIF(total_articles, 0) AS global_ratio,
                       (tech_pos - tech_neg) * 1.0 / NULLIF(total_articles, 0) AS tech_ratio,
                       (realestate_pos - realestate_neg) * 1.0 / NULLIF(total_articles, 0) AS realestate_ratio,
                       politics_pos * 1.0 / NULLIF(total_articles, 0) AS politics_pos_ratio,
                       global_pos * 1.0 / NULLIF(total_articles, 0) AS global_pos_ratio,
                       tech_pos * 1.0 / NULLIF(total_articles, 0) AS tech_pos_ratio,
                       kospi_actual_change, usdkrw_actual_change,
                       samsung_actual_change, nasdaq_actual_change,
                       NULL AS kospi_next_dir, NULL AS usdkrw_next_dir,
                       NULL AS samsung_next_dir, NULL AS nasdaq_next_dir
                FROM weekly_records
                WHERE verified_at IS NOT NULL AND kospi_actual_change IS NOT NULL
            '''
            # daily_records 테이블이 존재하면 포함
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            if 'daily_records' in tables:
                _rt_sql += '''
                UNION ALL
                SELECT day AS week,
                       (politics_pos - politics_neg + global_pos - global_neg +
                        tech_pos - tech_neg + realestate_pos - realestate_neg) * 1.0 /
                       NULLIF(total_articles, 0) AS sentiment_score,
                       (politics_pos - politics_neg) * 1.0 / NULLIF(total_articles, 0) AS politics_ratio,
                       (global_pos - global_neg) * 1.0 / NULLIF(total_articles, 0) AS global_ratio,
                       (tech_pos - tech_neg) * 1.0 / NULLIF(total_articles, 0) AS tech_ratio,
                       (realestate_pos - realestate_neg) * 1.0 / NULLIF(total_articles, 0) AS realestate_ratio,
                       politics_pos * 1.0 / NULLIF(total_articles, 0) AS politics_pos_ratio,
                       global_pos * 1.0 / NULLIF(total_articles, 0) AS global_pos_ratio,
                       tech_pos * 1.0 / NULLIF(total_articles, 0) AS tech_pos_ratio,
                       kospi_actual_change, usdkrw_actual_change,
                       samsung_actual_change, nasdaq_actual_change,
                       NULL AS kospi_next_dir, NULL AS usdkrw_next_dir,
                       NULL AS samsung_next_dir, NULL AS nasdaq_next_dir
                FROM daily_records
                WHERE verified_at IS NOT NULL AND kospi_actual_change IS NOT NULL
                '''
            _rt_sql += ' ORDER BY week'
            rt = pd.DataFrame([dict(r) for r in conn.execute(_rt_sql).fetchall()])

        frames = [f for f in [bf, rt] if not f.empty]
        if not frames:
            return pd.DataFrame()

        df = pd.concat(frames, ignore_index=True)
        df = df.drop_duplicates('week').sort_values('week').reset_index(drop=True)
        logger.info(f'데이터 로드: {len(df)}주 (백필 {len(bf) if not bf.empty else 0}개 + 실시간 {len(rt) if not rt.empty else 0}개)')
        return df

    # ------------------------------------------------------------------ #
    # 2. 피처 엔지니어링                                                    #
    # ------------------------------------------------------------------ #
    def _build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """학습용 피처 생성"""
        df = df.copy()
        df['week_dt'] = pd.to_datetime(df['week'])
        df['month'] = df['week_dt'].dt.month
        df['quarter'] = df['week_dt'].dt.quarter

        # 피처: 이번 주 등락률 + lag 2주
        price_cols = ['kospi_actual_change', 'usdkrw_actual_change',
                      'samsung_actual_change', 'nasdaq_actual_change']
        for col in price_cols:
            df[f'{col}_lag1'] = df[col].shift(1)
            df[f'{col}_lag2'] = df[col].shift(2)

        # sentiment 4주 이동평균
        df['sentiment_ma4'] = df['sentiment_score'].rolling(4, min_periods=1).mean()

        # 카테고리별 비율 (weekly_records에만 존재 — backfill은 NaN, XGBoost가 자체 처리)
        cat_ratio_cols = ['politics_ratio', 'global_ratio', 'tech_ratio', 'realestate_ratio',
                          'politics_pos_ratio', 'global_pos_ratio', 'tech_pos_ratio']
        for col in cat_ratio_cols:
            if col not in df.columns:
                df[col] = float('nan')
            # 4주 rolling (NaN 포함 허용)
            df[f'{col}_ma4'] = df[col].rolling(4, min_periods=1).mean()

        return df

    def _get_feature_cols(self) -> list[str]:
        return [
            'sentiment_score', 'sentiment_ma4',
            'kospi_actual_change', 'usdkrw_actual_change',
            'samsung_actual_change', 'nasdaq_actual_change',
            'kospi_actual_change_lag1', 'usdkrw_actual_change_lag1',
            'samsung_actual_change_lag1', 'nasdaq_actual_change_lag1',
            'kospi_actual_change_lag2', 'usdkrw_actual_change_lag2',
            'samsung_actual_change_lag2', 'nasdaq_actual_change_lag2',
            'month', 'quarter',
            # 카테고리별 감성 (실시간 데이터 축적 시 활성화)
            'politics_ratio', 'global_ratio', 'tech_ratio', 'realestate_ratio',
            'politics_pos_ratio', 'global_pos_ratio', 'tech_pos_ratio',
            'politics_ratio_ma4', 'global_ratio_ma4', 'tech_ratio_ma4', 'realestate_ratio_ma4',
        ]

    # ------------------------------------------------------------------ #
    # 3. 학습                                                              #
    # ------------------------------------------------------------------ #
    def train(self) -> dict:
        df_raw = self._load_data()
        if df_raw.empty or len(df_raw) < 30:
            logger.warning(f'데이터 부족 ({len(df_raw)}주) — 학습 생략')
            return {'status': 'skipped', 'reason': f'데이터 {len(df_raw)}주 (최소 30주 필요)'}

        df = self._build_features(df_raw)
        feat_cols = self._get_feature_cols()
        results = {}

        for target in _TARGETS:
            next_col = f'{target}_next_dir'
            if next_col not in df.columns:
                continue

            sub = df[df[next_col].notna()].copy()
            sub['label'] = (sub[next_col] == '상승').astype(int)

            # 핵심 피처만 NaN 체크 (카테고리별 피처는 backfill에 없어도 XGBoost가 처리)
            _CAT_FEATURE_PREFIXES = ('politics_', 'global_ratio', 'tech_ratio', 'realestate_ratio',
                                     'global_pos_ratio', 'tech_pos_ratio')
            core_cols = [c for c in feat_cols if not c.startswith(_CAT_FEATURE_PREFIXES)]
            valid_mask = sub[core_cols].notna().all(axis=1)
            sub = sub[valid_mask]

            if len(sub) < 30:
                logger.warning(f'{target}: 유효 샘플 부족 ({len(sub)}개)')
                continue

            X = sub[feat_cols].values
            y = sub['label'].values

            # 시계열 교차검증 (5-fold)
            tscv = TimeSeriesSplit(n_splits=5)
            cv_scores = []
            for train_idx, val_idx in tscv.split(X):
                X_tr, X_val = X[train_idx], X[val_idx]
                y_tr, y_val = y[train_idx], y[val_idx]
                clf = XGBClassifier(
                    n_estimators=100, max_depth=4, learning_rate=0.05,
                    subsample=0.8, colsample_bytree=0.8,
                    eval_metric='logloss', verbosity=0, nthread=1
                )
                clf.fit(X_tr, y_tr)
                cv_scores.append(accuracy_score(y_val, clf.predict(X_val)))

            cv_mean = float(np.mean(cv_scores))

            # 전체 데이터로 최종 모델 학습
            final_model = XGBClassifier(
                n_estimators=100, max_depth=4, learning_rate=0.05,
                subsample=0.8, colsample_bytree=0.8,
                eval_metric='logloss', verbosity=0, nthread=1
            )
            final_model.fit(X, y)

            # 모델 저장
            model_path = _MODEL_DIR / f'{target}_xgb.pkl'
            joblib.dump({'model': final_model, 'features': feat_cols,
                         'trained_at': datetime.now().isoformat(),
                         'n_samples': len(sub)}, model_path)

            results[target] = {
                'cv_accuracy': round(cv_mean * 100, 1),
                'n_samples': len(sub),
                'model_path': str(model_path),
            }
            logger.info(f'{target}: CV 정확도={cv_mean*100:.1f}% (샘플 {len(sub)}개)')

        # 메타 저장
        meta = {
            'trained_at': datetime.now().isoformat(),
            'total_weeks': len(df_raw),
            'results': results,
        }
        with open(_MODEL_DIR / 'meta.json', 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        logger.info(f'학습 완료: {len(results)}개 모델 저장')
        return {'status': 'trained', **meta}

    # ------------------------------------------------------------------ #
    # 4. 예측 (파이프라인 통합용)                                            #
    # ------------------------------------------------------------------ #
    def _fetch_this_week_changes(self) -> dict:
        """이번 주 실제 등락률 yfinance로 조회"""
        import yfinance as yf
        from datetime import datetime, timedelta

        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())  # 이번 주 월요일
        tickers = {
            'kospi': '^KS11', 'usd_krw': 'KRW=X',
            'samsung': '005930.KS', 'nasdaq': '^IXIC',
        }
        result = {}
        for name, ticker in tickers.items():
            try:
                df = yf.Ticker(ticker).history(
                    start=week_start.strftime('%Y-%m-%d'),
                    end=today.strftime('%Y-%m-%d'),
                )
                if len(df) >= 2:
                    chg = (float(df['Close'].iloc[-1]) - float(df['Close'].iloc[0])) / float(df['Close'].iloc[0]) * 100
                    result[f'{name}_actual_change'] = round(chg, 2)
                else:
                    result[f'{name}_actual_change'] = 0.0
            except Exception:
                result[f'{name}_actual_change'] = 0.0
        return result

    def predict(self, this_week_data: dict) -> dict:
        """
        this_week_data: {
            'sentiment_score': float,
            'kospi_actual_change': float, 'usdkrw_actual_change': float,
            'samsung_actual_change': float, 'nasdaq_actual_change': float,
        }
        """
        meta_path = _MODEL_DIR / 'meta.json'
        if not meta_path.exists():
            logger.error('학습된 모델 없음 — predict() 빈 dict 반환. trainer.train()을 먼저 실행하세요.')
            return {}

        predictions = {}
        for target in _TARGETS:
            model_path = _MODEL_DIR / f'{target}_xgb.pkl'
            if not model_path.exists():
                continue
            try:
                saved = joblib.load(model_path)
                model: XGBClassifier = saved['model']
                feat_cols: list = saved['features']

                row = {col: this_week_data.get(col, 0.0) for col in feat_cols}
                X = np.array([[row.get(col, 0.0) for col in feat_cols]])
                prob = float(model.predict_proba(X)[0][1])  # 상승 확률
                direction = '상승' if prob >= 0.5 else '하락'
                predictions[target] = {
                    'direction': direction,
                    'confidence': round(prob * 100, 1),
                    'source': 'xgboost',
                }
            except Exception as e:
                logger.warning(f'{target} XGBoost 예측 실패: {e}')

        return predictions

    def predict_this_week(self, analyzed: list[dict]) -> dict:
        """파이프라인에서 호출 — 이번 주 데이터로 XGBoost 예측"""
        # 전체 + 카테고리별 sentiment 계산
        sentiment_map = {'positive': 1, 'negative': -1, 'neutral': 0}
        total_w = 0.0
        weighted = 0.0
        total_n = len(analyzed) or 1

        cat_counts: dict[str, dict] = {
            'politics_economy': {'pos': 0, 'neg': 0},
            'global_macro':     {'pos': 0, 'neg': 0},
            'tech_industry':    {'pos': 0, 'neg': 0},
            'real_estate':      {'pos': 0, 'neg': 0},
        }
        for a in analyzed:
            val = sentiment_map.get(a.get('sentiment', 'neutral'), 0)
            imp = float(a.get('importance', 5))
            weighted += val * imp
            total_w += imp
            cat = a.get('category', '')
            if cat in cat_counts:
                if val > 0:
                    cat_counts[cat]['pos'] += 1
                elif val < 0:
                    cat_counts[cat]['neg'] += 1

        sentiment_score = (weighted / total_w) if total_w > 0 else 0.0

        cat_features = {
            'politics_ratio': (cat_counts['politics_economy']['pos'] - cat_counts['politics_economy']['neg']) / total_n,
            'global_ratio':   (cat_counts['global_macro']['pos'] - cat_counts['global_macro']['neg']) / total_n,
            'tech_ratio':     (cat_counts['tech_industry']['pos'] - cat_counts['tech_industry']['neg']) / total_n,
            'realestate_ratio': (cat_counts['real_estate']['pos'] - cat_counts['real_estate']['neg']) / total_n,
            'politics_pos_ratio': cat_counts['politics_economy']['pos'] / total_n,
            'global_pos_ratio':   cat_counts['global_macro']['pos'] / total_n,
            'tech_pos_ratio':     cat_counts['tech_industry']['pos'] / total_n,
        }

        price_changes = self._fetch_this_week_changes()
        this_week = {'sentiment_score': sentiment_score, **cat_features, **price_changes}
        result = self.predict(this_week)

        if result:
            logger.info(f'XGBoost 예측 완료: ' +
                        ', '.join(f'{k}={v["direction"]}({v["confidence"]}%)' for k, v in result.items()))
        return result


if __name__ == '__main__':
    trainer = WeeklyTrainer()
    result = trainer.train()
    print(json.dumps(result, ensure_ascii=False, indent=2))
