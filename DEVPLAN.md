# 개발 계획 — 서울시 대기오염물질배출시설설치사업장 인허가 정보 MCP

## 프로젝트 개요

| 항목 | 값 |
|---|---|
| **저장소명** | `air-emission-facility-mcp` |
| **데이터 제공처** | 서울특별시 기후환경본부 대기정책과 |
| **API 플랫폼** | 서울 열린데이터광장 (openapi.seoul.go.kr) |
| **서비스명** | LOCALDATA_093008 |
| **서비스명(한글)** | 서울시 대기오염물질배출시설설치사업장 인허가 정보 |
| **라이선스** | 공공누리 1유형 |
| **적재 주기** | 매일 |
| **좌표 체계** | 중부원점TM (EPSG:5174) — 위경도 미제공 |
| **데이터 신선도** | 3일 지연 |

---

## 1. API 명세 분석

### 1-1. 요청 구조

**Base URL:**
```
http://openapi.seoul.go.kr:8088/{TYPE}/{SERVICE}/{START_INDEX}/{END_INDEX}
```

**필수 파라미터:**

| 파라미터명 | 타입 | 설명 | 주의사항 |
|---|---|---|---|
| `KEY` | STRING | 열린데이터광장 인증키 | URL 쿼리: `?key=<인증키>` |
| `TYPE` | STRING | 응답 파일 타입 | `xml`, `json` 지원 (기본값 xml) |
| `SERVICE` | STRING | 서비스명 | `LOCALDATA_093008` (고정) |
| `START_INDEX` | INTEGER | 요청 시작 위치 | 1 이상 정수 (1부터 시작) |
| `END_INDEX` | INTEGER | 요청 종료 위치 | START_INDEX 이상, 최대 1000건 차이 |

**요청 예시:**
```
GET http://openapi.seoul.go.kr:8088/xml/LOCALDATA_093008/1/10?key=<인증키>
GET http://openapi.seoul.go.kr:8088/json/LOCALDATA_093008/1/10?key=<인증키>
```

### 1-2. 응답 필드 (34개)

| 순번 | 필드명 | 한글명 | 타입 | 설명 |
|---|---|---|---|---|
| 1 | `OGDP_INST_CD` | 개방자치단체코드 | STRING | 서울특별시 코드 |
| 2 | `MNG_NO` | 관리번호 | STRING | 시설 고유 식별번호 |
| 3 | `LCPMT_YMD` | 인허가일자 | STRING | YYYYMMDD 형식 |
| 4 | `SALS_STTS_CD` | 영업상태코드 | STRING | 01: 폐업, 02: 휴업, 03: 영업, 04: 소재불명 |
| 5 | `SALS_STTS_NM` | 영업상태명 | STRING | 영업상태 한글명 |
| 6 | `DTL_SALS_STTS_CD` | 상세영업상태코드 | STRING | 상세 상태 코드 |
| 7 | `DTL_SALS_STTS_NM` | 상세영업상태명 | STRING | 상세 상태 한글명 |
| 8 | `CLSBIZ_YMD` | 폐업일자 | STRING | YYYYMMDD 형식 (해당 시 만 있음) |
| 9 | `TCBIZ_BGNG_YMD` | 휴업시작일자 | STRING | YYYYMMDD 형식 |
| 10 | `TCBIZ_END_YMD` | 휴업종료일자 | STRING | YYYYMMDD 형식 |
| 11 | `ROBIZ_YMD` | 재개업일자 | STRING | YYYYMMDD 형식 |
| 12 | `TELNO` | 전화번호 | STRING | 사업장 전화번호 |
| 13 | `LCTN_ZIP` | 소재지우편번호 | STRING | 우편번호 |
| 14 | `LOTNO_ADDR` | 지번주소 | STRING | 지번 기반 주소 |
| 15 | `ROAD_NM_ADDR` | 도로명주소 | STRING | 도로명 기반 주소 |
| 16 | `ROAD_NM_ZIP` | 도로명우편번호 | STRING | 도로명 우편번호 |
| 17 | `BPLC_NM` | 사업장명 | STRING | 시설 또는 업체명 |
| 18 | `LAST_MDFCN_YMD` | 최종수정일자 | STRING | YYYYMMDD 형식 |
| 19 | `DATA_UPDT_SE` | 데이터갱신구분 | STRING | 신규/변경/삭제 등 |
| 20 | `DATA_UPDT_YMD` | 데이터갱신일자 | STRING | YYYYMMDD 형식 |
| 21 | `BZSTAT_SE_NM` | 업태구분명 | STRING | 사업 업태 |
| 22 | `XCRD` | 좌표정보(X) | FLOAT | 중부원점TM X좌표 |
| 23 | `YCRD` | 좌표정보(Y) | FLOAT | 중부원점TM Y좌표 |
| 24 | `ENVM_TASK_SE_NM` | 환경업무구분명 | STRING | 환경관련 업무 구분 |
| 25 | `TPBIZ_SE_NM` | 업종구분명 | STRING | 업종 분류 |
| 26 | `CTGRY_NM` | 종별명 | STRING | 배출시설 종별 |
| 27 | `MAIN_PRDT_NM` | 주생산품명 | STRING | 주요 생산품 |
| 28 | `EMS_FCLT_OPER_HRM` | 배출시설조업시간 | INTEGER | 조업시간 (시간 단위) |
| 29 | `EMS_FCLT_ANL_OPRTNG_DCNT` | 배출시설연간가동일수 | INTEGER | 연간 가동 일수 |
| 30 | `PVT_FCLT_OPER_HRM` | 방지시설조업시간 | INTEGER | 방지시설 조업시간 (시간 단위) |
| 31~34 | (추가 필드) | 기타 필드 | - | 명세서 미명시 항목 |

