# 개발 로그 — air-emission-facility-mcp

설계 및 개발 과정에서 발견된 사항, 실측 결과, 의사결정 기록을 남깁니다.

---

## 2026-08-17 (설계 단계)

### 항목 1: 명세서 분석 완료

**상태**: ✅ 완료

명세서는 HTML 형식의 XLS 파일로 다음 내용을 포함:
- 메타정보 (제공기관: 서울시 기후환경본부 대기정책과)
- 파라미터 명세: KEY, TYPE, SERVICE, START_INDEX, END_INDEX
- 응답 필드: 34개 필드 상세 정의
- 에러 코드: 15가지 정의
- 샘플 URL: `http://openapi.seoul.go.kr:8088/json/LOCALDATA_093008/1/5?key=...`

**주요 특징**:
- INDEX 기반 페이징 (SQL OFFSET/LIMIT 방식, 날짜 기반 아님)
- 1회 최대 1000건 조회 가능 (샘플 키는 최대 5건)
- 응답: XML/JSON 선택 가능
- 3일 지연 데이터
- 중부원점TM 좌표 (위경도 미제공)

---

### 항목 2: 도구 설계 확정

**상태**: ✅ 확정 (3개 도구)

#### 도구 1: `search_emission_facilities`
- 페이징 조회 (start_index, end_index)
- 필드 선택 반환 (include_fields)
- 필드 단위 명시 (좌표는 ㎍/㎥ 아님, m 단위)

#### 도구 2: `get_facility_info`
- 관리번호(MNG_NO) 기반 상세 조회
- search_emission_facilities 결과에서 MNG_NO 추출 후 사용

#### 도구 3: `list_facility_statuses`
- 상태별 집계 정보 (메타)
- 정확도: 표본 기반 추정치 명시

**의사결정**: 서울 열린데이터광장의 다른 대기환경 MCP들(실시간 측정치)과의 보완성을 고려하여 3개로 최소화.

---

### 항목 3: 기술 스택 확정

**상태**: ✅ 확정

- **프레임워크**: FastMCP (Python)
- **클라이언트**: httpx (비동기)
- **응답**: JSON 고정 (XML은 개별 요청으로도 처리 가능하나, 도구 출력은 JSON으로 통일)
- **배포**: fly.io + FastMCP streamable-http
- **보안**: 3단계 IP rate limit (공개 MCP)

---

### 항목 4: 실측 필요 항목 목록 작성

**상태**: ✅ 문서화 (개발 중 확인 예정)

| # | 항목 | 확인 방법 | 우선순위 |
|---|---|---|---|
| 1 | `list_total_count` 필드 존재 | API 직접 호출 | 높음 |
| 2 | JSON 응답 구조 | curl 또는 requests | 높음 |
| 3 | 상태명 형식 (한글 여부) | 응답 데이터 | 높음 |
| 4 | 좌표값 타입 (float vs string) | 데이터 타입 검증 | 높음 |
| 5 | 필드 누락 처리 (null vs 공백) | 모든 응답 필드 검사 | 중간 |
| 6 | 에러 응답 구조 | 잘못된 파라미터로 테스트 | 중간 |
| 7 | 샘플 키 vs 실제 키 동작 차이 | 키 전환 후 테스트 | 낮음 |

---

## 2026-08-17 (구현 단계)

### 항목 5: 구현 완료

**상태**: ✅ 완료

- [x] requirements.txt 작성
- [x] seoul_api.py 구현
- [x] server.py 구현 (stateless_http=True 확인)
- [x] rate limit 미들웨어 구현 (Starlette BaseHTTPMiddleware, mcp.run(middleware=[...]))
- [x] .env.example, .gitignore 작성

### 항목 6: 로컬 실측 테스트 결과

**상태**: ✅ 완료

#### 중요 발견 1: URL 형식이 DEVPLAN 명세와 다름

DEVPLAN 명세: `{BASE}/{TYPE}/{SERVICE}/{START}/{END}?key=<키>` (key는 쿼리 파라미터)

**실측 결과**: key는 쿼리 파라미터가 아니라 **경로의 첫 요소**로 들어가야 정상 작동함.

```
정상 동작: http://openapi.seoul.go.kr:8088/{KEY}/json/{SERVICE}/{START}/{END}
실패(ERROR-300): http://openapi.seoul.go.kr:8088/json/{SERVICE}/{START}/{END}?key={KEY}
```

