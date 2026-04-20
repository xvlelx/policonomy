"""Groq API 공통 유틸리티"""
import re


def parse_reset_seconds(reset_str: str) -> float:
    """'2m30.5s', '6s', '577ms' 등을 초 단위로 변환"""
    if not reset_str:
        return 1.0
    total = 0.0
    for match in re.finditer(r'([\d.]+)(ms|s|m|h)', reset_str):
        val, unit = float(match.group(1)), match.group(2)
        if unit == 'ms':
            total += val / 1000
        elif unit == 's':
            total += val
        elif unit == 'm':
            total += val * 60
        elif unit == 'h':
            total += val * 3600
    return max(total, 0.1)
