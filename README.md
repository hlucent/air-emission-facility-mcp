# 서울시 대기오염물질배출시설설치사업장 인허가 정보 MCP

Claude와 대화하며 서울시의 대기 배출시설 인허가 정보를 직접 조회할 수 있는 MCP 서버입니다.

**데이터 출처**: 서울특별시 기후환경본부 대기정책과  
**라이선스**: 공공누리 1유형 (저작권 표시 필수)  
**데이터 신선도**: 3일 지연 (매일 자동 갱신)  

---

## 주요 기능

### 🔍 도구 1: `search_emission_facilities`
대기오염물질 배출시설을 **페이징 조회**합니다.

```
사용 예:
  - 처음 100건 조회: start_index=1, end_index=100
  - 다음 페이지: start_index=101, end_index=200
  - 필드 선택 반환: include_fields='BPLC_NM,ROAD_NM_ADDR,SALS_STTS_NM'
```

**반환 정보**:
- 사업장명, 주소(지번/도로명), 전화번호
- 영업상태(영업/폐업/휴업), 인허가일자
- 업태/업종/종별, 환경업무구분
- 배출시설 조업시간, 연간 가동일수
- 좌표(중부원점TM 기준)

**제한사항**:
- 최대 1000건 차이까지 조회 가능
- 샘플 키: 최대 5건만 조회 가능

### 📋 도구 2: `get_facility_info`
관리번호로 **시설 상세정보를 조회**합니다.

```
사용 예:
  management_number='11110000010000001'
```

**반환 정보**:
- `get_facility_info` 도구로 조회한 시설의 전체 34개 필드

### 📊 도구 3: `list_facility_statuses`
영업상태별 시설 **현황을 조회**합니다.

```
반환 정보:
  - 영업: n개
  - 폐업: n개
  - 휴업: n개
  - 소재불명: n개
```

---

## 좌표계 주의사항 ⚠️

**이 MCP의 좌표는 위경도(위도/경도)가 아닙니다!**

- **좌표 체계**: 중부원점TM (EPSG:5174)
- **필드명**: `XCRD` (X좌표), `YCRD` (Y좌표)
- **변환 필요**: 위경도 지도에 표시하려면 좌표계 변환 필요
  - 예: 카카오맵 API의 좌표계 변환 도구 활용
  - 예: 서울시 GIS 포탈의 좌표 변환 서비스 활용

---

## 설치 및 배포

### 필수 조건

- Python 3.11+
- 서울 열린데이터광장 인증키 (무료 발급)
  - 신청처: https://data.seoul.go.kr/
  - 절차: 회원가입 → 마이페이지 → API 인증키 신청

### 로컬 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경변수 설정
echo "SEOUL_AIR_EMISSION_API_KEY=<발급받은키>" > .env

# 3. 서버 실행
python server.py
# 서버가 http://localhost:8000 에서 시작합니다
```

### fly.io 배포

```bash
# 1. fly 프로젝트 초기화
fly launch --no-deploy

# 2. API 키 설정
fly secrets set SEOUL_AIR_EMISSION_API_KEY=<발급받은키>

# 3. 배포
flyctl deploy

