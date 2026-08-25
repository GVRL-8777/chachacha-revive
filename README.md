# 다함께 차차차 리바이브!

## 고지

- 해당 프로젝트는 생성형 인공지능의 도움을 크게 받았습니다.
- 해당 프로젝트는 관련된 모든 저작권 보유자의 저작권을 침해할 의도가 없음을 밝힙니다.
- 해당 프로젝트의 잘못된 사용으로 인한 피해 발생 시 발제자는 그 어떠한 법적 책임도 지지 않습니다.
- **32비트(armeabi-v7a) 전용입니다.** 원본 게임에 64비트 라이브러리가 아예
  들어 있지 않아, 32비트를 지원하지 않는 최신 기기에서는 설치나 실행이
  불가능합니다. 구세대 기기라도 사양에 따라 실패할 수 있습니다.

## 개요

2017년 서비스가 종료된 추억의 스마트폰 게임 "다함께 차차차" 를
되살리는 프로젝트입니다.

서버가 폐쇄되어 다수의 데이터가 유실되었으나, 인터넷에 남아 있던 소수의
자료들을 기반으로 살려 보았습니다. **서버 없이 로컬 환경에서도 돌아갑니다.**
(즉 안드로이드 스마트폰에 APK만 깔 수 있으면 제약 없이 실행 가능합니다)

