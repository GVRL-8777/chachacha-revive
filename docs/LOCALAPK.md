# 서버 없는 로컬 전용 APK — 완성 (2026-08-21)

PC 서버(`chacnserver.py`) 없이 폰 혼자 돌아가는 빌드다. **실기로 끝까지 확인했다.**

```
chatool build --mode local --install      # 또는 런처의 '내보내기'
```

확인한 것 — 서버 프로세스를 죽이고 `adb reverse` 까지 걷어낸 상태에서:

| | 결과 |
|---|---|
| 로그인 · 내 정보 | 예외 0. 골드·트로피·타이어가 세이브 그대로 |
| 로비 · 주간순위 | 라이벌 5명까지 정상 |
| 복원한 맵 | `[CNBUNDLE] mainAsset=Gbeach01` — APK 안에서 읽었다 |
| 주행 | 필드 맵에서 정상 주행 |
| 저장 | 골드 1005034 → 1005039, 판수 1 → 2 가 폰의 파일에 남았다 |
| 런처로 갈아 끼우기 | 람보르기니·골드 777000 짜리 세이브를 넣으니 그대로 떴다 |

그리고 **앱을 통째로 지우고(데이터까지) 새로 깐 상태**에서 다시 확인했다:
기본값으로 정상 기동 → 세이브를 바깥 저장소에 스스로 만듦 →
런처로 가져오기·고치기·넣기 → 머스탱·골드 424242 로 다시 뜸. 예외 0.

처음 실행할 때 안드로이드가 창을 둘 띄운다(구형 앱이라 그렇다).
**권한 검토**('계속')와 **구버전 안내**('확인'). 둘 다 통과시켜야 게임이 뜬다.

## 구조

```
   게임 코드                          ChaLocal.dll
   ─────────                          ────────────
   Generic_HTTP.SendPacket    ──▶  Note(url, body)      요청을 받아 두고
   NetDispatcher._MakeWWW     ──▶  MakeWWW(...)         답을 만들어 둔다
        │ 통신하지 않는다                │
        ▼                               ▼
   WaitForXxx · _WWWSuccess   ◀──  Text(www) / Err(www)
        │                               │
        ▼                               ▼
   기존 파싱·화면 그대로          chasave.json (폰 안)
```

`MakeWWW` 는 곧바로 끝나는 **파일 요청**(`file://…/cha.dummy`)을 돌려준다.
그래야 코루틴의 `yield return www` 가 한두 프레임에 풀린다. 그리고 그 WWW 를
표에 적어 두었다가 `Text()` 에서 우리 답을 준다. 표에 없는 WWW —
프로필 사진 내려받기 같은 것 — 은 진짜 값을 그대로 흘려보낸다.

## 관문은 **둘**이었다

처음엔 `Generic_HTTP.SendPacket` 하나인 줄 알았는데 아니었다.
`NetDispatcher._MakeWWW` 라는 두 번째 길이 있고, **로비·되팔기·랭킹·결제**가
그 길로 간다(`NetDispatcher.Dispatch` 호출 32곳). 이걸 놓치면 로비 직전에
"네트워크가 원활하지 않아 접속 할 수 없습니다" 가 뜬다.

평문 본문은 `NetQueryData.queryString` 에 있다(`_BuildPacketStream` 이 그걸
암호화한다). 그래서 그 두 값을 그대로 `Note` 에 넘긴다.

## 피 흘린 것 둘

### 1. Unity 의 mscorlib 는 심하게 깎여 있다

전체 .NET 으로 컴파일하면 **통과하지만 폰에서 죽는다**. 없는 것들:

```
File.ReadAllText / WriteAllText / Move / Copy      System.IO.FileInfo (타입째)
Random.NextBytes / Random.Next(a, b)              Convert.ToDouble(object)
Convert.ToInt32(string, 밑수)                      long.TryParse(4인자)
```

그래서 `chkrefs.exe` 를 만들었다. **만든 DLL 이 부르는 바깥 멤버가 게임의
Managed 폴더 안에 실제로 있는지** 전부 검사한다.

```
./chkrefs.exe ChaLocal.dll mgbase        # 0개여야 한다
./chkrefs.exe mgbase/Assembly-CSharp.dll mgbase   # 기준선 9개(검사기 한계)
```

문자열 `switch` 도 피했다. 컴파일러가 `Dictionary` 표를 만들기 때문에
if 사슬로 두는 편이 안전하다.