# 4. Claude.ai에 커넥터 등록
# 설정 > 커넥터에서 아래 주소로 연결:
# https://air-emission-facility-mcp.fly.dev/mcp
```

---

## API 응답 예시

### search_emission_facilities (처음 1건)

```json
{
  "count": 1,
  "result": [
    {
      "MNG_NO": "11110000010000001",
      "BPLC_NM": "서울시 대기환경과 시험시설",
      "LCPMT_YMD": "20200716",
      "SALS_STTS_NM": "영업",
      "ROAD_NM_ADDR": "서울특별시 강남구 테헤란로 123",
      "LCTN_ZIP": "06000",
      "TELNO": "02-2133-4290",
      "BZSTAT_SE_NM": "제조업",
      "XCRD": 960123.45,
      "YCRD": 1950678.90,
      "EMS_FCLT_OPER_HRM": 24,
      "EMS_FCLT_ANL_OPRTNG_DCNT": 365
    }
  ],
  "note": "본 데이터는 3일 지연 데이터입니다. 좌표는 위경도가 아닌 중부원점TM(EPSG:5174) 좌표입니다."
}
```

### get_facility_info (상세)

```json
{
  "found": true,
  "facility": {
    "MNG_NO": "11110000010000001",
    "OGDP_INST_CD": "11",
    "BPLC_NM": "서울시 대기환경과 시험시설",
    "LCPMT_YMD": "20200716",
    "SALS_STTS_CD": "03",
    "SALS_STTS_NM": "영업",
    "DTL_SALS_STTS_CD": "0301",
    "DTL_SALS_STTS_NM": "정상영업",
    ... (전체 34개 필드)
  }
}
```

### list_facility_statuses

```json
{
  "query_timestamp": "2026-08-17T12:34:56Z",
  "data_recency": "3일 지연",
  "statuses": {
    "영업": 1234,
    "폐업": 567,
    "휴업": 89,
    "소재불명": 12
  },
  "total": 1902,
  "note": "상태별 집계는 표본 기반 추정치입니다. 정확한 수치는 search_emission_facilities로 확인하세요."
}
```

---

## 에러 처리

### API 레벨 에러

| 코드 | 의미 | 해결책 |
|---|---|---|
| INFO-100 | 인증키 오류 | API 키 재확인, 재발급 |
| ERROR-300 | 필수값 누락 | 파라미터 입력값 확인 |
| ERROR-336 | 1000건 초과 | end_index - start_index ≤ 1000 조정 |
| ERROR-500 | 서버 오류 | 잠시 후 재시도 |

### Rate Limit (공개 배포 시)

- **분당**: 3회 요청 (초과 시 429 응답)
- **위반 누적**: 1시간 내 5회 이상 위반 시 IP 24시간 차단
- **일일**: 30회 요청 한도

정상적인 Claude 사용 시에는 이 제한에 걸리지 않습니다.

---

## 필드 설명 (34개)

| 필드 | 타입 | 설명 | 단위 |
|---|---|---|---|
| MNG_NO | STRING | 시설 고유 관리번호 | - |
| BPLC_NM | STRING | 사업장명 | - |
| LCPMT_YMD | STRING | 인허가일자 | YYYYMMDD |
| SALS_STTS_NM | STRING | 영업상태 | 영업/폐업/휴업/소재불명 |
| ROAD_NM_ADDR | STRING | 도로명주소 | - |
| XCRD | FLOAT | X좌표 (중부원점TM) | m (미터) |
| YCRD | FLOAT | Y좌표 (중부원점TM) | m (미터) |
| EMS_FCLT_OPER_HRM | INTEGER | 배출시설 조업시간 | 시간/일 |
| EMS_FCLT_ANL_OPRTNG_DCNT | INTEGER | 배출시설 연간 가동일수 | 일 |
| CTGRY_NM | STRING | 배출시설 종별 | - |
| ... | ... | (외 24개 필드) | ... |

---

## 사용 사례

### 예 1: 특정 지역의 배출시설 현황 파악
```
Claude: "강남구의 대기배출시설 현황을 조회해줄래?"

1단계: search_emission_facilities로 초기 100건 조회
2단계: 응답에서 강남구(지번주소 포함) 필터링
3단계: 영업상태별 집계
```

### 예 2: 특정 사업장의 상세정보 확인
```
Claude: "관리번호 11110000010000001의 시설 정보를 알려줄래?"

도구: get_facility_info(management_number='11110000010000001')
```

### 예 3: 시간 추이 분석
```
Claude: "지난 3개월간 신규 허가된 배출시설이 얼마나 되나?"

1단계: search_emission_facilities로 페이징 조회
2단계: LCPMT_YMD (인허가일자) 필터링
3단계: 시간별 집계
```

---

## 저작권 및 라이선스

**공공누리 1유형 (저작권 표시)**

본 데이터의 저작권자는 서울특별시입니다.  
이 MCP로 조회한 데이터를 2차 가공하거나 공개할 때는 다음을 포함해야 합니다:

```
저작권자: 서울특별시 기후환경본부 대기정책과
제공처: 서울 열린데이터광장
데이터명: 서울시 대기오염물질배출시설설치사업장 인허가 정보
라이선스: 공공누리 1유형
```

---

## 제한사항 및 주의사항

1. **3일 지연 데이터**: 오늘의 새로운 허가 정보는 포함되지 않습니다.
2. **위경도 미제공**: 지도 앱에 표시하려면 좌표계 변환이 필요합니다.
3. **최대 1000건**: 한 번에 최대 1000건까지만 조회 가능합니다 (페이징 필수).
4. **API 키 보안**: 인증키는 공개하지 마세요. fly.io 배포 시 secrets으로 관리됩니다.

---

## 문의 및 지원

- **데이터 오류 / 서비스 문의**: 서울특별시 기후환경본부 대기정책과 (02-2133-4290)
- **API 플랫폼 문제**: 서울 열린데이터광장 (https://data.seoul.go.kr/)
- **MCP 개발 피드백**: GitHub Issues (프로젝트 저장소)

---

## 변경 이력

- **v1.0** (2026-08-17): 초기 배포
  - 3개 도구 (search_emission_facilities, get_facility_info, list_facility_statuses)
  - rate limit 3단계 (분당/위반누적/일일)
  - 중부원점TM 좌표 제공

---

## 관련 MCP

이 MCP와 함께 사용하면 좋은 다른 서울 대기환경 MCP:

- **서울시 실시간 대기환경 현황**: 측정소별 실시간 오염도 데이터
- **서울시 실시간 자치구별 대기환경 현황**: 구별 평균 오염도
- **서울시 대기환경 정보**: 역사 추이, 예보 등

함께 활용하면 배출시설 정보(정적) + 측정치(동적)를 연결한 분석이 가능합니다.

---

**Made with FastMCP & Claude**  
Licensed under Public Cloud 1.0 (Source Attribution Required)
