# Claude Code 실행 지침 — air-emission-facility-mcp

## 절대 규칙

1. **DEVPLAN.md 하나만 읽고 시작**. 다른 문서 재탐색 금지.
2. **웹 검색 금지**. API 스펙은 DEVPLAN.md에 이미 있음.
3. 불확실하면 추측성 재설계 대신 기본값 1개로 구현 후 DEVLOG.md에 "확인 필요" 기록.
4. 동일 오류 최대 3회까지만 재시도. 3회 실패 시 기록하고 사용자에게 보고.
5. **Claude Code의 역할은 "코드 구현 + 로컬 실측 테스트"까지**. 
   - `fly launch` / `fly secrets set` / `flyctl deploy` 등 fly.io 관련 명령은 **절대 자동 실행 금지**.
   - 배포는 사용자가 PowerShell에서 직접 수행함.
   - 로컬 테스트까지 마친 후 아래 "작업 완료" 섹션 안내 문구 그대로 출력하고 정지.

---

## 기술적 필수 사항

### `.env` 파일 처리 (BOM 문제 방지)

`.env` 파일을 생성하거나 갱신할 때 **반드시 UTF-8 (BOM 없음)**으로 저장한다.

```python
# python-dotenv가 BOM을 읽지 못하는 문제 방지
# .env 값을 생성/갱신할 때:
import os

env_content = f"SEOUL_AIR_EMISSION_API_KEY={api_key}\n"
# ❌ 틀린 방법:
# with open('.env', 'w') as f:
#     f.write(env_content)  # Python 기본값이 BOM을 붙일 수 있음

# ✅ 올바른 방법:
with open('.env', 'w', encoding='utf-8') as f:
    f.write(env_content)
```

### `stateless_http=True` 필수

server.py의 `mcp.run()` 호출에 **반드시 이 옵션을 포함**한다:

```python
mcp.run(
    transport="streamable-http", 
    host="0.0.0.0", 
    port=port, 
    stateless_http=True  # ← 절대 빼지 말 것
)
```

**이유**: fly.io는 기본적으로 머신 2대(HA)를 띄우는데, streamable-http 세션이 프로세스 메모리에만 저장되면 다른 머신이 요청을 받을 때 세션을 모르고 404를 반환한다. 이 옵션 없이 배포하면 Claude.ai 커넥터에서 "사용 가능한 도구 없음" 오류가 발생한다.

### API 키 취급 원칙

- 실제 키 값은 **코드에 하드코딩하지 않음**. `os.environ`으로만 읽기.
- `.env` 파일을 갱신했다는 사용자 보고 후 재테스트하기 전에, 반드시 파일이 실제로 갱신됐는지 확인할 것.
  - 파일 크기(바이트), 값의 앞 몇 글자 등으로 이전과 달라졌는지 비교.
  - 과거: 사용자가 "갱신했다"고 했으나 실제로는 파일이 그대로여서 같은 오류가 여러 번 반복된 사례 있음.

### rate limit 미들웨어 (3단계)

이 MCP는 API 키 없이 공개되므로 **반드시** 아래 3단계 IP 기반 rate limit을 구현한다.

```python
# server.py 상단에 미들웨어 로직 포함

# 1단계: 분당 호출 제한 (슬라이딩 윈도우)
#   - 같은 IP에서 60초 내 3회 초과 → 429 반환

# 2단계: 반복 위반 차단
#   - 1시간 내 429 응답 5회 이상 → 해당 IP 24시간 차단

# 3단계: 일일 총량 제한
#   - IP당 24시간(rolling) 기준 총 30회 초과 → 429 반환

# 구현 원칙:
# - 저장: in-memory dict/map (서버 재시작 시 초기화 허용)
# - IP 추출: X-Forwarded-For 헤더 (fly.io 프록시 환경) 또는 remote_addr
# - 응답: 429 + "Rate limit exceeded" 메시지
# - 다른 머신의 카운터와 완벽히 동기화되지 않아도 무방 (근사값 허용)
```

