"""
07:00 KST 검증 전용 스크립트
- 한국장 마감: 15:30 KST (전날)
- 미국장 마감: 05:00 KST (당일)
→ 07:00 실행 시 양쪽 종가 모두 확정 상태

crontab: 0 7 * * * conda run -n Policonomy python ~/policonomy/src/pipeline_verify.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from logger import get_logger
from predictor.daily_record import DailyRecorder

logger = get_logger('verify')


def main():
    recorder = DailyRecorder()
    result = recorder.verify_yesterday()
    if result:
        hits = result.get('direction_hits', 0) or 0
        total = result.get('direction_total', 0) or 0
        day = result.get('day', '?')
        acc = round(hits / total * 100, 1) if total else 0
        logger.info(f'검증 완료: {day} — {hits}/{total} 적중 ({acc}%)')
    else:
        logger.info('검증할 레코드 없음 (이미 검증됐거나 데이터 부족)')


if __name__ == '__main__':
    main()