서울 열린데이터광장 API의 공통 URL 패턴(key가 항상 첫 경로 세그먼트)을 따름. seoul_api.py에 이 형식으로 구현함.

#### 중요 발견 2: 응답 JSON 구조

```json
{
  "LOCALDATA_093008": {
    "list_total_count": 5571,
    "RESULT": {"CODE": "INFO-000", "MESSAGE": "정상 처리되었습니다"},
    "row": [ {...}, {...} ]
  }
}
```

- `list_total_count` 필드 **존재 확인** (전체 이용가능 건수 제공됨)
- 최상위 키가 서비스명(`LOCALDATA_093008`)으로 감싸져 있음 (명세서에 명시 안 됨)

#### 중요 발견 3: 일부 에러는 TYPE=json 요청에도 XML로 응답됨

`ERROR-336`(1000건 초과), `INFO-100`(인증키 오류) 등 특정 에러 케이스에서 `/json/` 경로로 요청했음에도
아래처럼 **XML 형식**으로 응답이 돌아옴 (httpx `response.json()` 파싱 실패):

```xml
<RESULT><CODE>ERROR-336</CODE><MESSAGE><![CDATA[데이터요청은 한번에 최대 1000건을 넘을 수 없습니다...]]></MESSAGE></RESULT>
```

**대응**: seoul_api.py의 `fetch_facilities`에서 `response.json()` 실패 시 정규식으로 `<CODE>`/`<MESSAGE>`를 추출하는 폴백 로직 추가.

#### 중요 발견 4: SALS_STTS_CD/NM 매핑이 DEVPLAN 명세와 다름

DEVPLAN 명세: `01: 폐업, 02: 휴업, 03: 영업, 04: 소재불명`

**실측 결과**: `01 → "영업"`, `04 → "폐쇄"` 확인됨. 02/03 코드는 표본에서 발견되지 않아 미확인.

**확인 필요**: 전체 코드-이름 매핑표를 신뢰할 수 없으므로, `list_facility_statuses` 도구는 코드가 아닌
`SALS_STTS_NM` 문자열 값을 그대로 집계하도록 구현함 (기본값 방식, CLAUDE.md 규칙 3 적용).

#### 중요 발견 5: 필드 타입 및 누락 처리

- 값이 없는 날짜/우편번호 필드(`CLSBIZ_YMD`, `LCTN_ZIP` 등)는 **공백 문자열**로 채워져 반환됨 (예: `"          "`), null이 아님.
- `XCRD`, `YCRD` 좌표값은 **문자열 타입**이며 뒤에 공백 패딩이 포함됨 (예: `"190145.164891265    "`). float 아님.
- `EMS_FCLT_OPER_HRM`, `EMS_FCLT_ANL_OPRTNG_DCNT` 등 숫자성 필드도 전부 **문자열**로 반환됨.
- `LCPMT_YMD`는 `YYYYMMDD`가 아니라 `YYYY-MM-DD` 형식(하이픈 포함)으로 반환됨.
- 실측된 필드 수는 30개로, 명세서의 34개와 차이 있음 (`PVT_FCLT_ANL_OPRTNG_DCNT` 등 명세서 미기재 필드 존재, 반대로 명세서에 있으나 실측에 없는 필드도 있을 수 있음 — 전수 비교는 안 함).

#### 실행한 테스트 결과 요약

| # | 테스트 | 결과 |
|---|---|---|
| 1 | 첫 5건 조회 | ✅ 성공, count=5, total_count=5571 |
| 2 | 범위 초과 (1002건) | ✅ ERROR-336 정상 매핑 (XML 폴백 확인) |
| 3 | START_INDEX > END_INDEX | ✅ ERROR-334 정상 매핑 |
| 4 | 잘못된 인증키 | ✅ INFO-100 정상 매핑 (XML 폴백 확인) |
| 5 | get_facility_info (존재하는 관리번호) | ✅ found=True |
| 6 | get_facility_info (존재하지 않는 관리번호) | ✅ found=False |

### 항목 7: FastMCP 스모크 테스트

**상태**: ✅ 완료

- `python server.py` (PORT=8124)로 로컬 기동 확인
- `/health` 커스텀 라우트 200 정상 응답 확인
- `/mcp` 경로로 JSON-RPC `initialize` 요청 성공 (serverInfo 반환 확인)
- `tools/list` 요청으로 3개 도구(search_emission_facilities, get_facility_info, list_facility_statuses) 정상 등록 확인
- Rate limit 미들웨어 동작 확인: 분당 3회 초과 시 429 + "RATE_LIMIT_EXCEEDED" 정상 반환