---

## 작업 순서

### 1. requirements.txt

```
fastmcp
httpx
python-dotenv
```

### 2. seoul_api.py

API 호출, JSON 파싱, 에러 코드 매핑을 담당한다.

```python
import httpx
import json
import os
from typing import Optional, Dict, List, Any

SEOUL_API_BASE = "http://openapi.seoul.go.kr:8088"
SERVICE_NAME = "LOCALDATA_093008"

async def fetch_facilities(
    start_index: int,
    end_index: int,
    api_key: str
) -> Dict[str, Any]:
    """
    서울시 대기오염물질 배출시설 조회
    
    Returns: {
        'success': bool,
        'count': int (조회된 건수),
        'facilities': list (시설 정보),
        'error_code': str (에러 시만),
        'error_message': str (에러 시만),
    }
    """
    # URL 구성
    url = f"{SEOUL_API_BASE}/json/{SERVICE_NAME}/{start_index}/{end_index}"
    params = {"key": api_key}
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            
        if response.status_code != 200:
            return {
                'success': False,
                'error_code': f'HTTP_{response.status_code}',
                'error_message': f'HTTP Status {response.status_code}'
            }
        
        data = response.json()
        
        # 응답 구조 확인 및 에러 코드 매핑
        # DEVPLAN 에러 코드 참고
        
        # (실측 이후 실제 응답 구조에 맞게 파싱)
        
        return {
            'success': True,
            'count': len(data.get('rows', [])),
            'facilities': data.get('rows', []),
        }
        
    except httpx.TimeoutException:
        return {
            'success': False,
            'error_code': 'TIMEOUT',
            'error_message': 'API 요청 시간 초과'
        }
    except Exception as e:
        return {
            'success': False,
            'error_code': 'EXCEPTION',
            'error_message': str(e)
        }


async def get_facility_by_mng_no(
    mng_no: str,
    api_key: str
) -> Dict[str, Any]:
    """
    관리번호로 시설 상세 정보 조회
    
    전략: search_emission_facilities를 1건 조회로 호출
    (또는 별도 상세 조회 API가 있으면 그것 사용)
    """
    # 구현 가능성:
    # 1. 전체 조회 후 관리번호 필터링 (비효율)
    # 2. 상세 조회 별도 API 확인 (명세서에 없음 → 실측 필요)
    # 3. 근사값: 관리번호로 정렬 후 범위 조회 시도
    
    # 일단 기본값: 1건 조회 시뮬레이션
    # 실제로는 search 1~1로 호출하거나, 
    # API가 제공하지 않으면 여러 건 조회 후 필터링
    
    result = await fetch_facilities(1, 1, api_key)
    if result['success']:
        # 결과에서 mng_no와 일치하는 항목 찾기
        for facility in result['facilities']:
            if facility.get('MNG_NO') == mng_no:
                return {'found': True, 'facility': facility}
        return {'found': False}
    else:
        return {'found': False, 'error': result}


# 에러 코드 매핑 (DEVPLAN 참고)
ERROR_MESSAGES = {
    'INFO-000': '정상 처리',
    'INFO-100': '인증키 유효하지 않음',
    'INFO-200': '해당 데이터 없음',
    'ERROR-300': '필수값 누락',
    'ERROR-301': 'TYPE 파라미터 오류',
    'ERROR-310': 'SERVICE 값 오류',
    'ERROR-331': 'START_INDEX 오류',
    'ERROR-332': 'END_INDEX 오류',
    'ERROR-333': '요청위치 타입 오류',
    'ERROR-334': 'START_INDEX > END_INDEX',
    'ERROR-335': '샘플키 최대 5건 초과',
    'ERROR-336': '요청 최대 1000건 초과',
    'ERROR-500': '서버 오류',
    'ERROR-600': 'DB 연결 오류',
    'ERROR-601': 'SQL 오류',
}
```

