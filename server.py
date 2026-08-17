import os
import json
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Tuple

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

from seoul_api import fetch_facilities, get_facility_by_mng_no

load_dotenv()

API_KEY = os.environ.get("SEOUL_AIR_EMISSION_API_KEY")
if not API_KEY:
    raise ValueError("SEOUL_AIR_EMISSION_API_KEY not set in environment")

COORD_NOTE = "본 데이터는 3일 지연 데이터입니다. 좌표는 위경도가 아닌 중부원점TM(EPSG:5174) 좌표입니다."


class RateLimiter:
    def __init__(self):
        self.requests_per_minute = defaultdict(list)  # IP -> [timestamp, ...]
        self.hour_violations = defaultdict(list)       # IP -> [timestamp, ...]
        self.blocked_ips = {}                           # IP -> unblock_time
        self.daily_requests = defaultdict(list)         # IP -> [timestamp, ...]

    def get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get('X-Forwarded-For', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
        if request.client:
            return request.client.host
        return 'unknown'

    def check_rate_limit(self, ip: str) -> Tuple[bool, str]:
        now = datetime.now(timezone.utc)

        # 3단계: 24시간 차단 확인
        if ip in self.blocked_ips:
            unblock_time = self.blocked_ips[ip]
            if now < unblock_time:
                return False, "IP is blocked for 24 hours"
            else:
                del self.blocked_ips[ip]

        # 1단계: 분당 제한 (3회/60초)
        minute_ago = now - timedelta(seconds=60)
        self.requests_per_minute[ip] = [
            ts for ts in self.requests_per_minute[ip] if ts > minute_ago
        ]

        if len(self.requests_per_minute[ip]) >= 3:
            self.hour_violations[ip].append(now)
            hour_ago = now - timedelta(hours=1)
            self.hour_violations[ip] = [
                ts for ts in self.hour_violations[ip] if ts > hour_ago
            ]
            # 2단계: 1시간 내 위반 5회 초과 시 24시간 차단
            if len(self.hour_violations[ip]) >= 5:
                self.blocked_ips[ip] = now + timedelta(hours=24)
                return False, "Rate limit exceeded (repeated violations)"

            return False, "Rate limit exceeded (3 requests/minute)"

        # 3단계: 일일 총량 (30회/24시간, rolling)
        day_ago = now - timedelta(hours=24)
        self.daily_requests[ip] = [
            ts for ts in self.daily_requests[ip] if ts > day_ago
        ]
        if len(self.daily_requests[ip]) >= 30:
            return False, "Daily request limit exceeded (30 requests/24h)"

        self.requests_per_minute[ip].append(now)
        self.daily_requests[ip].append(now)

        return True, ""


rate_limiter = RateLimiter()
mcp = FastMCP("air-emission-facility-mcp")


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = rate_limiter.get_client_ip(request)
        allowed, reason = rate_limiter.check_rate_limit(ip)
        if not allowed:
            return JSONResponse({"error": "RATE_LIMIT_EXCEEDED", "message": reason}, status_code=429)
        return await call_next(request)


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@mcp.tool()
async def search_emission_facilities(
    start_index: int,
    end_index: int,
    include_fields: str = None
) -> str:
    """
    대기오염물질 배출시설 조회 (INDEX 기반 페이징)

    Args:
        start_index: 조회 시작 위치 (1 이상, 정수)
        end_index: 조회 종료 위치 (start_index 이상, 최대 1000건 차이)
        include_fields: (선택) 반환 필드명 쉼표 구분
                       예: 'BPLC_NM,ROAD_NM_ADDR,SALS_STTS_NM'

    Returns:
        조회된 시설 정보 JSON
        - count: 조회된 건수
        - total_count: 전체 이용가능 건수
        - result: 시설 정보 배열
        - note: 좌표계 및 데이터 신선도 안내
    """
    if start_index < 1:
        return json.dumps({"error": "CLIENT_ERROR_INVALID_START_INDEX", "message": "start_index must be >= 1"}, ensure_ascii=False)

    if end_index < start_index:
        return json.dumps({"error": "CLIENT_ERROR_INVALID_INDEX_ORDER", "message": "end_index must be >= start_index"}, ensure_ascii=False)

    if end_index - start_index > 1000:
        return json.dumps({"error": "CLIENT_ERROR_INDEX_EXCEEDS_1000", "message": "Maximum 1000 items per request"}, ensure_ascii=False)

    result = await fetch_facilities(start_index, end_index, API_KEY)

    if not result['success']:
        return json.dumps({
            "error": result.get("error_code", "UNKNOWN"),
            "message": result.get("error_message", "Unknown error")
        }, ensure_ascii=False)

    facilities = result['facilities']
    if include_fields:
        fields = [f.strip() for f in include_fields.split(',')]
        facilities = [{k: v for k, v in fac.items() if k in fields} for fac in facilities]

    response = {
        'count': result['count'],
        'total_count': result.get('total_count'),
        'result': facilities,
        'note': COORD_NOTE,
    }

    return json.dumps(response, ensure_ascii=False, indent=2)


@mcp.tool()
async def get_facility_info(management_number: str) -> str:
    """
    관리번호로 배출시설 상세 정보 조회

    Args:
        management_number: 시설 고유 관리번호 (MNG_NO)
                          예: '317000021202000005'

    Returns:
        {
            "found": bool,
            "facility": { ... 전체 필드 ... }
        }
    """
    result = await get_facility_by_mng_no(management_number, API_KEY)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def list_facility_statuses() -> str:
    """
    배출시설 영업상태별 현황 조회 (표본 기반 추정치)

    확인 필요: SALS_STTS_CD/NM 매핑이 DEVPLAN 명세(01=폐업,02=휴업,03=영업,04=소재불명)와
    실측 결과(01=영업, 04=폐쇄 확인됨)가 다름. 정확한 전체 코드 매핑은 미확인 상태이며,
    본 도구는 SALS_STTS_NM 문자열 값 자체를 그대로 집계한다.

    Returns:
        {
            "query_timestamp": ISO8601,
            "statuses": { "<SALS_STTS_NM 값>": 건수, ... },
            "total": 표본 건수
        }
    """
    status_counts = defaultdict(int)
    total_count = None

    try:
        result = await fetch_facilities(1, 100, API_KEY)
        if result['success']:
            total_count = result.get('total_count')
            for facility in result['facilities']:
                status = facility.get('SALS_STTS_NM', '미분류').strip()
                status_counts[status] += 1
    except Exception:
        pass

    response = {
        'query_timestamp': datetime.now(timezone.utc).isoformat(),
        'data_recency': '3일 지연',
        'statuses': dict(status_counts),
        'sample_size': sum(status_counts.values()),
        'total_available': total_count,
        'note': '상태별 집계는 표본(최대 100건) 기반 추정치입니다. 정확한 수치는 search_emission_facilities로 확인하세요.'
    }

    return json.dumps(response, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        stateless_http=True,  # 절대 생략 금지
        middleware=[Middleware(RateLimitMiddleware)],
    )
