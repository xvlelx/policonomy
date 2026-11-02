"""
AWS SES 이메일 발송 모듈
구독자 관리 (SQLite) + SES 발송
"""
import hashlib
import hmac
import html as html_lib
import os
import secrets
from urllib.parse import quote
import sqlite3
from datetime import datetime, timedelta, timezone

import boto3
from botocore.exceptions import ClientError

from config import config
from logger import get_logger

logger = get_logger('publisher.email')

_SCHEMA = """
CREATE TABLE IF NOT EXISTS subscribers (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    email            TEXT UNIQUE NOT NULL,
    name             TEXT DEFAULT '',
    active           INTEGER DEFAULT 0,
    confirmed        INTEGER DEFAULT 0,
    confirm_token    TEXT,
    token_created_at TEXT,
    subscribed_at    TEXT,
    unsubscribed_at  TEXT
);
"""



UNSUBSCRIBE_PLACEHOLDER = '__UNSUBSCRIBE_URL__'


def _unsubscribe_secret() -> bytes:
    secret = os.getenv('UNSUBSCRIBE_SECRET') or os.getenv('POLICONOMY_ADMIN_KEY', '')
    if not secret:
        raise RuntimeError('UNSUBSCRIBE_SECRET(또는 POLICONOMY_ADMIN_KEY) 미설정 — 수신거부 링크 서명 불가')
    return secret.encode()


def unsubscribe_token(email: str) -> str:
    """이메일별 수신거부 서명 토큰 (HMAC-SHA256)"""
    return hmac.new(_unsubscribe_secret(), email.strip().lower().encode(), hashlib.sha256).hexdigest()


def verify_unsubscribe_token(email: str, token: str) -> bool:
    try:
        return hmac.compare_digest(unsubscribe_token(email), token or '')
    except RuntimeError:
        return False


def unsubscribe_url(email: str) -> str:
    site_url = os.getenv('SITE_URL', 'http://localhost:3000').rstrip('/')
    return f'{site_url}/unsubscribe?email={quote(email)}&token={unsubscribe_token(email)}'