### 3. server.py

MCP 서버 정의, 3개 도구, rate limit 미들웨어.

```python
import os
import asyncio
from fastmcp import Server
from fastmcp.caching import CachedResource
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple

from seoul_api import fetch_facilities, get_facility_by_mng_no

# rate limit 미들웨어 상태 (in-memory)
class RateLimiter:
    def __init__(self):
        self.requests_per_minute = defaultdict(list)  # IP → [timestamp, ...]
        self.hour_violations = defaultdict(list)      # IP → [timestamp, ...]
        self.blocked_ips = {}                         # IP → unblock_time
        self.daily_requests = defaultdict(int)        # IP → count
        
    def get_client_ip(self, request_headers: dict) -> str:
        # X-Forwarded-For (프록시) 또는 remote_addr
        forwarded = request_headers.get('X-Forwarded-For', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return 'unknown'
    
    def check_rate_limit(self, ip: str) -> Tuple[bool, str]:
        """
        Returns: (is_allowed, reason_if_blocked)
        """
        now = datetime.utcnow()
        
        # 1. 24시간 차단 확인
        if ip in self.blocked_ips:
            unblock_time = self.blocked_ips[ip]
            if now < unblock_time:
                return False, "IP is blocked for 24 hours"
            else:
                del self.blocked_ips[ip]
        
        # 2. 분당 제한 (3회/60초)
        minute_ago = now - timedelta(seconds=60)
        self.requests_per_minute[ip] = [
            ts for ts in self.requests_per_minute[ip] if ts > minute_ago
        ]
        
        if len(self.requests_per_minute[ip]) >= 3:
            # 위반 기록
            self.hour_violations[ip].append(now)
            # 1시간 내 위반 5회 초과 체크
            hour_ago = now - timedelta(hours=1)
            self.hour_violations[ip] = [
                ts for ts in self.hour_violations[ip] if ts > hour_ago
            ]
            if len(self.hour_violations[ip]) >= 5:
                # 24시간 차단 설정
                self.blocked_ips[ip] = now + timedelta(hours=24)
                return False, "Rate limit exceeded (repeated violations)"
            
            return False, "Rate limit exceeded (3 requests/minute)"
        
        self.requests_per_minute[ip].append(now)
        
        # 3. 일일 총량 (30회/24시간)
        day_ago = now - timedelta(hours=24)
        # daily_requests는 단순하게 rolling window 대신 하루 단위로 관리
        # (정확성 vs 단순성 trade-off, 근사값 허용)
        if self.daily_requests[ip] >= 30:
            return False, "Daily request limit exceeded (30 requests/24h)"
        
        self.daily_requests[ip] += 1
        
        return True, ""

rate_limiter = RateLimiter()
server = Server("air-emission-facility-mcp")

API_KEY = os.environ.get("SEOUL_AIR_EMISSION_API_KEY")
if not API_KEY:
    raise ValueError("SEOUL_AIR_EMISSION_API_KEY not set in environment")

# 도구 1: search_emission_facilities
@server.call_tool()
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
        - result: 시설 정보 배열
        - note: "본 데이터는 3일 지연 데이터입니다. 좌표는 위경도가 아닌 중부원점TM(EPSG:5174) 좌표입니다."
    """
    # 입력값 검증
    if start_index < 1:
        return '{"error": "CLIENT_ERROR_INVALID_START_INDEX", "message": "start_index must be >= 1"}'
    
    if end_index < start_index:
        return '{"error": "CLIENT_ERROR_INVALID_INDEX_ORDER", "message": "end_index must be >= start_index"}'
    
    if end_index - start_index > 1000:
        return '{"error": "CLIENT_ERROR_INDEX_EXCEEDS_1000", "message": "Maximum 1000 items per request"}'
    
    # API 호출
    result = await fetch_facilities(start_index, end_index, API_KEY)
    
    if not result['success']:
        return f'{{"error": "{result.get("error_code", "UNKNOWN")}", "message": "{result.get("error_message", "Unknown error")}"}}'
    
    # 필드 필터링 (선택)
    facilities = result['facilities']
    if include_fields:
        fields = [f.strip() for f in include_fields.split(',')]
        filtered_facilities = []
        for fac in facilities:
            filtered = {k: v for k, v in fac.items() if k in fields}
            filtered_facilities.append(filtered)
        facilities = filtered_facilities
    
    response = {
        'count': result['count'],
        'result': facilities,
        'note': '본 데이터는 3일 지연 데이터입니다. 좌표는 위경도가 아닌 중부원점TM(EPSG:5174) 좌표입니다.'
    }
    
    return json.dumps(response, ensure_ascii=False, indent=2)


# 도구 2: get_facility_info
@server.call_tool()
async def get_facility_info(management_number: str) -> str:
    """
    관리번호로 배출시설 상세 정보 조회
    
    Args:
        management_number: 시설 고유 관리번호 
                          (예: '11110000010000001')
    
    Returns:
        {
            "found": bool,
            "facility": { ... 34개 필드 ... }
        }
    """
    result = await get_facility_by_mng_no(management_number, API_KEY)
    
    return json.dumps(result, ensure_ascii=False, indent=2)


# 도구 3: list_facility_statuses
@server.call_tool()
async def list_facility_statuses() -> str:
    """
    배출시설 영업상태별 현황 조회 (메타 정보)
    
    Returns:
        {
            "query_timestamp": ISO8601,
            "statuses": {
                "영업": 건수,
                "폐업": 건수,
                "휴업": 건수,
                "소재불명": 건수
            },
            "total": 전체 건수
        }
    """
    # 구현 전략: 상태별로 소수 표본 조회 후 집계
    # 또는 서울시 공개 통계 API 링크
    
    # 임시 구현: 분류별 표본 조회 (1-5, 6-10, ...)
    status_counts = {
        '영업': 0,
        '폐업': 0,
        '휴업': 0,
        '소재불명': 0
    }
    
    try:
        result = await fetch_facilities(1, 100, API_KEY)
        if result['success']:
            for facility in result['facilities']:
                status = facility.get('SALS_STTS_NM', '미분류')
                if status in status_counts:
                    status_counts[status] += 1
    except:
        pass
    
    response = {
        'query_timestamp': datetime.utcnow().isoformat() + 'Z',
        'data_recency': '3일 지연',
        'statuses': status_counts,
        'total': sum(status_counts.values()),
        'note': '상태별 집계는 표본 기반 추정치입니다. 정확한 수치는 search_emission_facilities로 확인하세요.'
    }
    
    return json.dumps(response, ensure_ascii=False, indent=2)


# MCP 서버 실행
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        stateless_http=True  # ← 절대 생략 금지
    )
```

