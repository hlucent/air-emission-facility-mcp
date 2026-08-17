import re
import httpx
from typing import Dict, Any

# 일부 에러(예: ERROR-336, INFO-100)는 TYPE=json 요청에도 XML로 응답됨 (실측 확인)
_XML_ERROR_RE = re.compile(r"<CODE>(.*?)</CODE>.*?<MESSAGE>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</MESSAGE>", re.DOTALL)

SEOUL_API_BASE = "http://openapi.seoul.go.kr:8088"
SERVICE_NAME = "LOCALDATA_093008"

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


async def fetch_facilities(
    start_index: int,
    end_index: int,
    api_key: str
) -> Dict[str, Any]:
    """
    서울시 대기오염물질 배출시설 조회

    URL 형식(실측 확인): {BASE}/{KEY}/json/{SERVICE}/{START}/{END}
    (KEY는 쿼리 파라미터가 아니라 경로의 첫 요소)

    Returns: {
        'success': bool,
        'count': int (조회된 건수),
        'total_count': int (전체 이용가능 건수, list_total_count),
        'facilities': list (시설 정보),
        'error_code': str (에러 시만),
        'error_message': str (에러 시만),
    }
    """
    url = f"{SEOUL_API_BASE}/{api_key}/json/{SERVICE_NAME}/{start_index}/{end_index}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)

        if response.status_code != 200:
            return {
                'success': False,
                'error_code': f'HTTP_{response.status_code}',
                'error_message': f'HTTP Status {response.status_code}'
            }

        try:
            data = response.json()
        except ValueError:
            # 일부 에러는 TYPE=json 요청에도 XML로 반환됨 (실측 확인: ERROR-336, INFO-100 등)
            m = _XML_ERROR_RE.search(response.text)
            if m:
                code, message = m.group(1).strip(), m.group(2).strip()
                return {
                    'success': False,
                    'error_code': code,
                    'error_message': message,
                }
            return {
                'success': False,
                'error_code': 'PARSE_ERROR',
                'error_message': f'응답을 파싱할 수 없습니다: {response.text[:200]}',
            }

        # 정상 응답: {"LOCALDATA_093008": {"list_total_count", "RESULT", "row"}}
        # 에러 응답: {"RESULT": {"CODE", "MESSAGE"}} (최상위)
        service_data = data.get(SERVICE_NAME)

        if service_data is None:
            result = data.get('RESULT', {})
            code = result.get('CODE', 'UNKNOWN')
            message = result.get('MESSAGE', ERROR_MESSAGES.get(code, '알 수 없는 오류'))
            return {
                'success': False,
                'error_code': code,
                'error_message': message,
            }

        result = service_data.get('RESULT', {})
        code = result.get('CODE', '')

        if code not in ('INFO-000',):
            return {
                'success': False,
                'error_code': code,
                'error_message': result.get('MESSAGE', ERROR_MESSAGES.get(code, '알 수 없는 오류')),
            }

        rows = service_data.get('row', [])

        return {
            'success': True,
            'count': len(rows),
            'total_count': service_data.get('list_total_count'),
            'facilities': rows,
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
    관리번호(MNG_NO)로 시설 상세 정보 조회.

    확인 필요: 상세 조회 전용 API는 명세서에 없음.
    기본값(전략): 전체 목록을 페이지 단위(1000건씩)로 순회하며 MNG_NO 일치 항목을 찾는다.
    실측 결과 전체 건수(list_total_count)가 수천 건 수준이라 최대 몇 차례 호출로 충분하다.
    """
    start = 1
    page_size = 1000
    max_pages = 10  # 안전 상한 (최대 1만 건 탐색)

    for _ in range(max_pages):
        end = start + page_size - 1
        result = await fetch_facilities(start, end, api_key)

        if not result['success']:
            return {'found': False, 'error': result}

        for facility in result['facilities']:
            if facility.get('MNG_NO') == mng_no:
                return {'found': True, 'facility': facility}

        total = result.get('total_count')
        if total is not None and end >= total:
            break

        start = end + 1

    return {'found': False}