class EmailSender:
    def __init__(self):
        self.db_path = config.paths.data / 'policonomy.db'
        self.from_email = os.getenv('SES_FROM_EMAIL', '')
        self.region = os.getenv('AWS_REGION', 'ap-northeast-2')
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript(_SCHEMA)
            # migration: add columns if upgrading from old schema
            existing = {r[1] for r in conn.execute('PRAGMA table_info(subscribers)').fetchall()}
            if 'confirmed' not in existing:
                conn.execute('ALTER TABLE subscribers ADD COLUMN confirmed INTEGER DEFAULT 0')
            if 'confirm_token' not in existing:
                conn.execute('ALTER TABLE subscribers ADD COLUMN confirm_token TEXT')
            if 'token_created_at' not in existing:
                conn.execute('ALTER TABLE subscribers ADD COLUMN token_created_at TEXT')

    # ------------------------------------------------------------------ #
    # 구독 관리                                                             #
    # ------------------------------------------------------------------ #
    def subscribe(self, email: str, name: str = '') -> str | None:
        """이메일 등록 후 confirm_token 반환. 실패 시 None."""
        """이미 확인된 활성 구독자면 빈 문자열('') 반환."""
        token = secrets.token_urlsafe(32)
        try:
            with self._conn() as conn:
                existing = conn.execute(
                    'SELECT active, confirmed FROM subscribers WHERE email=?', (email,)
                ).fetchone()
                if existing and existing['active'] == 1 and existing['confirmed'] == 1:
                    return ''
                now = datetime.now().isoformat()
                # 재구독(이전에 해지한 사람)도 다시 확인 절차를 밟도록 active/confirmed 초기화
                conn.execute("""
                    INSERT INTO subscribers (email, name, active, confirmed, confirm_token, token_created_at, subscribed_at)
                    VALUES (?, ?, 0, 0, ?, ?, ?)
                    ON CONFLICT(email) DO UPDATE SET
                        name = excluded.name,
                        active = 0,
                        confirmed = 0,
                        confirm_token = excluded.confirm_token,
                        token_created_at = excluded.token_created_at,
                        subscribed_at = excluded.subscribed_at,
                        unsubscribed_at = NULL
                """, (email, name, token, now, now))
            logger.info(f'구독 신청 (미확인): {email}')
            return token
        except Exception as e:
            logger.error(f'구독 등록 실패 ({email}): {e}')
            return None

    def confirm(self, token: str) -> bool:
        """토큰으로 이메일 확인 → active=1, confirmed=1 (24시간 TTL)"""
        _TTL = timedelta(hours=24)
        try:
            with self._conn() as conn:
                row = conn.execute(
                    'SELECT token_created_at FROM subscribers WHERE confirm_token=? AND confirmed=0',
                    (token,)
                ).fetchone()
                if not row:
                    return False
                if row['token_created_at']:
                    created = datetime.fromisoformat(row['token_created_at'])
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) - created > _TTL:
                        conn.execute('UPDATE subscribers SET confirm_token=NULL WHERE confirm_token=?', (token,))
                        logger.warning(f'확인 토큰 만료 (token={token[:8]}...)')
                        return False
                result = conn.execute(
                    'UPDATE subscribers SET active=1, confirmed=1, confirm_token=NULL WHERE confirm_token=? AND confirmed=0',
                    (token,)
                )
                if result.rowcount == 0:
                    return False
            logger.info(f'구독 확인 완료 (token={token[:8]}...)')
            return True
        except Exception as e:
            logger.error(f'구독 확인 실패: {e}')
            return False

    def send_confirmation_email(self, email: str, name: str, token: str) -> bool:
        """이메일 확인 링크 발송 (텍스트 + HTML)"""
        base_url = os.getenv('SITE_URL', 'http://localhost:3000')
        confirm_url = f'{base_url}/confirm?token={token}'
        subject = '[Policonomy] 이메일 구독 확인'
        greeting = f', {name}' if name else ''
        text_body = f"""안녕하세요{greeting}!

Policonomy 구독 신청을 확인해주세요.

아래 링크를 클릭하시면 구독이 완료됩니다:
{confirm_url}

링크는 24시간 동안 유효합니다.

감사합니다.
— Policonomy 팀
"""
        html_body = f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" style="max-width:480px;background:#1e293b;border-radius:12px;padding:40px;color:#e2e8f0;">
        <tr><td>
          <h1 style="margin:0 0 8px;font-size:22px;color:#60a5fa;">Poli<span style="color:#e2e8f0;">conomy</span></h1>
          <p style="margin:0 0 24px;font-size:13px;color:#94a3b8;">AI 정치·경제 분석 & 예측</p>
          <p style="margin:0 0 16px;font-size:15px;">안녕하세요{greeting}!</p>
          <p style="margin:0 0 28px;font-size:14px;color:#94a3b8;line-height:1.6;">
            Policonomy 구독 신청을 해주셨습니다.<br>아래 버튼을 눌러 이메일을 확인하면 구독이 완료됩니다.
          </p>
          <a href="{confirm_url}" style="display:inline-block;background:#3b82f6;color:#fff;text-decoration:none;padding:14px 32px;border-radius:8px;font-size:15px;font-weight:600;">
            구독 확인하기
          </a>
          <p style="margin:28px 0 0;font-size:12px;color:#64748b;">링크는 24시간 동안 유효합니다.<br>본인이 신청하지 않으셨다면 이 메일을 무시해주세요.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
        return self._send_html(email, subject, text_body, html_body)

    def unsubscribe(self, email: str) -> bool:
        try:
            with self._conn() as conn:
                conn.execute("""
                    UPDATE subscribers
                    SET active = 0, unsubscribed_at = ?
                    WHERE email = ?
                """, (datetime.now().isoformat(), email))
            logger.info(f'구독 해제: {email}')
            return True
        except Exception as e:
            logger.error(f'구독 해제 실패 ({email}): {e}')
            return False

    def list_subscribers(self) -> list[dict]:
        with self._conn() as conn:
            return [dict(r) for r in conn.execute(
                'SELECT id, email, name, active, subscribed_at FROM subscribers ORDER BY subscribed_at DESC'
            ).fetchall()]

    # ------------------------------------------------------------------ #
    # 발송                                                                 #
    # ------------------------------------------------------------------ #
    def _send_html(self, to_email: str, subject: str, text: str, html: str) -> bool:
        """텍스트 + HTML 멀티파트 이메일 발송"""
        if not self.from_email:
            logger.warning('SES_FROM_EMAIL 미설정 — 발송 스킵')
            return False
        try:
            client = boto3.client('ses', region_name=self.region)
            client.send_email(
                Source=self.from_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Text': {'Data': text, 'Charset': 'UTF-8'},
                        'Html': {'Data': html, 'Charset': 'UTF-8'},
                    },
                },
            )
            return True
        except ClientError as e:
            logger.error(f'이메일 발송 실패 ({to_email}): {e.response["Error"]["Message"]}')
            return False

    def _send_raw(self, to_email: str, subject: str, body: str) -> bool:
        """단순 텍스트 이메일 발송"""
        if not self.from_email:
            logger.warning('SES_FROM_EMAIL 미설정 — 발송 스킵')
            return False
        try:
            client = boto3.client('ses', region_name=self.region)
            client.send_email(
                Source=self.from_email,
                Destination={'ToAddresses': [to_email]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {'Text': {'Data': body, 'Charset': 'UTF-8'}},
                },
            )
            return True
        except ClientError as e:
            logger.error(f'이메일 발송 실패 ({to_email}): {e.response["Error"]["Message"]}')
            return False

    def send_newsletter(self, html: str, subject: str) -> dict:
        """확인된 활성 구독자 전체에게 뉴스레터 발송"""
        with self._conn() as conn:
            subscribers = [dict(r) for r in conn.execute(
                'SELECT email, name FROM subscribers WHERE active = 1 AND confirmed = 1'
            ).fetchall()]

        if not subscribers:
            logger.info('활성 구독자 없음 — 발송 스킵')
            return {'sent': 0, 'failed': 0, 'skipped': True}

        if not self.from_email:
            logger.warning('SES_FROM_EMAIL 미설정 — 발송 스킵')
            return {'sent': 0, 'failed': 0, 'error': 'SES_FROM_EMAIL not set'}

        client = boto3.client('ses', region_name=self.region)
        sent = failed = 0
        for sub in subscribers:
            try:
                # 구독자별 서명된 수신거부 링크
                personalized_html = html.replace(
                    UNSUBSCRIBE_PLACEHOLDER, html_lib.escape(unsubscribe_url(sub['email']))
                )
                client.send_email(
                    Source=self.from_email,
                    Destination={'ToAddresses': [sub['email']]},
                    Message={
                        'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                        'Body': {'Html': {'Data': personalized_html, 'Charset': 'UTF-8'}},
                    },
                )
                sent += 1
            except ClientError as e:
                logger.error(f'발송 실패 ({sub["email"]}): {e.response["Error"]["Message"]}')
                failed += 1
            except RuntimeError as e:
                logger.error(f'발송 중단: {e}')
                return {'sent': sent, 'failed': failed + len(subscribers) - sent, 'error': str(e)}

        logger.info(f'뉴스레터 발송 완료: {sent}명 성공, {failed}명 실패')
        return {'sent': sent, 'failed': failed}

    def send_alert(self, subject: str, body: str) -> bool:
        """운영자 본인에게 알림 이메일 발송 (파이프라인 실패 등)"""
        if not self.from_email:
            logger.warning('SES_FROM_EMAIL 미설정 — 알림 발송 스킵')
            return False

        alert_to = os.getenv('ALERT_EMAIL', self.from_email)
        html = f"""
        <html><body style="font-family:monospace;background:#1a1a1a;color:#e0e0e0;padding:24px;">
        <h2 style="color:#f87171;">⚠️ {html_lib.escape(subject)}</h2>
        <pre style="background:#2a2a2a;padding:16px;border-radius:8px;white-space:pre-wrap;">{html_lib.escape(body)}</pre>
        <p style="color:#6b7280;font-size:12px;">Policonomy Pipeline · {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </body></html>
        """
        try:
            client = boto3.client('ses', region_name=self.region)
            client.send_email(
                Source=self.from_email,
                Destination={'ToAddresses': [alert_to]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {'Html': {'Data': html, 'Charset': 'UTF-8'}},
                },
            )
            logger.info(f'알림 발송 완료: {alert_to}')
            return True
        except Exception as e:
            logger.error(f'알림 발송 실패: {e}')
            return False