### 4. .env.example

```
# 서울 열린데이터광장 인증키
# https://data.seoul.go.kr/ 에서 신청
SEOUL_AIR_EMISSION_API_KEY=
```

### 5. .gitignore

```
.env
__pycache__/
*.py[cod]
*.so
.venv/
venv/
.idea/
.vscode/
*.egg-info/
dist/
build/
```

### 6. 로컬 실측 테스트

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. .env 파일에 실제 API 키 입력
echo "SEOUL_AIR_EMISSION_API_KEY=<발급받은키>" > .env

# 3. 각 도구 테스트
python3 << 'EOF'
import asyncio
from seoul_api import fetch_facilities, get_facility_by_mng_no
import os

API_KEY = os.environ.get("SEOUL_AIR_EMISSION_API_KEY")

async def test():
    # 테스트 1: 첫 10건 조회
    print("=== 테스트 1: 첫 10건 조회 ===")
    result = await fetch_facilities(1, 10, API_KEY)
    print(f"성공: {result['success']}")
    print(f"건수: {result.get('count', 0)}")
    if result.get('facilities'):
        print(f"첫 번째 시설: {result['facilities'][0]}")
    print()
    
    # 테스트 2: 응답 필드 확인
    print("=== 테스트 2: 응답 필드명 확인 ===")
    if result.get('facilities'):
        print(f"필드명: {list(result['facilities'][0].keys())}")
    print()
    
    # 테스트 3: 범위 초과 테스트
    print("=== 테스트 3: 범위 초과 (1001건) ===")
    result_error = await fetch_facilities(1, 1001, API_KEY)
    print(f"성공: {result_error['success']}")
    if not result_error['success']:
        print(f"에러 코드: {result_error.get('error_code')}")