### 2. `Aes.Decrypt` 를 전부 통과 함수로 바꾸면 안 된다

`Generic_HTTP` 는 **토큰·암호키·IV 를 암호화한 채로 들고 있다.**

```
set_initialVector:  _initialVector = aes.Encrypt(value)
get_initialVector:  return aes.Decrypt(_initialVector)
```

여기까지 통과 함수로 바꾸면 게터가 암호문을 돌려주고,
`CryptographicException: IV length is different than block size` 로 죽는다.
(키는 암호문이 32바이트라 AES-256 으로 통과해 버려서 **IV 만** 걸린다 —
증상만 보면 원인을 못 찾는다.)

`localfix` 는 `Generic_HTTP` 클래스만 빼고 바꾼다.

## 표는 손으로 옮기지 않았다

`mkskel.py` 가 `chacnserver.py` 를 그대로 불러
응답 뼈대 46경로 + 가격표·교환표·가챠 확률·초대 보상·되팔기 값을 떠서
`ChaLocalData.cs` 로 굽는다. 서버 쪽 표를 고쳤으면 이것만 다시 돌리면 된다.

```
python mkskel.py
```

## 한 벌에 둘 다 — 판은 파일 한 줄이 정한다

예전에는 APK 를 둘로 갈랐다. 서버판과 로컬판. 이제 **한 벌**을 굽고, 그
안에서 갈린다.

```
chamode.txt   안이 "server" 면 서버판, 그 밖(없어도)이면 로컬판
```

세이브 옆(`Android/data/<패키지>/files/`)에 둔다. 그래서 런처가 adb 로
갈아 끼울 수 있고, **게임 안 겹판**의 `USE SERVER / USE LOCAL` 로도 바꾼다.
바꾼 뒤에는 앱을 껐다 켜야 한다 — 켤 때 한 번만 읽는 자리가 있다.

### 갈고리 다섯 중 셋은 ChaLocal 혼자 갈린다

`Note` · `MakeWWW` · `BundleWWW` 는 서버판이면 원래 하던 일을 그대로 한다.
`MakeWWW` 가 **진짜 WWW** 를 돌려주면 그건 우리 표에 없으므로 `Text` ·
`Err` 도 진짜 값을 그대로 준다. 그래서 이 둘은 손댈 것이 없었다.

### 나머지 둘은 게임 자신의 타입이 있어야 한다

`Aes.Decrypt` 와 `CRSystem.myTrophy` 다. `ChaLocal.dll` 은
`Assembly-CSharp` 을 참조할 수 없다(서로 물린다). 그래서 `localfix` 가
**Assembly-CSharp 안에** 갈림길을 만들어 준다.

```
__ChaSwitch.__ChaDec(Aes a, string s)
    if (ChaLocal.IsLocal()) return ChaLocal.Dec(a, s);
    else                    return a.Decrypt(s);
```

호출 자리는 이 갈림길을 부르게만 바꾼다. 서명은 패치할 때 원본에서 그대로
떠 오므로 스택 모양이 어긋날 일이 없다 — 실제로 `Int64/Int64`,
`String/String` 으로 맞는 것을 굽는 자리에서 확인해 찍어 준다.

확인한 것: `chkrefs` 로 센 **못 푸는 참조가 기준(ACCN)과 똑같이 9개**다.
패치가 새로 만든 것이 하나도 없다는 뜻이다.

### 굽기

```
chatool build --mode both
```

로컬판과 **같은 것을 굽는다**. 번들도 들어가고(7.0 MB), 서버 주소도
자산에 박힌다. 나온 APK 는 57.4 MB.

## 복원 자산 번들

서버판은 `http://127.0.0.1:8888/bundle/pack.unity3d` 에서 받는다.
로컬판은 그 자리를 `ChaLocal.BundleWWW` 로 바꿔 **APK 안**
`assets/pack.unity3d` (StreamingAssets)에서 읽는다. 5.3 MB 가 APK 에 더 붙는다.

## 세이브 — `persistentDataPath` 를 믿으면 안 된다

```
/storage/emulated/0/Android/data/com.cjenm.chachacha.revive/files/chasave.json
```

**갓 설치한 기기에서 `Application.persistentDataPath` 는 앱 내부
(`/data/user/0/<패키지>/files`)로 잡힌다.** 거기는 루팅 없이 손댈 수 없어
런처가 세이브를 넣지도 빼지도 못한다. 폴더가 남아 있던 기기에서는 바깥으로
잡혀서 이 문제가 한동안 안 드러났다 — 앱을 완전히 지우고 다시 깔아 보고서야
나왔다.

