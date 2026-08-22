# 요청 스키마 수집기 (Schema Collector)

`dhlrunner/chachacha-server` 에 추가한 계층. 미구현 엔드포인트로 들어오는 요청을
자동으로 수집하고 JSON 스키마를 추론해, 남은 엔드포인트 구현의 출발점을 만든다.

## 변경 요약

| 파일 | 변경 |
|---|---|
| `HTTP/SchemaCollector.cs` | **신규.** 관측·스키마 추론·저장·리포트 생성 |
| `HTTP/HTTPProcessor.cs` | 경로 정규화, 전 요청 관측, 미구현 폴백 응답 |
| `HTTP/HTTPPath.cs` | 정적 생성자에서 경로 상수 정규화 |
| `patch/Program.cs` | prefix/capture 디렉터리 인자, 종료 시 flush |

### 1. 경로 정규화 (버그 수정)

원본은 `urlPath == HTTPPath.Login` 으로 정확히 비교하는데, `HTTPPath.Login` 은
`/user/auth/login` (트레일링 슬래시 없음)이다. APK 문자열에는 `/user/auth/login/`
형태가 존재하므로, 클라이언트가 슬래시를 붙여 보내면 **모든 분기가 미매칭**되어
전부 폴백으로 떨어진다. 양쪽을 `TrimEnd('/') + ToLowerInvariant()` 로 정규화했다.

대소문자도 통일했으므로 `/TimeAttack/current/list` 같은 경로를 나중에 추가해도 안전하다.

### 2. 미구현 폴백 응답

원본은 알 수 없는 경로에 평문 `"OK"` 를 반환한다. 클라이언트가 이를 파싱하지 못해
거기서 진행이 멈추고, 그 뒤에 올 엔드포인트들을 관측할 기회를 잃는다.

대신 최소 성공 응답을 돌려준다:

```json
{"success":true,"errorCode":null,"token":123456789}
```

로그인 이후에는 협상된 키로 암호화해서 보낸다(`keyIssued` 플래그). 클라이언트를
최대한 더 진행시켜 **한 번의 플레이 세션에서 더 많은 엔드포인트를 노출**시키는 것이 목적.

### 3. 수집 산출물

`capture/` 디렉터리에 생성된다.

| 파일 | 내용 |
|---|---|
| `requests.jsonl` | 관측 원본 (append-only). 요청마다 1줄, 재분석·리플레이용 |
| `schema.json` | 엔드포인트별 병합된 필드 스키마 (기동 시 자동 로드, 세션 간 누적) |
| `report.md` | 사람이 읽는 리포트. 미구현 목록이 먼저 나옴 |

필드는 `infoReq.accountSeq`, `cars[].carNo` 처럼 평탄화된 경로로 기록되고,
여러 번 관측하면 **자동 병합**된다. 관측 횟수가 총 횟수보다 적으면 선택적 필드다:

```
| `gachaReq.carClass`  | string | 2 | `S`        |   ← 항상 존재
| `gachaReq.couponCode`| string | 1 | `XMAS2014` |   ← 2회 중 1회. 선택적
```

## 실행

```bash
# 관리자 권한 (실제 클라이언트 연결용, 80 포트)
chachacha-server.exe

# 권한 없이 테스트
chachacha-server.exe http://localhost:8080/ ./capture
```

종료는 Enter 또는 Ctrl+C — 둘 다 수집 결과를 flush 하고 요약을 출력한다.
미구현 엔드포인트 관측 시에는 즉시 저장하므로 강제 종료해도 유실되지 않는다.

## 검증 결과 (2026-08-13)

.NET 8.0.424 로 빌드, 오류 0. 클라이언트 흐름을 재현해 확인:

- 트레일링 슬래시 경로 정규화 매칭 ✅
- `/user/auth/login/` 평문 응답에서 `cryptoKey`/`initialVector` 수신 ✅
- AES-128-CBC/PKCS7 요청 암호화 → 서버 복호화 → 응답 암호화 → 클라이언트 복호화 왕복 ✅
- 미구현 6종 관측, 스키마 추론 및 필드 병합 ✅

## 다음 단계

1. 실제 APK 를 붙여 로그를 모은다. `report.md` 의 "미구현" 목록이 곧 작업 큐다.
2. 관측된 요청 스키마를 보고 `HTTPPath` + DTO + 분기를 추가한다.
3. 응답 스키마는 요청만으로는 알 수 없다. 클라이언트가 폴백 응답을 받고
   어디서 멈추는지 관찰하며 필드를 하나씩 채워나가는 방식이 현실적이다.

## 알려진 한계

- `aes` 인스턴스가 전역 하나(원본 `//Todo: 유저별로 정해야됨`). 단일 클라이언트 전용.
- 응답 스키마는 수집하지 않는다. 서버가 만들어 보내는 쪽이므로 관측 대상이 아니다.
- 복호화 실패한 바디는 원문(base64)만 저장된다. 나중에 키를 알아내면 `requests.jsonl`
  로 재처리할 수 있다.