### 1-3. 에러 코드 체계

| 코드 | 설명 | 대응 |
|---|---|---|
| `INFO-000` | 정상 처리 | 성공 |
| `INFO-100` | 인증키 유효하지 않음 | 환경변수 확인 필요 |
| `INFO-200` | 해당 데이터 없음 | 정상 응답 (빈 결과 집합) |
| `ERROR-300` | 필수값 누락 | 파라미터 검증 |
| `ERROR-301` | TYPE 파라미터 오류 | xml/json 확인 |
| `ERROR-310` | SERVICE 값 오류 | LOCALDATA_093008 확인 |
| `ERROR-331` | START_INDEX 오류 | 정수값 확인 |
| `ERROR-332` | END_INDEX 오류 | 정수값 확인 |
| `ERROR-333` | 요청위치 타입 오류 | 정수 입력 |
| `ERROR-334` | START_INDEX > END_INDEX | 순서 확인 |
| `ERROR-335` | 샘플키 초과 (최대 5건) | 테스트 키 범위 제한 |
| `ERROR-336` | 요청 초과 (최대 1000건) | END_INDEX - START_INDEX ≤ 1000 |
| `ERROR-500` | 서버 오류 | 재시도 권고 |
| `ERROR-600` | DB 연결 오류 | 재시도 권고 |
| `ERROR-601` | SQL 오류 | 재시도 권고 |

### 1-4. 페이징 방식

- **방식**: INDEX 기반 (START_INDEX, END_INDEX)
- **1회 최대 요청**: 1000건
- **샘플 키**: 최대 5건

---

## 2. MCP 도구 설계

### 2-1. 도구 개수 및 전략

**총 3개 도구 (단순성 + 유용성 우선)**

각 도구는 서울 열린데이터광장 다른 대기환경 MCP들(서울시 실시간 대기환경 현황 등)과 보완 관계:
- 이 MCP: **배출시설 설치/허가 정보** (정적, 행정 기준)
- 기존 MCP: 실시간 측정치 및 평균 (동적)

### 2-2. 도구 상세 설계

#### **도구 1: `search_emission_facilities`**

대기오염물질 배출시설을 구간 조회합니다. 페이징은 INDEX 기반입니다.

```python
def search_emission_facilities(
    start_index: int,      # 조회 시작 위치 (1 이상)
    end_index: int,        # 조회 종료 위치 (1000건 이상 차이 금지)
    include_fields: str = None  # (선택) 쉼표 구분 필드명
) -> dict:
    """
    Args:
        start_index: 조회 시작 위치. 1부터 시작. (예: 1)
        end_index: 조회 종료 위치. start_index 이상, 최대 1000건 차이. (예: 100)
        include_fields: 응답에 포함할 필드명 (쉼표 구분). 
                       미지정 시 전체 34개 필드 반환.
                       예: 'BPLC_NM,LCTN_ZIP,ROAD_NM_ADDR,SALS_STTS_NM'
    
    Returns:
        dict: {
            'count': 조회된 건수 (int),
            'total_available': 전체 이용가능 건수 (int, 명세서 미제공 시 None),
            'result': [
                {
                    'MNG_NO': 관리번호,
                    'BPLC_NM': 사업장명,
                    'ROAD_NM_ADDR': 도로명주소,
                    'SALS_STTS_NM': 영업상태명,  # 영업/폐업/휴업/소재불명
                    'XCRD': X좌표 (중부원점TM, float),
                    'YCRD': Y좌표 (중부원점TM, float),
                    ... (선택된 필드들)
                },
                ...
            ],
            'note': '3일 지연 데이터입니다. 좌표는 위경도가 아닌 중부원점TM(EPSG:5174) 형식입니다.'
        }
    """
    pass
```

