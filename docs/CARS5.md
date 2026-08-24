# 한국 정식판 5.1.0 에서 건져 온 것들

2026-08-24 에 한국 정식 5.0.1 · 5.1.0 APK 를 새로 구했습니다. 지금 빌드는
**중국판 7.7** 을 바탕으로 한글화한 것이라, 한국 서비스에만 있던 자원이
통째로 빠져 있었습니다. 5.1.0 에서 되찾은 것을 적어 둡니다.

| | 우리(중국판 7.7) | 정식 5.1.0 |
|---|---|---|
| 차 | 30대 (+트로이) | **37대** |
| 캐릭터 보이스 | 11명 220줄 | **14명 280줄** |
| 컷인 그림 | **4장** | **14장** |
| 드라이버 | 8명 | 10명 |
| 맵 조각 | 29개(번들) + 중국판 Resources | 같음 — 더 줄 것이 없다 |

---

## 1. 정품 차 8대 (`tools/addcars5.py`)

```
폴리(17) 로이(18) 엠버(19) 헬리(21) 태극호(23)
아크엔젤(34) W3(35) 블리츠(36)
```

아크엔젤 · W3 · 블리츠는 중국판에 자원이 아예 없어 `trimcars.py` 가 차 표에서
지워 뒀었고(안 지우면 자동차 샵에서 `Instantiate(null)` 로 죽습니다), 헬리는
공여판에서 빌려 온 임시 사본이었습니다. 폴리 · 로이 · 엠버 · 태극호는 보이스만
남고 차가 없었습니다. 여덟 대 모두 5.1.0 에 원본이 그대로 있습니다.

### 넘어야 했던 것 — MonoScript 번호가 판마다 다르다

차 프리팹은 `CarDataLinker` 같은 스크립트가 붙어 있어야 굴러갑니다. 그런데
그 참조(`m_Script`)는 `sharedassets0.assets` 안의 **pathID** 이고, 그 번호는
빌드마다 다릅니다. 실측했습니다 — 이름이 겹치는 스크립트 497개 중 번호가
같은 것은 **0개**였습니다.

```
JumpLanding    우리 616   5.1.0 592
CarDataLinker  우리 492   5.1.0 479
BaseData       우리 253   5.1.0 248
```

다행히 여덟 대가 쓰는 스크립트는 여섯 갈래(312군데)뿐이고 전부 우리 빌드에도
있습니다. 그래서 원본 186개를 스크래치로 뜨면서 `m_Script` pathID 를
**클래스 이름으로 찾아** 우리 번호로 바꿔 적습니다. 길이가 같아 제자리에서
고칠 수 있습니다.

### 스크립트가 들고 있는 참조도 옮겨야 한다

MonoBehaviour 는 타입트리가 없어 필드를 바이트로 세야 합니다. 여섯 갈래 중
둘이 참조를 듭니다(합쳐 204곳).

```
JumpLanding            +24 landingClip · +32 stepClip
ChangeTextureMaterial  +32 개수, 그 뒤로 Material 배열
```

`sfmerge` · `packadd` 의 `mbptr=` 는 원래 **안쪽 참조만** 옮겼습니다. 여기서는
68곳이 합치는 다른 파일을 가리키고 136곳이 바깥을 가리켜서, 타입트리 있는
오브젝트와 **같은 규칙**을 쓰도록 올렸습니다.

`EffectManager` 는 자리가 다 0 입니다 — 실행 중에 `Car/{0}/{0}_Effect` 를
찾아 채웁니다. `CarDataLinker` · `BaseData` · `PlayerCarData` 는 값만 듭니다.

### 이름 가림 — 재질 조회 36개 중 34개가 가려져 있었다

번들은 오브젝트를 **이름으로** 찾습니다(`Generic_Title.__ChaFromBundle` 이
`bundle.LoadAll()` 을 훑어 `obj.name.ToLower()` 로 표를 짭니다). 열쇠가
겹치면 나중 것이 이기고, GameObject 를 **마지막에** 훑으므로 GameObject 가
늘 이깁니다.

