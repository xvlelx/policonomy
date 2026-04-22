import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FMT = '[%(asctime)s] %(name)s %(levelname)s - %(message)s'

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_FMT, datefmt='%H:%M:%S'))
    logger.addHandler(console)

    # Railway는 stdout만 수집 — 파일 핸들러는 로컬 전용
    if not os.getenv('RAILWAY_ENVIRONMENT'):
        log_dir = Path(__file__).parent.parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        fh = RotatingFileHandler(
            log_dir / 'pipeline.log',
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8',
        )
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(_FMT))
        logger.addHandler(fh)

    return logger