asyncio.run(test())
EOF

# 4. FastMCP 서버 스모크 테스트 (localhost:8000)
python3 server.py &
sleep 2
curl -X POST http://localhost:8000/mcp/initialize \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}'
# 정상이면 JSON 응답 확인, 그 후 프로세스 종료
```

### 7. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "server.py"]
```

### 8. fly.toml

```toml
app = "air-emission-facility-mcp"
primary_region = "nrt"

[build]
dockerfile = "Dockerfile"

[env]
PORT = "8000"

[[services]]
internal_port = 8000
protocol = "http"

[services.concurrency]
type = "connections"
hard_limit = 256
soft_limit = 200
```

### 9. README.md, DEVLOG.md 갱신

- README.md: 도구 설명, 환경변수, 좌표계 주의사항 추가
- DEVLOG.md: 실측 결과 기록 (응답 필드, 에러 코드 확인, 제약사항 등)

### 10. git 커밋

```bash
git add -A
git commit -m "Initial commit: air-emission-facility-mcp server"
git push origin main
```

### 11. 정지 및 안내

**여기서 정지합니다.** 아래 사용자 안내 문구를 출력합니다.

---

## 작업 완료 — 다음 단계 (사용자가 PowerShell에서 직접 수행)

```
✅ Claude Code 작업 완료:
   - requirements.txt, server.py, seoul_api.py 구현
   - 로컬 실측 테스트 완료
   - git commit & push 완료

🚀 이제 PowerShell 창(Claude Code 아님)에서 아래를 순서대로 실행하세요:

cd "C:\Users\hwang\Projects\air-emission-facility-mcp"
fly launch --no-deploy
fly secrets set SEOUL_AIR_EMISSION_API_KEY=<발급받은키>
flyctl deploy

배포 완료 후 나온 주소(https://*****.fly.dev) 뒤에 "/mcp"를 붙여서
Claude.ai 설정 > 커넥터에서 연결하세요.

예: https://air-emission-facility-mcp.fly.dev/mcp
```

---

## 트러블슈팅 (Claude Code에서 만난 경우)

| 에러 | 원인 | 조치 |
|---|---|---|
| ImportError: No module named 'fastmcp' | 의존성 미설치 | `pip install -r requirements.txt` 재실행 |
| SEOUL_AIR_EMISSION_API_KEY not set | 환경변수 미설정 | `.env` 파일 생성, 키 입력 후 Python 재시작 |
| API 응답 파싱 실패 | 응답 구조 예상 오류 | API를 직접 호출해서 응답 JSON 구조 확인 (curl 또는 브라우저) |
| stateless_http=True 누락 → fly.io 배포 후 "도구 없음" | 코드 누락 | server.py의 mcp.run() 호출에 `stateless_http=True` 추가 |
| 동일 오류 3회 이상 반복 | 해결 불가 상황 | DEVLOG.md에 기록 후 사용자에게 보고, 정지 |

---

## 추가 참고

- **DEVPLAN.md**: API 스펙, 도구 설계, 실측 필요 항목
- **README.md**: 사용자용 도구 설명서 (배포 후 갱신)
- **DEVLOG.md**: 개발 진행 기록 및 실측 결과