여력이 닿는 대로 제보를 받아 계속 유지보수해 나갈 계획입니다.
**남은 자료를 가지고 계시다면 보내 주세요.** 
무엇이 필요한지는 아래 [찾습니다](#찾습니다) 에 적어 두었습니다.

**그 외 지금은 서비스가 종료된 여러 온라인 게임들도 찾고 있습니다.**
특히 오래된 핸드폰의 android/data 폴더 안에 아래 제목의 폴더가 남아 있다면 보내주세요!
**- "다함께 차차차 2"(com.netmarble.chachacha2)**, 
**- "드리프트 걸즈"(com.nhnent.driftgirls.NE)**

---

## 어디까지 왔나

서버와의 통신이 필수이던 원래 게임과 달리, **인터넷 없이 폰 혼자서도**
돌아가게 고쳤습니다. 서버 몫은 앱 안의 코드가 대신합니다.
필요하면 서버에 붙는 쪽으로 되돌릴 수도 있습니다.

| | |
|---|---|
| **되살린 것** | 주간순위 · 지난주 순위 · 초대 · 수신함 · 결제 · 튜닝 · 등급업 · 차량 구매 · 자동차 가챠 · 장애물(허들) 모드 · 차량 되팔기 |
| **맵** | 다른 배포판에서 테마 10종을 이식 (그리스 · 빅 · 아쿠아 계열) |
| **한국어화** | 시작 화면 · 타이틀 로고 · 앱 이름 · 중국판 전용 팝업 끄기 |
| **판 가르기** | APK 는 한 벌. 시작 상태는 **세이브 파일**이 정합니다 |
| **판 나누기** | 로컬판과 서버판을 **따로** 굽습니다. 앱 안에서는 못 바꿉니다 |
| **정식판 복원** | 한국 5.1.0 에서 차 8대 · 보이스 3벌 · 컷인 10장을 옮겨 왔습니다 |
| **런처** | 세이브 편집 · 자산 뽑기/칠하기 · 새 차 추가 · APK 굽기 (한국어 · 영어) |
| **자산 도구** | 모델 · 텍스처 · 뼈대 · 동작을 OBJ · glTF · STL · PNG 로 꺼내기 |
| **추가** | 기존 게임에는 없던 세이브 시스템 도입 + 현질용 재화(트로피) 무료화 |

아직 못 살린 것과 왜 못 살렸는지는 [`docs/DORMANT.md`](docs/DORMANT.md) 에
적어 두었습니다.

---

## 찾습니다

혼자 자료를 뒤져 맞춘 것이라 **빈 곳이 많습니다.** 아래 중 하나라도 가지고
계시면 Issue 로 알려 주세요.

### 1. 다른 판본의 APK

특히 **한국 서비스 말기 판본**과 **초기 판본**을 찾습니다. 지금 뼈대로 쓰는
것은 중국 배포판이라, 한국판에만 있던 것들이 통째로 빠져 있을 수 있습니다.

### 2. 서비스 중의 서버 응답 · 패킷 기록

API 는 클라이언트 코드를 눈으로 뜯어 맞춘 것입니다. **진짜 응답이 어땠는지는
모릅니다.** HTTP 로그, 프록시 캡처, 뭐든 좋습니다.

### 3. 아직 폰에 남아 있는 게임 데이터

**이게 가장 귀합니다.** 게임을 지웠어도 폴더가 남아 있는 경우가 많습니다.
파일 관리자로 아래 자리를 확인해 주세요.

```
내장 저장공간/Android/data/com.cjenm.chachacha/
내장 저장공간/Android/obb/com.cjenm.chachacha/
```

- **다함께 차차차** — `com.cjenm.chachacha`, `com.cjenm.chachacha_inni`,
  `com.cjenm.chachachacn` 중 아무거나
- **다함께 차차차 2** — `com.netmarble.chachacha2` 혹은 비슷한 이름

폴더째 압축해서 보내 주시면 됩니다. **안을 열어 보지 않으셔도 됩니다** —
뭐가 쓸모 있는지는 제가 보겠습니다.

> 게임 APK 자체(`.apk`)가 남아 있다면 그것도 꼭 알려 주세요.
> **판본이 다르면 그 자체로 새 자료입니다.**

### 4. 이벤트 · 시즌 자료

공지 내용, 이벤트 일정, 출석 보상, 콜라보 차량 — 지금은 전부 비어 있습니다.

### 5. 기타 세이브 관련 파일 · 계정 자료

실제 진행이 어떤 모양이었는지 알 수 있습니다.

---

## 어떤 APK 를 구해야 하나

### ① 뼈대 — 중국 배포판 (필수)

| | |
|---|---|
| 패키지 | `com.cjenm.chachachacn` |
| 버전 | **1.2.1** |
| 크기 | **41,767,401** 바이트 (39.8 MB) |
| sha256 | `e0619ded86abd90b3da691f0dfbac0f2d73cec994f1ab28b137ec531596032ff` |
| 흔한 이름 | `5577.com.cjenm.chachachacn.apk` |

제가 구할 수 있던 APK 중 유일하게 **CDN 계층이 없는 버전이었습니다.** 
자산이 전부 APK 안에 들어 있어서 이미 죽은 넷마블 CDN 을 안 찾습니다. 
막히는 곳은 360/NetmarbleS 소셜 플러그인 초기화 하나뿐인데 그건 건너뛸 수 있습니다.

한국판(`com.cjenm.chachacha` 7.7.0)에는 `AssetBundleManager` 가 들어 있어
자산 일부를 서버에서 받아 오려 합니다. 그래서 뼈대로는 못 씁니다.

### ② 한국어 그림 — 한국판 (한국어 지원용)

| | |
|---|---|
| 패키지 | `com.cjenm.chachacha` |
| 버전 | **7.7.0** |
| 크기 | 26.6 MB |
| sha256 앞자리 | `c540a1118d4d3e2fa3165824ca48cc50…` |
| 흔한 이름 | `CCC_fK_v7.7.0.apk` |

여기서 **시작 화면 · 런처 아이콘 · 타이틀 로고**를 가져옵니다. 중국판의
`一起车车车` 로고를 이 아틀라스의 `다함께 차차차` 조각으로 갈아 끼웁니다.

### ③ 한국어 문자열표 — LINE GoGoGo (한국어 지원용)

| | |
|---|---|
| 패키지 | `com.linecorp.LGCAR` |
| 버전 | **1.0.3** |
| 크기 | **33,002,191** 바이트 (31.5 MB) |
| sha256 | `fe0e75adeb26bd842218081e8d051f70c3d8fbc060b34d44cc8351887fc4d2ad` |
| 흔한 이름 | `LINE_GoGoGo-1.0.3.apk` |

일본판. 이 판의 `tb_systemtext` 가 **한국어 원본**입니다. 
게임 안의 거의 모든 글이 여기서 나옵니다.

> 한국어화를 건너뛰면 ②③ 은 없어도 됩니다. 대신 게임이 **중국어로** 돕니다.

### ④ 맵 이식원 — GoGoGo Racer (선택)

| | |
|---|---|
| 패키지 | `net.netmarble.m.push.id` |
| 버전 | **1.4.3** |
| 크기 | **41,506,938** 바이트 (39.6 MB) |
| sha256 | `d8cf006d7187229a1a98f0168b00857072cf08a375b4a05125e77f743c7ca3a7` |
| 흔한 이름 | `gogogoracer-1-4-3.apk`, `YX_com.netmarble.chachachaf.apk` |

같은 엔진(Unity 4.1.5f1)으로 만든 자매작입니다. 중국판에 없는 배경 테마
10종이 들어 있습니다. **없어도 게임은 돌아갑니다** — 맵이 원래의 세 종류로
줄어들 뿐입니다.

### 확인하는 법

```bash
sha256sum 5577.com.cjenm.chachachacn.apk
unzip -p 5577.com.cjenm.chachachacn.apk AndroidManifest.xml | strings | grep chachachacn
```

버전이 다르면 자산의 자리(pathID)가 어긋나 패치가 엉뚱한 곳을 칩니다.
**크기와 해시를 꼭 맞춰 보세요.**

---

## 폴더 안내

```
tools/       런처 · 서버 · 빌드 도구. 서로 부르므로 한자리에 둡니다
patch/       Cecil 패처 소스와 APK 에 들어갈 C# 코드
scripts/     빌드 사슬과 잔심부름 (.sh)
research/    한 번 쓰고 만 조사용 스크립트. 혼자 도는 것들입니다
docs/        연구 기록
lang/        런처의 말 (en · kr)
```

명령은 **저장소 뿌리에서** 실행합니다. `tools/` 안으로 들어가지 마세요.
도구들은 뿌리를 작업 폴더로 보고 `x77/` · `saves/` · `lang/` 을 찾습니다.

파일 하나하나가 무슨 일을 하는지는 [`docs/FILES.md`](docs/FILES.md) 에
264개 전부 한 줄씩 적어 두었습니다.

```
python tools/chatool.py
```

`research/` 는 자산을 뜯어보며 쓴 일회성 도구 모음입니다. 다른 데서
부르지 않으니 안 쓰셔도 되고, 무엇을 어떻게 알아냈는지 궁금하실 때
들여다보시면 됩니다.

---

## 필요한 것

| | 왜 |
|---|---|
| **Python 3.9 이상** | 도구 전부 (저는 3.13 버전으로 작업했습니다) |
| `UnityPy` | Unity 자산 읽기/쓰기 (63개 파일이 씁니다) |
| `Pillow` | 텍스처 · 초상화 |
| `cryptography` | 서버의 AES |
| **JDK** (`jarsigner`) | APK 서명 |
| **Android SDK platform-tools** (`adb`) | 폰에 넣기 |
| **.NET Framework csc** | IL 패처. `v4.0.30319` 로 패처를, `v3.5` 로 `ChaLocal.dll` 을 굽습니다 |
| `patch/Mono.Cecil.dll` | 패처가 씁니다 (저장소에 포함) |

`csc` 자리도 알아서 찾습니다. 윈도우가 어느 드라이브에 깔렸든 상관없고,
필요하면 `CHA_CSC` 로 짚어 주면 됩니다.

```bash
pip install UnityPy Pillow cryptography
```

`csc` 는 윈도우에 원래 들어 있습니다
(`C:\Windows\Microsoft.NET\Framework\v3.5\csc.exe`). **v3.5 가 꼭 필요합니다** —
이 게임의 mscorlib 는 .NET 2.0 이라 최신 컴파일러로 구우면 없는 것을
참조합니다.

---

## 만드는 법

### 0. 자리 잡기

스크립트들이 **정해진 자리**를 찾습니다. 이 모양을 지켜 주세요.

```
chachacha-revive/
  x77/                                  작업 트리 — 여기를 고쳐 나갑니다
  survey/5577.com.cjenm.chachachacn/    손대지 않은 중국판 (견줌용)
  survey/gogogoracer-1-4-3/             맵 이식원
  kr/                                   한국판을 푼 것
  line_tb_systemtext.txt                LINE 판에서 뽑은 한국어 문자열표
  mgbase/                               기준 DLL 이 놓일 자리
  bundles/                              구운 자산 번들
  saves/                                세이브
```

```bash
git clone <이 저장소> chachacha-revive && cd chachacha-revive
mkdir -p x77 survey kr mgbase bundles

# ① 중국판 — 작업 트리와 원본 견줌용, 두 벌
unzip -o 5577.com.cjenm.chachachacn.apk -d x77
unzip -o 5577.com.cjenm.chachachacn.apk -d survey/5577.com.cjenm.chachachacn

# ② 한국판 — 그림을 가져올 곳
unzip -o CCC_fK_v7.7.0.apk -d kr

# ④ 맵 이식원 (선택)
unzip -o gogogoracer-1-4-3.apk -d survey/gogogoracer-1-4-3

# 관리 DLL 을 기준 자리로
cp x77/assets/bin/Data/Managed/*.dll mgbase/
```

`x77/` 은 계속 고쳐 나갑니다. **망쳤으면 원본 APK 에서 다시 풀면 됩니다** —
그래서 원본은 지우지 마세요.

**원본 APK 는 어디에 두어도 됩니다.** 스크립트가 알아서 찾습니다 —
`CHA_APK_DIR` 환경변수 → `apk/` 폴더 → 저장소 폴더 → 그 부모 순으로 봅니다.
파일 이름도 배포처마다 달라서 여러 이름을 두고 찾습니다.

```bash
python tools/chapaths.py          # 어느 것이 있고 없는지 한눈에
```

```
apk 를 찾는 자리:
  /home/me/chachacha-revive
  /home/me

  글자 폭을 잴 한글 폰트: /usr/share/fonts/truetype/nanum/NanumGothicBold.ttf

  cn     중국판 com.cjenm.chachachacn 1.2.1        5577.com.cjenm.chachachacn.apk
  gogo   GoGoGo Racer 1.4.3 (맵 이식원)             gogogoracer-1-4-3.apk
  kr     한국판 com.cjenm.chachacha 7.7.0          — 없음
```

딴 데 두셨으면 알려 주시면 됩니다.

```bash
export CHA_APK_DIR=/어디에/두었는지        # 윈도우는 set CHA_APK_DIR=...
```

못 찾으면 **무엇을 어디에 두면 되는지 알려 주고 멈춥니다.**

한글화 도구는 문구가 화면에서 몇 픽셀을 먹는지 재느라 **한글 트루타입**도
하나 씁니다. 윈도우의 맑은 고딕, 리눅스의 나눔고딕, macOS 의 애플 고딕을
차례로 찾아보고, 없으면 `CHA_FONT` 로 알려 주시면 됩니다.

```bash
export CHA_FONT=/어디에/NanumGothicBold.ttf
```

### 1. 한국어 문자열표 뽑기

LINE 1.0.3 의 `tb_systemtext` 를 텍스트로 꺼내 `line_tb_systemtext.txt` 로
둡니다.

```bash
mkdir -p survey/line && unzip -o LINE_GoGoGo-1.0.3.apk -d survey/line
python tools/dump_systemtext.py survey/line line_tb_systemtext.txt
```

`키 = 값` 이 줄마다 늘어선 표가 나오면 맞습니다.

### 2. 한국어화 + 소셜 건너뛰기

```bash
python tools/korean_res.py       # 시작 화면 · 런처 아이콘   (한국판에서 가져옴)
python tools/krtitle.py          # 타이틀 로고 一起车车车 -> 다함께 차차차
python tools/mkkorean.py         # 문자열표 갈아 끼우기      (LINE 판에서 가져옴)
python tools/bakedkr.py          # 프리팹에 박힌 중국어 라벨 78개
python tools/swapfont.py         # 한글 글리프가 있는 글꼴로

csc /nologo /target:exe /out:patchcn.exe /r:patch/Mono.Cecil.dll patchcn.cs

# patchcn.exe <읽을 DLL> <쓸 DLL> <Managed 폴더> <지연 프레임>
./patchcn.exe mgbase/Assembly-CSharp.dll mgbase/Assembly-CSharp.dll \
              x77/assets/bin/Data/Managed 150
```

`mkkorean.py` 는 **중국판 키 목록을 기준**으로 삼습니다. 한국어표가 더 뒤
버전이라 같은 키라도 `{0}` 같은 자리표시자 구성이 다른 경우가 있는데,
그대로 넣으면 `String.Format` 이 터집니다. 그래서 구성이 같을 때만 바꿉니다.

`patchcn` 이 하는 일은 하나입니다. 타이틀에서 **소셜 플러그인 단계를 건너뛰고
게스트 레이스로 바로 들어가게** 합니다. 이 게임이 멈추는 자리가 거기입니다.

여기까지 나온 `mgbase/Assembly-CSharp.dll` 이 앞으로의 기준입니다.

### 3. 기능 패처 사슬

```bash
sh scripts/builddll.sh
```

여덟 개를 차례로 겁니다. **순서를 지켜야 합니다** — 앞의 것이 만든 함수를
뒤의 것이 씁니다.

| | 하는 일 |
|---|---|
| `tunnelfix` | 터널 세트 되살리기 · 번들 주소 |
| `notutorial` | 중국판 전용 도움말 팝업 4개 끄기 |
| `rankfix` | 소셜 없이도 주간순위가 그려지게 |
| `invitefix` | 초대 목록에 이웃 5명 |
| `shopfix` | 결제창 원화 표시 · 즉시 결제 |
| `modesfix` | 중국판이 꺼 둔 모드 켜기 (장애물 · 되팔기) |
| `tradefix` | 되팔기 팝업의 널 딕셔너리 초기화 |
| `titlefix` | 타이틀이 그냥 지나쳐 버리는 것 |

나온 `ACCN.dll` 이 **서버판**의 게임 코드입니다.

### 4. 맵 이식 (선택 — ④ APK 가 있을 때)

0단계에서 이미 `survey/gogogoracer-1-4-3/` 로 풀어 두었으니 바로 시작합니다.

```bash
python tools/mapspec.py                       # 옮길 자산과 의존 파일 목록
python tools/sfmerge.py pack.dat cha @packspec.txt
python tools/derename.py pack.dat
python tools/mkbundle.py bundles/pack.unity3d pack.dat
```

테마 10종이 `bundles/pack.unity3d` 하나로 묶입니다. 게임은 이걸 로컬판이면
APK 안에서, 서버판이면 서버에서 받아 갑니다.

### 5. APK 굽기

여기부터는 도구 하나가 다 합니다.

```bash
python tools/chatool.py build --mode local     # 서버 없이 도는 판
python tools/chatool.py build --mode server    # PC 서버에 붙는 판
```

속에서 이런 일이 일어납니다.

1. 고른 세이브를 `ChaLocalData.cs` 로 구움 (`mkskel.py`)
2. `ChaLocal.dll` 컴파일 (csc **v3.5**)
3. `localfix` 로 게임 코드에 갈고리 걸기 → `ACLOCAL.dll`
4. 번들을 APK 안 `StreamingAssets` 로
5. `pack.py` 로 재조립 → `setappname.py` (앱 이름) → `setpkg.py` (패키지 이름)
6. `jarsigner` 로 서명

나오는 파일은 `chachacha_revive.apk`, 약 57 MB 입니다.

### 6. 폰에 넣기

```bash
adb install -r --bypass-low-target-sdk-block chachacha_revive.apk
```

**처음 깔면 안드로이드가 창을 둘 띄웁니다.** 구형 SDK 앱이라 그렇습니다.
둘 다 통과해야 뜹니다.

1. 권한 검토 → `계속`
2. 구버전 안내 → `확인`

---

## 런처

굽는 것 말고도 대부분의 일을 창 하나에서 합니다.

```bash
python tools/chatool.py            # 브라우저에서 열립니다
```

파이썬이 없는 PC 라면 [릴리스](../../releases)의 `chatool.exe` 하나만
받으면 됩니다. 같은 런처가 그대로 들어 있습니다.

- **세이브** — PC 와 폰의 세이브를 나란히 놓고 만들고 · 옮기고 · 지웁니다
- **고치기** — 골드 · 트로피 · 보유 차량 · 드라이버 · 아이템 · 스킬 · 공지
- **자산 · 모델** — 3D 미리보기, 동작 재생, **감기 검사**, 파일로 꺼내기
- **굽기** — 위의 두 판, 서버 주소 설정
- **기록** — 한 일을 전부 남깁니다

화면 말은 한국어 · 영어를 오갑니다. `lang/en.json` 을 복사해 값만 바꾸면
언어가 하나 늘어납니다 — 자세한 것은 [`docs/TOOL.md`](docs/TOOL.md).

---

## 서버로도 돌리기

혼자 놀 거면 **로컬판이면 충분합니다.** 서버는 여럿이 쓰거나 서버 쪽을
고쳐 볼 때 씁니다.

```bash
python tools/chacnserver.py 8888
adb reverse tcp:8888 tcp:8888     # 폰의 127.0.0.1:8888 이 PC 로
```

붙는 방법은 넷입니다 — USB 직결 · 같은 공유기 · 사설 메시(Tailscale 등) ·
클라우드. 런처의 굽기 화면에서 고르면 주소를 APK 에 박아 줍니다.

> **주의.** 지금 서버는 **한 사람용이고 인증이 없습니다.** 포트에 닿는
> 사람이 곧 주인입니다. 아무나 닿는 자리에 두지 마세요. 평문 HTTP 라
> 유니티 4.1.5 가 요즘 TLS 를 못 받습니다.

---

## 여기 없는 것

- **원본 APK** — 저작권자 것입니다. 각자 구하세요.
- **뽑아낸 게임 자산** (모델 · 텍스처 · 소리 · 번들) — 같은 까닭입니다.
- **서명 열쇠** — 각자 만드세요.
  ```bash
  keytool -genkey -v -keystore test.keystore -alias test \
          -keyalg RSA -validity 10000
  ```
- **세이브 · 작업 기록** — 개인적인 것이라 뺐습니다.

이 저장소의 코드는 **원본을 고치는 방법**을 적은 것이지 원본을 담고 있지
않습니다. 그래도 문제가 된다면 알려 주세요. 바로 내리겠습니다.

---

## 문서

| | |
|---|---|
| [`docs/RESTORE.md`](docs/RESTORE.md) | 되살리는 순서 · 빌드 사슬 |
| [`docs/LOCALAPK.md`](docs/LOCALAPK.md) | 서버 없이 돌리기 · 로컬판과 서버판 나누기 |
| [`docs/PRESETS.md`](docs/PRESETS.md) | 세이브로 판 가르기 · 게임 안 세이브 칸 |
| [`docs/TOOL.md`](docs/TOOL.md) | 통합 도구 · 자산 · 언어 |
| [`docs/NEWCAR.md`](docs/NEWCAR.md) | 새 차 추가 |
| [`docs/CARS5.md`](docs/CARS5.md) | 한국 정식판 5.1.0 에서 건져 온 것들 |
| [`docs/DORMANT.md`](docs/DORMANT.md) | 살릴 수 있는데 안 살린 것 |
| [`docs/CAPTURE.md`](docs/CAPTURE.md) | 요청 스키마 수집기 |

기록에는 **실패한 것도 적어 두었습니다.** 같은 데서 두 번 넘어지지 않게요.

---

## 라이선스

이 저장소의 **코드와 문서**는 MIT입니다. 상업적 목적이 아닌 이상 자유로이 사용할 수 있습니다.

게임 "다함께 차차차" 와 그 자산의 권리는 **넷마블 · CJ E&M** 에 있습니다.
이 프로젝트는 그 권리를 주장하지 않고, 자산을 담고 있지도 않습니다.
이 프로젝트는 순수히 상업적 목적이 배제된 보존과 연구에 그 목적을 두고 있습니다.

---

## 제보

- 실행 시 문제가 발생할 경우, 혹은 유실된 자료를 가지고 계시다면
  **Issues** 로 제보 바랍니다.
- 문제 제보 시 가능한 한 상세한 설명을 첨부해 주시면 감사하겠습니다.
  어느 단계에서 멈췄는지, 어떤 APK 와 어떤 기기를 쓰셨는지 적어 주시면
  좋습니다.
- **자료 제보는 Issue 로 부탁드립니다.**
- 파일이 커서 올리기 어려우면 Issue로 연락 주세요.
