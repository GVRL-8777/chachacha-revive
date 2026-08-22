# `patch/` — 게임 DLL 을 뜯어고치는 C# 소스

게임의 `Assembly-CSharp.dll` 은 죽은 서버에 붙으려 하고, 중국 배포판은
여러 기능을 잠가 두었습니다. 여기 있는 프로그램들이 그 DLL 을 **Mono.Cecil 로
직접 고쳐** 서버 없이도 돌게 만듭니다.

세 갈래입니다.

- **APK 에 들어가는 코드** — `ChaLocal.cs` 는 게임 안에서 같이 도는 코드입니다.
  서버가 할 일을 폰 안에서 대신합니다.
- **패처** — 원본 DLL 을 읽어 호출 지점을 바꿔치기합니다.
- **들여다보는 도구** — 어느 메서드가 어디서 불리는지, 필드가 어떤 순서인지
  알아내는 작은 프로그램들. 패치를 만들기 전에 이것들로 먼저 봅니다.

---

## 담긴 파일 41개

### 이 폴더

| 파일 | 하는 일 |
|---|---|
| `README.md` | `patch/` — 게임 DLL 을 뜯어고치는 C# 소스 |

### APK 에 들어가는 코드

| 파일 | 하는 일 |
|---|---|
| `ChaLocal.cs` | 로컬 전용 차차차 — 서버 없이 폰 안에서 다 끝낸다. |
| `ChaLocalData.cs` | 자동 생성 — mkskel.py 가 chacnserver.py 에서 떠 온 것이다. |

### 게임 DLL 패처

| 파일 | 하는 일 |
|---|---|
| `localfix.cs` | localfix — 서버 없이 도는 빌드로 바꾼다. |
| `patchcn.cs` | 중국판(5577.com.cjenm.chachachacn) 패처. |
| `patch8.cs` | 8.apk(v1.3.1) 전용 패처. |
| `dbhook.cs` | 차차차 Assembly-CSharp.dll 패처 (Mono.Cecil) 1) AssetBundleManager.GetResourceDBFile 을 에셋 번들 대신 아래 순서로 읽게 바꾼다: sdcard/chachacha/<name>.json (adb push 로 밸런스 즉시 교체) <persistentDataPath>/chachacha/<name>.json DLL 안에 ldstr 로 박아넣은 기본값 2014년 CDN 은 죽었고 Unity 4 는 번들 빌드가 Pro 전용이라, 번들 경로 자체를 없앤다. |
| `tunnelfix.cs` | 이미 패치된 Assembly-CSharp.dll 에 두 가지만 더 손본다. |
| `shopfix.cs` | 트로피 결제창을 원화로 고치고, 결제를 그 자리에서 끝낸다. |
| `titlefix.cs` | titlefix — 타이틀 화면이 그냥 지나쳐 버리는 것을 고칩니다. |
| `tradefix.cs` | 되팔기 팝업(TradeCarPop)을 살린다. |
| `rankfix.cs` | 주간순위를 소셜 플랫폼 없이도 그릴 수 있게 한다. |
| `invitefix.cs` | 초대 목록을 소셜 플랫폼 없이도 채운다. |
| `modesfix.cs` | 중국판이 꺼 둔 모드를 켠다. |
| `notutorial.cs` | 중국 배포판에만 있는 '도움말 팝업' 네 개를 띄우지 않는다. |
| `restore.cs` | UnityEngine.dll 에서 바이트코드 스트리퍼가 잘라낸 메서드 선언을 되살린다. |
| `strswap.cs` | DLL 안의 ldstr 리터럴을 통째로 치환한다 (Cecil 이 재작성하므로 길이 제약 없음). |
| `chkrefs.cs` | ChaLocal.dll 이 부르는 모든 바깥 멤버가 게임의 Managed 폴더 안에 **실제로 있는지** 검사한다. |

### DLL 을 들여다보는 도구

| 파일 | 하는 일 |
|---|---|
| `dump.cs` | 이름이 특정 접두사로 시작하는 타입들의 IL 을 찍는다(기본 __Cha). |
| `alltype.cs` | 한 타입(중첩 포함)의 모든 메서드 IL 과 필드를 통째로 찍는다. |
| `cdump.cs` | Cecil 기반 범용 덤퍼 (잃어버린 파이썬 IL 도구 대체). |
| `tdump.cs` | 지목한 타입들의 메서드·필드 개수와 목록을 요약한다. |
| `lst.cs` | 타입의 public 메서드 목록을 인자 타입까지 붙여 찍는다. |
| `tn.cs` | 이름에 특정 낱말이 든 타입을 찾는다. |
| `tn2.cs` | 이름에 특정 낱말이 든 **열거형**을 찾는다(중첩까지). |
| `fld.cs` | 타입의 인스턴스 필드를 **직렬화 순서대로** 번호를 붙여 찍는다. |
| `flddump.cs` | 타입의 필드 이름과 타입을 두 칸으로 찍는다. |
| `fldref.cs` | 지목한 필드를 읽거나 쓰는 자리를 전부 찾는다. |
| `fieldinfo.cs` | 타입의 필드를 메타데이터 토큰·타입·static 여부까지 찍는다. |
| `sigdump.cs` | 메서드 하나의 인자·반환 타입(시그니처)을 찍는다. |
| `enums.cs` | 지목한 열거형 하나의 값 목록을 찍는다. |
| `enumdump.cs` | 어셈블리 안의 열거형과 그 값을 전부 찍는다. |
| `enumval.cs` | 정규식에 걸리는 열거형들의 값을 찍는다. |
| `callsite.cs` | 지목한 메서드가 어디서 몇 번 불리는지 센다. |
| `site3.cs` | 어떤 메서드를 부르는 메서드의 이름만 나열한다. |
| `s4.cs` | 어떤 메서드를 부르는 자리를 찾아 그 앞뒤 IL 까지 같이 보여 준다. |
| `apidump.cs` | NetQuery / NetRecive 클래스에 중첩된 eType 열거형을 전부 덤프한다. |
| `apischema.cs` | 응답 스키마 추출기 (기존 apidump + typemap 을 Cecil 하나로 통합). |

### C# 서버 쪽

| 파일 | 하는 일 |
|---|---|
| `Program.cs` | C# 커뮤니티 서버의 진입점. |
| `SchemaCollector.cs` | <summary> 미구현 엔드포인트로 들어오는 요청을 수집하고, 관측된 JSON에서 요청 스키마를 추론한다. |

### 라이브러리

| 파일 | 하는 일 |
|---|---|
| `Mono.Cecil.dll` | Jb Evain 의 Mono.Cecil (MIT). 패처들이 .NET DLL 을 읽고 고치는 데 씁니다. |

---

전체 목록은 [`docs/FILES.md`](../docs/FILES.md) 에 있습니다.