FBX 하나에서 나온 GameObject · Mesh · Texture2D · Material 은 이름이 다
같습니다. 그래서 `Car/Poli/Materials/Poli` 를 찾으면 재질이 아니라 프리팹 속
GameObject 가 나옵니다. IL 로 확인하니 그 자리는 이렇습니다.

```
Car/{0}/{0}@{1}          isinst GameObject
Car/{0}/{0}_robot@{1}    isinst GameObject
Car/{0}/Materials/…      isinst Material    ← 어긋나면 sharedMaterial 이
Car/{0}/Player_{0}_{1}   isinst GameObject     null 이 되어 차가 안 보인다
Car/{0}/{0}_Effect       isinst GameObject
```

`isinst` 가 어긋나면 null 이 들어갑니다. 재질이면 `set_sharedMaterial(null)`
이라 **차가 안 보입니다.** 그래서 조회 자리 112개를 뽑아, 같은 이름을 든
**다른** 오브젝트 246개에 `_` 를 붙여 비켜 세웁니다. 그것들은 전부 PPtr 로만
참조되므로 이름이 바뀌어도 그만입니다.

`@` 이름을 처음에 AnimationClip 으로 잡았다가 틀렸습니다. 되던 공여판 헬리를
보니 `car/helly/helly_robot@race` 가 **GameObject** 를 가리키고 있었고, IL 도
그렇습니다. 클립은 따로 있고(`Race` · `Damage` · `Jump`) 그건
`carName == "helly"` 일 때만 타는 가지라 정품 프리팹(carName 이 숫자)에는
걸리지 않습니다.

### 헬리는 갈아 끼운다

공여판 헬리와 정품 헬리는 이름이 똑같아 그냥 더하면 둘 중 하나가 이깁니다.
붙이기 전에 지금 번들의 `car/helly/*` 33개를 `old_` 로 개명하고 매니페스트에서
뺍니다. 자원은 남지만 아무도 못 찾으므로 부딪히지 않습니다.

### 차 표는 정식판 것을 통째로 쓴다

우리 표(31대)는 중국판에서 온 것이라 헬리 값이 우리가 지어낸 것이었고
CarIndex 도 17번에 얹혀 있었습니다. 5.1.0 표(37대)가 정답이라 통째로 바꿉니다.
`TurningStatusDB` · `UpgradeCostDB` · `TurningCostDB` 는 두 판이 **바이트까지
같아서** 안심하고 바꿀 수 있었습니다. 겹치는 30대 중 값이 다른 것은 다섯뿐.

```
CAT          Preminum False→True · mission10 → none
Challenger   EventCar False→True
Choper       none → mission18        Falcon  none → mission17
helly        CarIndex 17→21 · 트로피 0→60 · 아틀라스 CarIcon→SpecialCarIcon
             최고속 326→356 / 354→420 / 390→456 (우리가 지어낸 값이었다)
```

`mission17` · `mission18` 은 우리 문자열표에도 있습니다(확인). 트로이가 쓰던
자리(18)는 로이의 것이라 **트로이는 여기서 빠집니다.** 나중에 다시 넣도록
표 안에 공백 2000바이트를 남겨 둡니다(`addtroy.register_cardb` 가 찾습니다).

### 아이콘 (`tools/carsicon.py`)

폴리 · 로이 · 엠버 · 헬리 · 태극호는 우리 아틀라스에 이미 있었고, 아크엔젤 ·
W3 · 블리츠 여섯 칸만 없었습니다. 두 판의 `Atlas_SpecialCarIcon` 은 **판 짜임이
달라서**(겹치는 42개 중 좌표가 같은 것이 다섯뿐) 통째로 못 바꿉니다. 그래서
`troyicon.py` 와 같은 길로 그림 조각만 오려 빈 자리에 붙이고 스프라이트 표에
여섯 줄을 더합니다. DXT5 칸 1540개만 바뀌고 나머지 42개 아이콘은 바이트 하나
안 바뀝니다.

---

## 2. 보이스 세 벌 (`tools/addvox5.py`)

```
ROPE       정신이     Driver_8    지금 빌드에서 바로 울린다
NAJUNGBI   나정비     Driver_9    드라이버가 없어 소리만 들어 있다
AHNBYULE   안별이     Driver_10   드라이버가 없어 소리만 들어 있다
```

