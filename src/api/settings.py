import json
import logging
import os
import secrets
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Header, HTTPException

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


def _is_admin(key: str) -> bool:
    admin_key = os.environ.get('POLICONOMY_ADMIN_KEY', '')
    return bool(admin_key) and secrets.compare_digest(key or '', admin_key)


@router.get('', response_model=UserSettings)
def get_settings(x_admin_key: str = Header(default='')):
    settings = _load_settings()
    if not _is_admin(x_admin_key):
        # 전역 설정이므로 이메일은 관리자에게만 노출
        settings = settings.model_copy(update={'email': ''})
    return settings


@router.put('', response_model=UserSettings)
def update_settings(settings: UserSettings, x_admin_key: str = Header(default='')):
    # 사용자 구분 없는 전역 설정 — Google OAuth 도입 전까지 관리자만 수정 가능
    if not _is_admin(x_admin_key):
        raise HTTPException(status_code=403, detail='설정 저장은 관리자만 가능합니다')
    if not settings.email:
        # 빈 이메일로 기존 값을 지우지 않음 (GET이 비관리자에게 email을 비워서 반환하므로)
        settings = settings.model_copy(update={'email': _load_settings().email})
    _save_settings(settings)
    return settings