### 항목 8: 배포 설정 작성

**상태**: ✅ 완료

- Dockerfile (python:3.11-slim 기반) 작성
- fly.toml (nrt 리전, PORT=8000) 작성
- README 갱신 (실측 결과 반영: 좌표/날짜 필드 타입, 상태값 실제 표기, list_facility_statuses 응답 구조)

### 항목 9: git 커밋 & push

**상태**: ⏳ 진행 예정 (다음 단계)

### 항목 10: 사용자 안내

**상태**: ⏳ 진행 예정

CLAUDE.md "작업 완료" 섹션의 안내 문구 출력 후 정지 예정.

---

## 의사결정 기록

### 결정 1: 3개 도구 확정 (상세 조회 API 미사용)

**배경**: 
- 명세서에는 관리번호로 직접 조회하는 별도 API가 없음
- 전체 조회 후 필터링하거나, search(1~1)로 대체 가능

**결정**: 
- search_emission_facilities 1건 조회 방식으로 대체
- get_facility_info는 내부적으로 search(1~N) 여러 건을 조회 후 필터링

**근거**: 
- 단순성 (API 1개 재사용)
- 실무 사용성 (search로도 충분하나, 편의상 get_facility_info 별도 제공)

---

### 결정 2: JSON 고정, XML 지원 안 함

**배경**:
- 명세서는 TYPE에서 xml/json 모두 지원
- MCP 도구는 JSON 반환이 표준

**결정**:
- 서버 내부에서는 JSON만 요청
- XML 필요 시 사용자가 별도로 Seoul Open API 직접 호출

**근거**:
- FastMCP 도구의 표준 출력은 JSON
- XML 파싱 추가 복잡도 불필요

---

### 결정 3: rate limit 3단계 구현

**배경**:
- MCP는 Claude.ai에 공개되어 누구나 접근 가능
- 무제한 요청 시 API 서버 과부하 가능성

**결정**:
- IP 기반 rate limit 3단계 구현
- 임계값: 분당 3회, 위반 누적 5회 시 24시간 차단, 일일 30회

**근거**:
- Claude 정상 사용 시에는 이 한도를 초과하지 않음
- 악의적 접근 방지
- 다른 서울시 공개 MCP와 일관성 유지

---

### 결정 4: 좌표계 명시 (중부원점TM)

**배경**:
- 명세서: "위경도 좌표는 제공하고 있지 않음"
- XCRD, YCRD는 중부원점TM (EPSG:5174) 기준

**결정**:
- 도구 docstring에 명시
- README에 경고 (⚠️ 기호 사용)
- 응답 note에 항상 포함

**근거**:
- 사용자가 위경도로 착각하면 위치 기반 분석이 완전히 틀림
- 실제 사례: 타사 지도 API와 좌표계 불일치로 위치 표시 오류

---

## 리스크 및 대응

| 리스크 | 발생 확률 | 영향 | 대응 |
|---|---|---|---|
| API 응답 구조 다름 | 중간 | 높음 | 로컬 실측 테스트 우선 (curl로) |
| 선택 파라미터 부분 채움 금지 | 낮음 | 높음 | 에러 시뮬레이션, 사전 검증 로직 |
| 샘플 키 vs 실제 키 동작 다름 | 낮음 | 중간 | 양쪽 키로 테스트 |
| fly.io 배포 후 "도구 없음" 오류 | 매우 낮음 | 높음 | stateless_http=True 필수 구현 확인 |

---

## 참고 자료

- 명세서 출처: 서울 열린데이터광장 ("서울시 대기오염물질배출시설설치사업장 인허가 정보" 데이터셋)
- 데이터셋 ID: LOCALDATA_093008
- 데이터셋 URL: https://data.seoul.go.kr/ (검색: "배출시설")
- 제공 부서: 서울특별시 기후환경본부 대기정책과
- 담당자: 정찬욱 (02-2133-4438)

---

## 다음 단계

1. Claude Code에서 코드 구현 시작
2. 로컬 실측 테스트로 API 응답 구조 확인
3. 발견 사항을 본 DEVLOG에 추가 기록
4. 배포 및 커넥터 연결

---

*Last Updated: 2026-08-17 (설계 단계)*