보이스를 고르는 길은 이렇습니다.

```
"Character VOX/" + eCutinModelType + "/" + eCutinModelType + "_VOX_" + …
```

우리 `eCutinModelType` 은 열둘(끝이 `ROPE`), `eDriverType` 은 여덟입니다.
5.1.0 은 열넷 · 열이라 `NAJUNGBI` · `AHNBYULE` 이 더 있습니다. 정신이는
**둘 다 이미 있는데 소리만 없었습니다.** 그 자리를 채웠습니다.

소리 60개는 자산 파일 55개에 흩어져 있고 그중 하나는 UI 화면이 통째로 든 큰
파일입니다(`*_VOX_CHOICE` · `*_VOX_EQUIP` 이 거기 있습니다). 통째로 들여오면
쓰지도 않을 오브젝트 2천 개가 딸려 오므로 **AudioClip 60개만 오려** 새 파일
하나로 묶습니다. AudioClip 은 가리키는 것이 없어 그냥 옮겨도 됩니다.

원본에 `AHNBYULE _VOX_CHOICE` 처럼 **이름에 빈칸이 낀 것**이 하나 있습니다.
번들은 이름으로 찾으므로 그대로 두면 영영 못 찾습니다 — 넣을 때 텁니다.

들어 보려면 `python tools/voxout.py` 로 `export/voice/` 에 뽑습니다
(280개, 폴더 이름에 출처가 붙습니다).

---

## 3. 아틀라스 — 되려 우리 쪽이 낫다

'정품 2배 아틀라스로 바꾼다'로 잡아 두었는데, 재 보니 **거꾸로**였습니다.

| 아틀라스 | 우리 | 5.1.0 |
|---|---|---|
| `Atlas_CarIcon` | **2048×1024** | 1024×512 |
| `Atlas_Cutin` | **1024×1024** | 1024×512 |
| `Atlas_EventPop` | **2048×1024** | 1024×1024 |
| `Atlas_InGame` | 1024×1024 | 1024×1024 |

우리 2배 판은 한국 **초기판(8.apk, 2013)** 의 진짜 2배 원화에서 왔습니다
(`docs/HIRES.md`). 5.1.0 의 아틀라스는 작은 쪽이라 바꾸면 나빠집니다.
5.1.0 에만 있는 `Atlas_Dialog` · `Atlas_MainMenu` · `Atlas_TItle` ·
`Atlas_Gradationsprite` 는 우리 빌드에 그것을 쓰는 코드가 없습니다.

**다만 `Atlas_Cutin` 은 다릅니다.** 크기는 우리가 크지만 **장수가 모자랍니다.**

```
우리    PtCutinC1 ~ C4      (4장)
5.1.0   PtCutinC1 ~ C14     (14장)
```

`Cutin::SetCutin(type)` 은 `driverCutin[type]` 만 켜고 나머지를 끕니다.
우리 배열은 넷이라 **컷인 갈래 4~11 은 그림이 아예 안 나왔습니다.** 초기판에도
넷뿐이고(2013), 5.0.1 이 열둘, 5.1.0 이 열넷입니다.

`tools/cutin5.py` 가 열 장을 옮기고 프리팹의 `driverCutin` 배열을 열넷으로
늘렸습니다. 판은 1024×1024 → **2048×512** 로 다시 담았습니다 — 넓이가 같아
`sharedassets1.assets` 도 조각(`.splitN`) 수도 그대로입니다. 우리 넉 장은
2배 그대로 두고 새로 온 열 장은 원본 크기(247×96)로 넣습니다. 이 컷인들은
전부 `Simple` 스프라이트라 위젯 크기로 그려지므로, 정식판이 보여 주던 것과
똑같이 보이고 우리 넉 장만 더 또렷합니다.

`level0` 을 다시 쓸 때 **오브젝트 표를 pathID 오름차순으로** 적어야 합니다.
자료 순서로 적었더니 레이스 장면을 읽다가 앱이 그냥 죽었습니다(실기).

---

## 4. 맵 조각 — 가져올 것이 없다 (헛짚었던 자리)