**사용 예시:**
```
1. 처음 100건 조회:
   start_index=1, end_index=100

2. 사업장명과 주소만 조회:
   start_index=1, end_index=50, 
   include_fields='BPLC_NM,ROAD_NM_ADDR,SALS_STTS_NM'

3. 다음 페이지:
   start_index=101, end_index=200
```

**에러 처리:**
- `start_index < 1`: CLIENT_ERROR_INVALID_START_INDEX
- `end_index < start_index`: CLIENT_ERROR_INVALID_INDEX_ORDER
- `end_index - start_index > 1000`: CLIENT_ERROR_INDEX_EXCEEDS_1000
- API 서버 에러 (ERROR-500 등): API_ERROR_SERVER

#### **도구 2: `get_facility_info`**

관리번호(MNG_NO) 기준으로 상세 정보를 조회합니다.

```python
def get_facility_info(
    management_number: str  # 관리번호 (예: 'MG001234567')
) -> dict:
    """
    Args:
        management_number: 시설 고유 관리번호. search_emission_facilities 
                          결과에서 MNG_NO 필드 값 사용.
                          예: '11110000010000001'
    
    Returns:
        dict: {
            'found': bool,
            'facility': {
                'MNG_NO': 관리번호,
                'BPLC_NM': 사업장명,
                'LCPMT_YMD': 인허가일자 (YYYYMMDD),
                'SALS_STTS_NM': 영업상태명,
                'ROAD_NM_ADDR': 도로명주소,
                'LOTNO_ADDR': 지번주소,
                'TELNO': 전화번호,
                'BZSTAT_SE_NM': 업태구분명,
                'CTGRY_NM': 종별명,
                'ENVM_TASK_SE_NM': 환경업무구분명,
                'XCRD': X좌표,
                'YCRD': Y좌표,
                'EMS_FCLT_OPER_HRM': 배출시설조업시간 (시간),
                'EMS_FCLT_ANL_OPRTNG_DCNT': 배출시설연간가동일수 (일),
                'LAST_MDFCN_YMD': 최종수정일자 (YYYYMMDD),
                ... (전체 34개 필드)
            }
        }
    """
    pass
```

**사용 예:**
```
특정 시설의 모든 정보 조회:
management_number='11110000010000001'
```

**에러 처리:**
- 관리번호 미발견: `found=False` (정상 응답, 에러 아님)
- API 서버 에러: API_ERROR_SERVER

#### **도구 3: `list_facility_statuses`**

영업상태별 집계 정보를 제공합니다 (메타 정보).

```python
def list_facility_statuses() -> dict:
    """
    대기오염물질 배출시설의 영업상태별 현황을 조회합니다.
    
    Returns:
        dict: {
            'query_timestamp': ISO8601 조회 시각,
            'data_recency': '3일 지연',
            'statuses': {
                '영업': 건수,
                '폐업': 건수,
                '휴업': 건수,
                '소재불명': 건수
            },
            'total': 전체 시설 수,
            'note': '상태별 집계 정보입니다. 정확한 수치는 search_emission_facilities로 확인하세요.'
        }
    """
    pass
```

**구현 전략:**
- 상태별로 소수(5-10)개 표본 조회 후 이를 통해 전체 건수 추정
- 또는 서울 시정 담당 부서 (기후환경본부)에 별도 공개된 집계 통계 API 확인 후 링크

---

## 3. 기술 스택

| 항목 | 선택 |
|---|---|
| **프레임워크** | FastMCP (Python) |
| **Python 버전** | 3.11+ |
| **HTTP 클라이언트** | httpx (비동기) |
| **직렬화** | 기본 JSON (응답 타입 json으로 고정) |
| **배포** | fly.io (FastMCP streamable-http) |

---

## 4. 디렉토리 구조

```
air-emission-facility-mcp/
├── .gitignore
├── .env.example
├── requirements.txt
│   └── fastmcp
│       httpx
│       python-dotenv
├── seoul_api.py              # API 호출, 에러 매핑
├── server.py                 # MCP 서버 정의, 도구 3개
├── Dockerfile
├── fly.toml
├── README.md                 # 사용자용 문서
├── DEVPLAN.md                # 이 문서
├── CLAUDE.md                 # Claude Code 실행 지침
└── DEVLOG.md                 # 진행 기록
```