바깥 폴더는 앱이 **직접 mkdir 할 수도 없다**
(`Access to the path … is denied`). 안드로이드가 시스템을 거쳐서만 만들어 준다.
그래서 JNI 로 한 번 요청한다.

```csharp
UnityPlayer.currentActivity.getExternalCacheDir()   // 시스템이 <패키지>/ 를 만든다
   -> 그 옆에 files/ 를 만들어 쓴다
```

`getExternalFilesDir` 이 아니라 캐시 쪽을 쓰는 이유는 인자가 없어서다.
`getExternalFilesDir(null)` 은 null 인자의 JNI 서명 해석이 까다롭다.

순서는 이렇다. **바깥(JNI) → 바깥(직접) → 앱 내부**. 마지막으로 물러서면
로그에 "런처로는 손댈 수 없다" 고 적는다. 그리고 예전에 내부에 쓰던 세이브가
있으면 처음 읽을 때 이어받는다.

**스키마는 `chastate.json` 과 똑같다.** 그래서 런처가 손댈 것 없이 그대로
쓰이고, 세이브를 서버판과 로컬판 사이에서 옮겨 다닐 수 있다.
루팅 없이 `adb pull/push` 로 꺼내고 넣을 수 있고, 폰의 파일 관리자로도 보인다.

`File.Move` 가 없어서 임시 파일 뒤 갈아치우기를 못 한다. 곧바로 덮어쓴다.
쓰는 중에 앱이 죽으면 그 판은 날아갈 수 있다(값이 바뀔 때만 쓴다).

## 로그

`logcat` 에서 `[ChaLocal]` 로 거르면 오간 것이 다 보인다.

```
adb logcat -d | grep -a ChaLocal
```

끄려면 `ChaLocal.Trace = false`.

## 두 빌드는 서로 덮어쓴다

패키지 이름이 같아서 서버판 `chacn_ko.apk` 와 로컬판 `chacn_local.apk` 는
같은 자리에 설치된다. 둘을 같이 두려면 패키지 이름을 바꿔야 하는데,
매니페스트와 자원 참조를 통째로 손봐야 해서 아직 하지 않았다.

## 파일

| 파일 | 무엇 |
|---|---|
| `ChaLocal.cs` | 미니 JSON · 세이브 입출력 · 처리기 30개 · 관문 |
| `ChaLocalData.cs` | 자동 생성. 서버에서 떠 온 표 전부 |
| `mkskel.py` | 그 표를 뜨는 도구 |
| `patch/localfix.cs` | Cecil 패처 |
| `patch/chkrefs.cs` | 참조가 실제로 풀리는지 검사 |
| `scripts/runlocal.sh` | 서버를 죽이고 로컬판만으로 띄워 보는 시험 |

## 패키지 이름

**하나로 고정입니다.**

```
com.cjenm.chachacha.revive     앱 이름 다함께 차차차
```

예전에는 프리셋마다 앱을 갈랐지만(`.rag` · `.rich`) 접었습니다. 시작
상태는 **세이브 파일**이 정합니다 — `PRESETS.md` 를 보라.

바꾸는 곳은 딱 둘이다 (`setpkg.py`, 빌드 사슬의 서명 직전).

1. `AndroidManifest.xml` 의 `package=` — 이진 XML 이라 문자열 풀을 다시 쓴다
2. `resources.arsc` 의 패키지 이름 — 이름 칸이 UTF-16 128자 **고정**이라
   제자리에서 덮어쓴다

**클래스 이름은 원판 그대로 뒀다.** 매니페스트가 액티비티를 절대 이름으로
적어 두어서 패키지와 클래스가 달라도 된다. 대신 부를 때 상대 이름은 안 먹는다.

```
adb shell am start -n com.cjenm.chachacha.revive/com.cjenm.chachachacn.CustomUnityPlayerActivity
```

APK 에 구워 넣는 **시작 세이브**는 런처에서 고른 것이다
(`mkskel.py --save saves/<이름>.json`). 폰에 다른 세이브를 넣으면 그게 이긴다.

`mainData` 안 유니티 `bundleIdentifier` 는 원판 이름 그대로다. 게임 DLL 이
그 값을 안 읽고, 세이브 자리는 JNI 로 실제 패키지에서 받아 온다.