처음에는 **번들**만 보고 "5.1.0 에 조각 열둘이 더 있다"고 적었습니다.
틀렸습니다. 조각은 두 군데에서 옵니다.

```
ResourceByOption::Load(name)
    1. __ChaMapHook(name)        Background/… 이면 **번들에서** 찾는다 ← 먼저
    2. __ChaResLoad(name_low)    Resources 먼저, 없으면 번들
    3. __ChaResLoad(name)
```

우리 번들에 든 29개는 이 프로젝트가 **더 넣은** 것(`b*` 16 · `g*` 13)이고,
중국판 자신의 조각은 **APK 의 Resources** 에 따로 있습니다.

```
Prefabs/Background         field · beach · bridge · city · sand + tunnel01~03
Prefabs/Background_Hurdle  bfield · bbeach · bbridge · bcity · sand + btunnel01~03
```

중국판 Resources 를 실제로 세어 보면 `field01·02 · beach01·02 · bridge01·02 ·
city01·02 · sand01·02·03 · tunnel01·02·03 · check` 가 **전부 있습니다.**
즉 빈 테마는 없었고, 5.1.0 이 더 주는 조각도 없습니다(이름이 같은 같은 자산).

한 번 옮겨 넣어 봤다가 되돌렸습니다. `__ChaMapHook` 이 **번들을 먼저** 보므로,
넣으면 중국판 자신의 조각을 5.1.0 것으로 **덮어쓰게** 됩니다 — 얻는 것 없이
바꾸는 셈이라 뺐습니다.

곁들여 빌드의 구멍을 하나 막았습니다. `chatool._newer` 가 시각만 보고 있어서,
backup 에서 **되돌린**(시각이 더 옛것인) 번들을 APK 에 다시 안 담았습니다.
이제 크기가 다르면 시각과 무관하게 담습니다.

---

## 붙이는 차례 (`tools/bundlechain.py`)

`packadd` 는 이미 구운 번들에 **얹는** 도구입니다. 처음부터 다시 굽는 길은
없습니다(공여판 트리를 저장소에 담아 둘 수 없어 걷어냈습니다). 그래서 얹는
도구는 저마다 "손대기 전"으로 되돌린 뒤 자기 것을 붙입니다 — 두 번 돌려도
두 번 붙지 않도록. 되돌릴 자리가 하나면 **뒷사람이 앞사람 것을 지웁니다.**
그래서 단계마다 자리를 따로 둡니다.

```
bundle       손대기 전 원본
bundle5      addcars5   정품 차 8대
bundlevox    addvox5    보이스 3명
bundletroy   addtroy    트로이            ← 맨 뒤
```

아틀라스도 마찬가지입니다 — `backup/atlas`(원본) → `backup/atlas5`(carsicon)
→ `troyicon`.

```
python tools/addcars5.py     정품 차 8대 + 차 표 + 서버 표
python tools/carsicon.py     아크엔젤 · W3 · 블리츠 아이콘
python tools/addvox5.py      보이스 세 벌
python tools/cutin5.py       컷인 열 장 (아틀라스 · level0)
sh scripts/builddll.sh       DLL 고침 사슬
python tools/chatool.py build --mode local
```

## 7. 트로이를 제자리로 (`tools/addtroy.py`)

18번은 **로이**의 자리였다. 정식 차 표(37대)를 들여오며 임자가 돌아왔으므로
트로이는 표 뒤의 빈 번호로 옮겼다.

    CarIndex 37 · 서버 carNo 38 · C급 · 트로피 15

붙이는 차례에서 **맨 뒤**다(`bundlechain` 의 `bundletroy`). 아이콘도
`carsicon` 뒤에 이어 붙는다(`backup/atlas5` → `troyicon`).

실기 확인: 자동차 샵에 뜨고, 사서 3474 m 를 달렸고, **점프해도 모델이
갈라지지 않는다**(예전에 뼈 차례가 어긋나 몸통만 길에 남던 자리다).

---

## 8. 주간순위를 초기판 데모 자료로

