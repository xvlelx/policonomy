"""
파이프라인 백그라운드 실행기 — 중복 실행 방지 락파일 포함
API에서 POST /api/pipeline/run 을 받으면 이 모듈을 subprocess로 실행한다.
"""
import os
import sys
import json
import time
import fcntl
import signal
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
LOCK_FILE = DATA_DIR / '.pipeline.lock'
STATUS_FILE = DATA_DIR / 'pipeline_status.json'


def _write_status(status: str, stage: str | None = None,
                  progress: int | None = None, total: int | None = None):
    payload = {
        'status': status,
        'stage': stage,
        'progress': progress,
        'total': total,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')


def _is_running() -> bool:
    """락파일이 존재하고 프로세스가 살아있으면 True"""
    if not LOCK_FILE.exists():
        return False
    try:
        pid = int(LOCK_FILE.read_text().strip())
        os.kill(pid, 0)  # 프로세스 존재 확인
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        LOCK_FILE.unlink(missing_ok=True)
        return False


def run_pipeline():
    """파이프라인을 포그라운드로 실행 (이 함수 자체가 백그라운드 프로세스로 spawn됨)"""
    DATA_DIR.mkdir(exist_ok=True)

    # 락파일에 PID 기록
    LOCK_FILE.write_text(str(os.getpid()))

    def _cleanup(signum=None, frame=None):
        LOCK_FILE.unlink(missing_ok=True)
        if signum:
            sys.exit(0)

    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)

    try:
        _write_status('running', '파이프라인 시작')
        # src/ 를 경로에 추가하고 pipeline.py 실행
        src_dir = str(BASE_DIR / 'src')
        env = os.environ.copy()
        env['PYTHONPATH'] = src_dir + os.pathsep + env.get('PYTHONPATH', '')

        result = subprocess.run(
            [sys.executable, str(BASE_DIR / 'src' / 'pipeline.py')],
            cwd=str(BASE_DIR),
            env=env,
        )
        if result.returncode == 0:
            _write_status('completed', '완료')
        else:
            _write_status('error', f'종료코드 {result.returncode}')
    except Exception as e:
        _write_status('error', str(e))
    finally:
        _cleanup()


if __name__ == '__main__':
    run_pipeline()
