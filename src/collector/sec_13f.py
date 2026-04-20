"""
SEC EDGAR 13F-HR 헤지펀드 포지션 수집기
분기별 대형 기관투자자 보유 종목 변화 추적
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path
import httpx
from logger import get_logger

logger = get_logger('collector.sec_13f')

_BASE = 'https://data.sec.gov'
_ARCHIVES = 'https://www.sec.gov/Archives/edgar/data'
_HEADERS = {'User-Agent': 'Policonomy contact@policonomy.com', 'Accept-Encoding': 'gzip, deflate'}

# 추적 헤지펀드 목록
HEDGE_FUNDS = [
    {'name': 'Berkshire Hathaway',       'short': 'BRK',       'cik': '0001067983'},
    {'name': 'Renaissance Technologies', 'short': 'RenTec',    'cik': '0001037389'},
    {'name': 'Pershing Square',          'short': 'Pershing',  'cik': '0001336528'},
    {'name': 'Tiger Global',             'short': 'Tiger',     'cik': '0001167483'},
    {'name': 'Appaloosa Management',     'short': 'Appaloosa', 'cik': '0001006438'},
]


def _get(url: str, delay: float = 0.15) -> httpx.Response:
    """SEC rate limit (10 req/s) 준수"""
    time.sleep(delay)
    return httpx.get(url, headers=_HEADERS, timeout=20, follow_redirects=True)


def _quarter_label(report_date: str) -> str:
    """reportDate(YYYY-MM-DD) → 'Q4 2025' 형식"""
    dt = datetime.strptime(report_date, '%Y-%m-%d')
    q = {3: 'Q1', 6: 'Q2', 9: 'Q3', 12: 'Q4'}[dt.month]
    return f'{q} {dt.year}'


def _latest_13f(cik: str) -> dict | None:
    """해당 CIK의 최신 13F-HR 메타데이터 반환"""
    url = f'{_BASE}/submissions/CIK{cik}.json'
    try:
        resp = _get(url)
        resp.raise_for_status()
        data = resp.json()
        recent = data.get('filings', {}).get('recent', {})
        for i, form in enumerate(recent.get('form', [])):
            if form == '13F-HR':
                return {
                    'cik_int': int(cik),
                    'accession': recent['accessionNumber'][i],
                    'filing_date': recent['filingDate'][i],
                    'report_date': recent['reportDate'][i],
                }
    except Exception as e:
        logger.warning(f'submissions 조회 실패 ({cik}): {e}')
    return None


def _find_infotable_url(cik_int: int, accession: str) -> str | None:
    """파일링 디렉터리에서 인포테이블 XML URL 탐색"""
    acc_no_dashes = accession.replace('-', '')
    dir_url = f'{_ARCHIVES}/{cik_int}/{acc_no_dashes}/'
    try:
        resp = _get(dir_url)
        resp.raise_for_status()
        # XML 파일 중 primary_doc.xml이 아닌 것 (인포테이블)
        xml_files = re.findall(r'href="([^"]+\.xml)"', resp.text, re.I)
        for f in xml_files:
            fname = f.split('/')[-1].lower()
            if fname != 'primary_doc.xml':
                # 절대경로로 변환
                if f.startswith('/'):
                    return f'https://www.sec.gov{f}'
                return f'{dir_url}{f}'
    except Exception as e:
        logger.warning(f'디렉터리 조회 실패 ({cik_int}): {e}')
    return None


def _parse_infotable(xml_text: str) -> list[dict]:
    """13F 인포테이블 XML → 집계된 보유 종목 목록"""
    # 네임스페이스 제거 후 파싱
    xml_text = re.sub(r'\s+xmlns[^=]*="[^"]*"', '', xml_text)

    holdings: dict[str, dict] = {}

    for block in re.finditer(r'<infoTable>(.*?)</infoTable>', xml_text, re.S):
        b = block.group(1)

        def _val(tag: str) -> str:
            m = re.search(rf'<{tag}>(.*?)</{tag}>', b, re.S)
            return m.group(1).strip() if m else ''

        name = _val('nameOfIssuer')
        cusip = _val('cusip')
        value_str = _val('value')
        shares_str = _val('sshPrnamt')

        if not name or not value_str:
            continue

        try:
            value = int(value_str)  # 13F value 필드는 실제 USD (천달러 아님)
            shares = int(shares_str) if shares_str else 0
        except ValueError:
            continue

        key = cusip or name
        if key in holdings:
            holdings[key]['value'] += value
            holdings[key]['shares'] += shares
        else:
            holdings[key] = {'name': name, 'cusip': cusip, 'value': value, 'shares': shares}

    items = sorted(holdings.values(), key=lambda x: -x['value'])
    total_value = sum(h['value'] for h in items)

    result = []
    for h in items:
        pct = round(h['value'] / total_value * 100, 1) if total_value else 0
        result.append({
            'name': h['name'],
            'cusip': h['cusip'],
            'value_usd': h['value'],
            'shares': h['shares'],
            'pct': pct,
        })
    return result, total_value


def _fmt_value(v: int) -> str:
    """USD → 읽기 쉬운 포맷 ($1.2B, $345M)"""
    if v >= 1_000_000_000:
        return f'${v / 1_000_000_000:.1f}B'
    if v >= 1_000_000:
        return f'${v / 1_000_000:.0f}M'
    return f'${v:,}'


class HedgeFund13FCollector:
    def __init__(self, data_dir: Path | None = None):
        from config import config
        self.data_dir = data_dir or config.paths.data
        self.cache_path = self.data_dir / 'hedge_funds_13f.json'

    def _is_cache_fresh(self) -> bool:
        """캐시가 6시간 이내면 재사용"""
        if not self.cache_path.exists():
            return False
        mtime = datetime.fromtimestamp(self.cache_path.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        return age_hours < 6

    def collect(self, force: bool = False) -> dict:
        if not force and self._is_cache_fresh():
            logger.info('13F 캐시 재사용')
            return json.loads(self.cache_path.read_text(encoding='utf-8'))

        logger.info('SEC 13F 데이터 수집 시작...')
        funds_data = []

        for fund in HEDGE_FUNDS:
            logger.info(f"  {fund['name']} 처리 중...")
            try:
                meta = _latest_13f(fund['cik'])
                if not meta:
                    logger.warning(f"  {fund['name']}: 13F 없음")
                    continue

                xml_url = _find_infotable_url(meta['cik_int'], meta['accession'])
                if not xml_url:
                    logger.warning(f"  {fund['name']}: 인포테이블 URL 탐색 실패")
                    continue

                resp = _get(xml_url)
                resp.raise_for_status()

                holdings, total_value = _parse_infotable(resp.text)

                funds_data.append({
                    'name': fund['name'],
                    'short': fund['short'],
                    'cik': fund['cik'],
                    'quarter': _quarter_label(meta['report_date']),
                    'report_date': meta['report_date'],
                    'filed_at': meta['filing_date'],
                    'total_value': total_value,
                    'total_value_fmt': _fmt_value(total_value),
                    'holdings_count': len(holdings),
                    'top_holdings': holdings[:10],
                })
                logger.info(f"  {fund['name']}: {len(holdings)}개 종목, 총 {_fmt_value(total_value)}")
            except Exception as e:
                logger.warning(f"  {fund['name']} 실패: {e}")

        result = {
            'updated_at': datetime.now().isoformat(),
            'funds': funds_data,
        }

        self.cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        logger.info(f'13F 수집 완료: {len(funds_data)}개 펀드')
        return result