---

## 5. 개발 진행 순서

### 5-1. Claude Code가 할 일

1. **requirements.txt** 작성 (fastmcp, httpx, python-dotenv)
2. **seoul_api.py** 작성
   - 기본 API 호출 함수 (KEY, TYPE, SERVICE, INDEX)
   - JSON 응답 파싱
   - 에러 코드 매핑 및 필드 검증
3. **server.py** 작성
   - 3개 도구 정의 (docstring에 반드시 필드명과 단위 명시)
   - 각 도구가 seoul_api.py 함수 호출
   - **반드시 `stateless_http=True` 포함**
   - (공개 MCP이므로) 3단계 rate limit 미들웨어 포함
4. **.env.example, .gitignore**
5. **로컬 실측 테스트**
   - 각 도구 직접 호출 (실제 키 사용)
   - 응답 필드 확인
   - 에러 시나리오 테스트 (정상/인증오류/범위초과 등)
6. **FastMCP 서버 스모크 테스트** (initialize 요청)
7. **Dockerfile, fly.toml** 작성
8. **README.md, DEVLOG.md** 갱신
9. **git add/commit/push**
10. **정지** → 사용자에게 4번 안내 문구 출력

### 5-2. 실측 필요 항목 (개발 시 반드시 확인)

1. **API 응답의 `list_total_count` 필드 존재 여부**
   - 명세서에 명시 안 됨. 실제 응답에서 확인 필요.
   - 전체 이용가능 건수를 알 수 있는지 여부.

2. **응답 XML vs JSON 구조**
   - JSON 응답이 실제 어떤 필드 구조인지 직접 호출 후 확인.
   - 순번 기반이 아니라 필드명 기반인지 재확인.

3. **상태명 및 코드값 정확성**
   - `SALS_STTS_CD`, `SALS_STTS_NM` 응답값의 정확한 형식 (예: 영업/폐업 한글 여부)

4. **좌표값 형식 및 정확도**
   - `XCRD`, `YCRD` 반환값이 float인지 string인지
   - 소수점 자리수 확인

5. **필드 누락 처리**
   - 폐업일자, 휴업일자 등이 없는 경우 API가 어떻게 반환하는지 (null, 공백, 미포함)

---

## 6. 사용자가 먼저 할 일

### 6-1. 서울 열린데이터광장 인증키 발급

1. https://data.seoul.go.kr/ 접속
2. 회원 가입 (이미 있으면 로그인)
3. **우측 상단 "마이페이지" → "API 인증키"**
4. **"인증키 신청"** 클릭
5. 발급된 32자리 hex 키를 복사해두기

### 6-2. 샘플 URL로 API 테스트 (선택)

명세서 샘플 URL:
```
GET http://openapi.seoul.go.kr:8088/json/LOCALDATA_093008/1/5?key=<발급받은키>
```

---

## 7. 배포 환경 변수

| 변수명 | 설명 | 예시 | 설정 방법 |
|---|---|---|---|
| `SEOUL_AIR_EMISSION_API_KEY` | 열린데이터광장 인증키 | (32자 hex) | `fly secrets set` |

---

## 8. 예상 타임라인

- **코드 구현**: 1-2시간 (도구 3개, 로직 단순)
- **로컬 실측 테스트**: 30분 (API 호출 + 필드 확인)
- **배포 (fly launch/secrets/deploy)**: 10-15분
- **커넥터 연결 및 검증**: 5분
- **총 소요시간**: 약 2-3시간 (순차, 버그 없을 시)

---

## 9. 주의사항

1. **좌표계 명확히**: 중부원점TM (위경도 아님) → 도구 docstring에 명시
2. **3일 지연 데이터**: 응답에 항상 "본 데이터는 3일 지연" 안내
3. **API 키는 코드에 절대 하드코딩 금지** — `os.environ`으로만 읽기
4. **stateless_http=True 필수** — 빼면 fly.io에서 "사용 가능한 도구 없음" 오류
5. **rate limit 미들웨어** 포함 (3단계: 분당/위반 누적/일일)

---

## 부록: 참고 자료

- **서울 열린데이터광장**: https://data.seoul.go.kr/
- **API 샘플**: http://openapi.seoul.go.kr:8088/sample/json/LOCALDATA_093008/1/5/
- **자치구 기관코드 데이터셋**: https://data.seoul.go.kr/dataList/OA-22872/S/1/datasetView.do
- **제공부서 연락처**: 서울특별시 기후환경본부 대기정책과 (02-2133-4290)