초기판 `LOBBY_ATLAS` 에 로비 화면이 통째로 **그림으로** 그려져 있고, 그
주간순위에 개발 당시 이름과 기록이 박혀 있다(픽셀이라 문자열 검색으로는
안 잡힌다).

    1 한지윤 25345M   2 김호근 1345M   3 하흥희 1145M
    4 신용석   945M   5 차요한  745M

그대로 `chacnserver.RIVALS` 에 옮겼다. 단위는 그때 **거리(M)** 였고 지금은
**점수**라 숫자만 가져왔다. 한 판이 1~2만 점이라 2~5등은 곧 제치고 1등을
쫓게 된다 — 주행 중 오른쪽 위 '다음목표'가 6 → 5 로 줄어드는 것을 실기로
확인했다. 예전에는 꼴찌가 8만 점이라 영영 6등에 멈춰 있었다.

**프로필 사진은 접었다.** `imageUrl` 을 채우는 곳은
`CRSystem::SetDefaultRankData` 뿐이고 거기서 **소셜 친구 정보만** 본다 —
응답 JSON 에 넣어 줘도 안 읽는다. 그 메서드에 IL 을 덧대 보았으나
`localfix` 끝자리 · `rankfix` 블록 **두 번 다 모노 JIT 이 죽었다**(네이티브
크래시). 얻는 것에 비해 위험이 커서 이름과 기록만 살렸다. 그림은
`tools/rankphoto.py` 로 `export/rank/` 에 뽑아 볼 수 있다.

---

## 남은 것

없다. 1~5번과 트로이까지 다 들어갔다.

---

## 5. 유실 확인 — 포마 · 보스 모드 · 드라이버 넷

### 포마(Poma) — 이름만 남았다

한국 **7.7.0**(`_scratch/kr77`) 문자열표에 `CarName_Poma = 포마` 한 줄이
있다. 그게 전부다. 모델도 아이콘도 수치도 없다.

7.7.0 은 차를 **전부 내려받는** 구조로 바뀌었다. APK 안 `car/` 에 든 것은
`car_01`~`car_11` 열한 칸뿐이고, 열어 보면 세단 · 버스 · 택시 · 소방차 ·
군용트럭 같은 **교통 차량**이다(`enemy_bus` 등과 짝). `database/cardatabase`
도 알맹이 없는 GameObject 껍데기다.

7.7.0 에만 있는 후기 차 열넷 — 포마 · 포니 · 새턴 · 머큐리 · 팬텀 ·
스트라이커 · 육공이 · 나폴리 · 스파이카 · 파이로매니악 · 지미 · 엑시아 ·
아이카 · 주피터. 이 중 살아남은 그림은 아이콘 한 조각(`Pony_A_00`)뿐이다.

가진 트리 여섯(x77 · x77o · 초기판 · 5.0.1 · 5.1.0 · 7.7.0)을 전수로 훑은
결과다.

### 보스 모드 — 코드는 7.7.0 에 통째로 있다

우리 빌드(중국 7.7 바탕)에는 **클래스 0개 · 자원 0개**, 문자열 한 줄
(`CarName_Boss = 보스`)뿐이다. 한국 7.7.0 에는 다 있다.

```
BossEnemyManager   BossData   BossDataBase   BossTimer
BossSkillBasic     BossSkillFireWall   BossSkillLaser
BossAppearCutin    BossResultCutin     BossUnlockNoticePop
```

자원도 0.47 MB 남아 있다 — 방패 · 화염벽 · 김치전 파 · 막걸리 ·
DANGER 글자 · 위험등, 그리고 `car/bossenemymanager` 프리팹.
문자열도 보스 모드 · 보스퇴치점수 · 보스순위 · 히든 보스 포인트가 있다.

**다만 보스 정의 표(`BossDataBase` 알맹이)는 서버가 내려주던 것이라 없다.**
옮겨 오려면 (1) 클래스 열 남짓을 우리 DLL 로 이식하고 (2) 그 표를 우리
사설 서버가 지어내야 한다. 7.7.0 의 `Assembly-CSharp` 은 1.45 MB 로 우리
것(1.10 MB)과 사이가 멀어, 작은 패치로 될 일이 아니다.

### 드라이버 넷의 보이스

