import json
import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'


class UserSettings(BaseModel):
    categories: list[str] = Field(
        default=['politics_economy', 'global_macro', 'tech_industry', 'real_estate']
    )
    email: str = Field(default='')
    email_notifications: bool = Field(default=False)


router = APIRouter(prefix='/api/settings', tags=['settings'])


def _get_settings_path():
    return DATA_DIR / 'settings.json'


def _load_settings() -> UserSettings:
    path = _get_settings_path()
    if not path.exists():
        return UserSettings()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return UserSettings(**data)
    except Exception as e:
        logger.warning(f'설정 로드 실패, 기본값 사용: {e}')
        return UserSettings()


def _save_settings(settings: UserSettings):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = _get_settings_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(settings.model_dump(), f, ensure_ascii=False, indent=2)


@router.get('', response_model=UserSettings)
def get_settings():
    return _load_settings()


@router.put('', response_model=UserSettings)
def update_settings(settings: UserSettings):
    _save_settings(settings)
    return settings
