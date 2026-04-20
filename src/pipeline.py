import json
import time
from datetime import datetime
from pathlib import Path
from logger import get_logger
from config import config
from collector.rss import ArticleCollector
from analyzer.llm import ArticleAnalyzer
from predictor.kronos import MarketPredictor
from predictor.fusion import PredictionFusion
from publisher.newsletter import NewsletterPublisher
from analyzer.report_generator import ReportGenerator
from publisher.email import EmailSender
from predictor.tracker import PredictionTracker
from predictor.daily_record import DailyRecorder
from predictor.trainer import WeeklyTrainer

logger = get_logger('pipeline')


class Pipeline:
    def __init__(self):
        self.collector = ArticleCollector()
        self.analyzer = ArticleAnalyzer()
        self.predictor = MarketPredictor()
        self.fusion = PredictionFusion()
        self.publisher = NewsletterPublisher()
        self.email_sender = EmailSender()
        self.tracker = PredictionTracker()
        self.recorder = DailyRecorder()
        self.trainer = WeeklyTrainer()
        self.report_generator = ReportGenerator(config.paths.data)

    def _update_status(self, status: str, stage: str, progress: int = None, total: int = None) -> None:
        data = {
            'status': status,
            'stage': stage,
            'progress': progress,
            'total': total,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        path = config.paths.data / 'pipeline_status.json'
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError as e:
            logger.warning(f'상태 파일 저장 실패: {e}')

    def run(self) -> dict:
        logger.info(f'파이프라인 시작: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        start = time.time()
        self._update_status('running', '시작 중')

        try:
            # 0. 전날 실제 결과 검증
            self.recorder.verify_yesterday()

            # 1. 수집
            logger.info('[1/4] 수집 시작')
            self._update_status('running', '수집 중')
            all_articles = self.collector.collect_all()
            self._save_json('raw_articles.json', {
                cat: [a.to_dict() for a in articles]
                for cat, articles in all_articles.items()
            })

            # 2. 분석
            logger.info('[2/4] 분석 시작')
            self._update_status('running', '분석 중')
            analyzed = self.analyzer.run(all_articles)
            if not analyzed:
                logger.warning('LLM 분석 결과 없음 — 예측·뉴스레터는 빈 분석으로 계속 진행')
            self._save_json('analyzed_articles.json', analyzed)

            # 3. 예측
            logger.info('[3/4] 예측 시작')
            self._update_status('running', '예측 중')

            last_verification = self.tracker.verify_last_prediction()
            accuracy = self.tracker.get_accuracy()
            predictions = self.predictor.run()
            if not predictions:
                raise RuntimeError('Kronos 예측 결과 없음 — 모델/데이터 확인 필요')
            fused = self.fusion.fuse(predictions, analyzed)
            self.tracker.save_prediction(predictions)
            self.recorder.save_day(analyzed, predictions)
            self.recorder.save_weekly_top()

            # XGBoost 재학습 + 예측 (subprocess로 격리 — macOS segfault 방지)
            logger.info('[3.5] XGBoost 재학습 중...')
            xgb_predictions = self._run_xgb_subprocess(analyzed)

            final_prediction = {
                'generated_at': datetime.now().isoformat(),
                'kronos_predictions': predictions,
                'xgb_predictions': xgb_predictions,
                'fused_analysis': fused,
                'last_verification': last_verification,
                'accuracy': accuracy,
            }
            self._save_json('predictions.json', final_prediction)

            # run_type 결정: 오전(~11시) → morning, 오후(12시~) → afternoon
            run_type = 'morning' if datetime.now().hour < 12 else 'afternoon'

            # 4. 글로벌 브리핑 리포트 생성
            logger.info(f'[4/5] 글로벌 브리핑 리포트 생성 시작 (run_type={run_type})')
            self._update_status('running', '브리핑 생성 중')
            try:
                self.report_generator.generate(run_type=run_type)
                logger.info('글로벌 브리핑 리포트 저장 완료')
            except Exception as e:
                logger.warning(f'브리핑 리포트 생성 실패 (파이프라인은 계속): {e}')

            # 5. 뉴스레터 생성 + 이메일 발송
            logger.info('[5/5] 뉴스레터 생성 시작')
            self._update_status('running', '뉴스레터 생성 중')
            try:
                output_path = self.publisher.publish(analyzed, final_prediction)
            except Exception as e:
                logger.error(f'뉴스레터 생성 실패: {e}')
                output_path = None

            # 이메일 발송 (구독자 있을 때만)
            self._update_status('running', '이메일 발송 중')
            try:
                if output_path is None:
                    raise RuntimeError('뉴스레터 파일 없음 — 생성 실패')
                today_str = datetime.now().strftime('%Y년 %m월 %d일')
                label = '모닝 마켓 브리핑' if run_type == 'morning' else '마감 마켓 브리핑'
                subject = f'[Policonomy] {today_str} {label}'
                with open(output_path, encoding='utf-8') as f:
                    html = f.read()
                send_result = self.email_sender.send_newsletter(html, subject)
                if send_result.get('sent', 0) > 0:
                    logger.info(f'이메일 발송: {send_result["sent"]}명')
            except Exception as e:
                logger.warning(f'이메일 발송 실패 (파이프라인은 계속): {e}')

            elapsed = time.time() - start
            result = {
                'status': 'success',
                'articles': len(analyzed),
                'predictions': len(predictions),
                'newsletter': output_path,
                'elapsed_min': round(elapsed / 60, 1)
            }
            self._update_status('completed', '완료')
            logger.info(f'파이프라인 완료! {elapsed/60:.1f}분 소요')
            return result

        except Exception as e:
            logger.error(f'파이프라인 오류: {e}')
            self._update_status('error', f'오류: {str(e)[:100]}')
            try:
                import traceback
                logger.error('Pipeline traceback:\n' + traceback.format_exc())
                self.email_sender.send_alert(
                    subject=f'[Policonomy] 파이프라인 실패 — {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                    body=f'오류 타입: {type(e).__name__}\n발생 시간: {datetime.now().isoformat()}\n\n상세 로그는 서버에서 확인하세요.',
                )
            except Exception:
                pass
            raise

    def _run_xgb_subprocess(self, analyzed: list) -> dict:
        """XGBoost 재학습 + 예측을 별도 프로세스로 실행 (macOS segfault 격리)"""
        import subprocess, sys, tempfile, os
        # analyzed 데이터를 임시 파일로 전달
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json',
                                         delete=False, encoding='utf-8') as f:
            json.dump(analyzed, f, ensure_ascii=False)
            tmp_path = f.name
        try:
            # tmp_path은 sys.argv[1]로 전달 — f-string에 경로를 삽입하지 않음 (injection 방지)
            src_dir = str(Path(__file__).parent)
            script = (
                f"import sys, json; sys.path.insert(0, {src_dir!r}); "
                "analyzed = json.load(open(sys.argv[1], encoding='utf-8')); "
                "from predictor.trainer import WeeklyTrainer; t = WeeklyTrainer(); "
                "train_result = t.train(); "
                "xgb = t.predict_this_week(analyzed); "
                "print(json.dumps(xgb, ensure_ascii=False))"
            )
            result = subprocess.run(
                [sys.executable, '-c', script, tmp_path],
                capture_output=True, text=True, timeout=300,
                env={**os.environ, 'OBJC_DISABLE_INITIALIZE_FORK_SAFETY': 'YES'},
            )
            if result.returncode == 0 and result.stdout.strip():
                # stdout 마지막 줄이 JSON
                last_line = result.stdout.strip().split('\n')[-1]
                xgb_preds = json.loads(last_line)
                logger.info(f'XGBoost 예측 완료: ' +
                            ', '.join(f'{k}={v["direction"]}({v["confidence"]}%)'
                                      for k, v in xgb_preds.items()))
                return xgb_preds
            else:
                logger.warning(f'XGBoost 서브프로세스 실패 (code={result.returncode})')
                if result.stderr:
                    logger.warning(result.stderr[-500:])
                return {}
        except Exception as e:
            logger.warning(f'XGBoost 서브프로세스 오류: {e}')
            return {}
        finally:
            os.unlink(tmp_path)

    def _save_json(self, filename: str, data, critical: bool = False) -> None:
        path = config.paths.data / filename
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f'저장 완료: {filename}')
        except OSError as e:
            if critical:
                logger.error(f'파일 저장 실패 ({filename}): {e}')
                raise
            else:
                logger.warning(f'파일 저장 실패 ({filename}), 계속 진행: {e}')


if __name__ == '__main__':
    pipeline = Pipeline()
    result = pipeline.run()
    print(result)