| | 보이스 | 컷인 |
|---|---|---|
| 나정비(Char9) | **있다** — 5.1.0 에서 20줄 | **있다** — `PtCutinC13` |
| 안별이(Char10) | **있다** — 5.1.0 에서 20줄 | **있다** — `PtCutinC14` |
| 쌈바여인(Char11) | **없다** | **없다** |
| 한이 가희(Char12) | **없다** | **없다** |

쌈바여인 · 한이 가희는 7.7.0 때 붙은 자리인데, 7.7.0 은 보이스도 전부
내려받아 APK 안 VOX 색인이 **0줄**이다. 컷인 그림도 마찬가지다.

---

## 6. 고친 것 셋

### 로보카 차로 달리면 BGM 이 안 나오던 것 (`patch/robotbgm.cs`)

```
Player::GameStart   if (baseData.robot == null) bgmSound.Play();
```

변신 차(헬리 · 폴리 · 엠버 · 로이)는 무대 BGM 을 **일부러 건너뛴다.**
정식 5.1.0 을 보면 그 자리에 짝이 있다.

```
Player::SetPlayBGM(on)
    if (robot == null) mainBgmSound[playLevel].Play();
    else               robocaBGMSound.Play();
```

로보카 차는 자기 테마를 틀었던 것인데, 중국판이 로보카 차를 들어내면서
`robocaBGMSound` 필드째 사라지고 가드만 남았다. 그래서 아무것도 안 울린다.

그 테마는 아직 있다 — 공여판 번들의 `Roboca_BGM`(1.46 MB, MP3). 필드를 새로
만들지 않고 **있는 `bgmSound` 의 클립만 갈아 끼운다.** 볼륨 · 루프를 그대로
물려받는다. 못 찾으면 무대 BGM 이 나온다.

곁들여 `addcars5.retire_helly` 가 헬리를 갈아 끼울 때 `car/helly/sound/*`
여섯 줄은 **안 물리도록** 고쳤다. 그 안에 이 테마가 있다.

### 드라이버 9~12 의 컷인이 전부 나정비로 나오던 것 (`patch/drivercutin.cs`)

`Player::_GetCutinModel` 의 스위치에 가지가 여덟뿐이라 드라이버 9~12 가
전부 기본값 12 로 떨어졌다. 컷인이 넷뿐이던 때는 12가 배열 밖이라 아무것도
안 나왔는데, 배열을 열넷으로 늘리면서 12가 **나정비** 자리가 되었다.

  · `eCutinModelType` 에 NAJUNGBI(12) · AHNBYULE(13) 을 더한다.
    이름이 있어야 보이스도 탄다 — `Cutin::SetVoiceAudioClip` 이
    `"Character VOX/" + 열거자이름 + …` 으로 경로를 짓는다.
  · 스위치를 열가지로 늘려 Driver_9 → 12 · Driver_10 → 13.
  · **기본값을 12 → 14 로.** 안 그러면 짝 없는 드라이버가 여전히 나정비를
    뒤집어쓴다. 14 는 배열 밖이라 아무 컷인도 안 뜬다.
  · `eDriverType` 도 Driver_9~12 로 넓혔다.

쌈바여인 · 한이 가희는 그림이 없으므로 **빈 판**으로 뜬다. 남의 얼굴을
뒤집어쓰는 것보다 낫다고 보았다. 둘을 목록에서 아예 감추려면 서버의
`DRIVER_COUNT` 를 10 으로 내리면 된다.

### 값을 못 치러도 사지던 것 (`tools/chacnserver.py`)

서버가 **조용히 안 주면서 성공을 돌려줬다.** 클라이언트는 그 말을 믿고
카드를 '장착중'으로 바꾼다 — 새로고침해야 원래대로 돌아온다. 그래서
'트로피가 모자라도 그냥 사진다'로 보였다.

`ep_buycharacter` 와 `_getcar`(차 구매 · 해금)가 못 산 경우
`success=False` · `errorCode` 를 돌려주도록 고쳤다. 클라이언트에는
`BuyDriverFailServer` 가지가 이미 있다.

캐릭터는 트로피가 모자라면 **골드로 받는 길**이 일부러 열려 있다
(트로피 1 = 500골드). 예전에 넣은 편의라 그대로 두었다.
