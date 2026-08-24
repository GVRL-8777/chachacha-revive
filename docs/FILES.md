# 파일 하나하나가 하는 일

저장소에 든 305개 파일의 한 줄 요약입니다. 같은 설명이 각 파일 첫머리에도
주석으로 붙어 있고, 이 문서는 거기서 긁어 만듭니다 (`python tools/mkfiles.py`).

---

## `tools/`

런처 · 서버 · 빌드 도구. 서로 부르므로 한자리에 둡니다. **명령은 저장소 뿌리에서** 실행합니다.

### 이 폴더

| 파일 | 하는 일 |
|---|---|
| `README.md` | `tools/` — 런처 · 서버 · 빌드 도구 |

### 런처

| 파일 | 하는 일 |
|---|---|
| `chatool.py` | 차차차 통합 도구 — 세이브 런처 · 자산 뽑기/칠하기/들여오기 · APK 내보내기. |
| `chatool_page.py` | 런처 화면. |
| `chatool_page_assets.py` | 런처 화면의 '자산·모델' 탭. |
| `chatool_assets.py` | 자산 도구의 백엔드. |
| `chabuild.py` | APK 굽기의 **속**. |
| `chasaves.py` | 세이브 파일 살림살이. |
| `chahost.py` | 서버판이 붙을 **주소**를 바꿉니다. |
| `chastate.py` | 서버로 갈 데이터를 **파일 하나**에 담는다. |
| `chaproj.py` | 프로젝트 파일 — 지금까지 만든 것을 한 덩이로 묶습니다. |
| `chalog.py` | 바꾼 내역을 적어 둡니다. |
| `chalang.py` | 화면에 쓰는 **말**. |
| `langkeys.py` | 옮길 말의 열쇠를 긁어모아 `lang/*.json` 에 맞춰 넣습니다. |
| `langcheck.py` | 빌드의 언어를 텍스트 자산으로 판별합니다 (CarName_AVEO 줄을 봅니다). |
| `chapaths.py` | 원본 APK 가 어디 있는지 **스스로 찾습니다.** 예전에는 스크립트마다 `D:/어딘가/CCC_fK_v7.7.0.apk` 처럼 만든 사람의 경로가 박혀 있었습니다. |
| `chapick.py` | 파일·폴더 고르는 창을 띄웁니다. |
| `chalauncher.py` | 차차차 상태 파일을 브라우저에서 고친다. |
| `mkfiles.py` | `docs/FILES.md` — 저장소 파일 하나하나의 한 줄 설명 — 를 다시 만든다. |

### 사설 서버

| 파일 | 하는 일 |
|---|---|
| `chacnserver.py` | 一起车车车 (중국판 5577.com.cjenm.chachachacn) 전용 사설 서버. |
| `mkskel.py` | 사설 서버가 들고 있는 표와 응답 뼈대를 통째로 떠서 C# 쪽에 넘긴다. |

### APK 만들기

| 파일 | 하는 일 |
|---|---|
| `pack.py` | x77/ 작업 트리를 기준 APK 위에 덮어 다시 묶는다. |
| `buildapk.py` | 범용 APK 리패키저. |
| `setappname.py` | resources.arsc 의 문자열 하나를 길이가 달라도 안전하게 바꾼다. |
| `setpkg.py` | APK 의 **패키지 이름**을 바꿉니다. |
| `mkbundle.py` | 유니티 4 용 UnityRaw(무압축) 에셋번들을 만든다. |
| `mkpack.py` | packspec.txt 를 읽어 복원 자산 번들(bundles/pack.unity3d)을 다시 만듭니다. |
| `packadd.py` | 이미 구운 번들에 자산 파일 하나를 **덧붙인다.** 왜 필요한가. |
| `mapspec.py` | 이식할 맵 테마의 sfmerge 스펙과 의존 파일 목록을 만든다. |
| `dump_systemtext.py` | APK 를 푼 폴더에서 `tb_systemtext` 를 텍스트로 꺼낸다. |

### 차 · 드라이버 · 자산

| 파일 | 하는 일 |
|---|---|
| `chaassets.py` | 차차차 자산 도구 — 뽑기 · 다시 칠하기 · 들여오기. |
| `chaanim.py` | 애니메이션 읽기 — 뼈대 · 클립 · 굽기. |
| `chaanimglb.py` | 뼈대와 동작까지 담은 glTF 2.0 (.glb) 내보내기. |
| `newcar.py` | 내 모델을 **새 차로 추가합니다**. |
| `mktaegeuk.py` | 사진 한 장에서 새 자동차 '태극호'를 만들어 넣는다. |
| `carmesh.py` | 새 자동차의 메시를 만든다. |
| `addtaegeuk.py` | 태극호를 게임 데이터에 등록한다. |
| `addhelly.py` | 차량 DB(JSON TextAsset)에 helly(변신 로봇)를 추가하고 다시 자산으로 만든다. |
| `addtroy.py` | 잘려 나간 차 **트로이**를 게임 안에 되살린다. |
| `troyicon.py` | 트로이의 **자동차 샵 아이콘**을 만들어 아틀라스에 넣는다. |
| `addcars5.py` | 한국 정식판 5.1.0 에서 **정품 차 8대**를 지금 빌드로 옮긴다. |
| `carsicon.py` | 아크엔젤 · W3 · 블리츠의 **아이콘**을 5.1.0 아틀라스에서 옮겨 온다. |
| `addvox5.py` | 빠져 있던 **캐릭터 보이스 세 벌**을 5.1.0 에서 옮겨 온다. |
| `bundlechain.py` | 번들에 **차례로 덧붙이는** 도구들이 서로를 지우지 않게 한다. |
| `cardb.py` | 빌드에서 CarDataBase 를 읽어 옵니다 (TextAsset 안의 JSON). |
| `carprice.py` | CarDataBase 안의 차 한 대 값을 고칩니다. |
| `trimcars.py` | CarDataBase 에서 **모델이 없는 차**를 지운다. |
| `chadrv.py` | 드라이버 프로필 — 초상화 · 이름 · 능력 · 값 · 보이스. |
| `drvprice.py` | 캐릭터(드라이버) 값을 프리팹에서 읽어 옵니다. |
| `drvfont.py` | 드라이버 선택 창의 능력 설명 글자 크기를 줄입니다. |
| `chaskill.py` | 스킬 표 — `DataBase/SkillDataBase` 를 읽습니다. |
| `voicefix.py` | 기본 드라이버 4명의 보이스를 딴 판의 것으로 갈아 끼웁니다. |
| `voxout.py` | 드라이버 보이스를 **귀로 들을 수 있게** 파일로 뽑는다. |
| `titlevoice.py` | 타이틀 로고 보이스('다함께 차차차!')를 한국어로 바꿉니다. |

### 한글화

| 파일 | 하는 일 |
|---|---|
| `mkkorean.py` | 한국어 문자열표를 만들어 중국판 자산에 써 넣는다. |
| `krmerge.py` | 게임 안 한국어 표를 **한국 정식판 것으로** 바꾼다. |
| `krtext.py` | tb_systemtext 의 문구를 **길이를 지키며** 바꾼다. |
| `krtitle.py` | 타이틀 로고를 한국판 것으로 바꾼다. |
| `korean_res.py` | 중국 배포판에만 있는 중국어 이미지를 한국판 것으로 바꾼다. |
| `bakedkr.py` | 프리팹에 **박혀 있는** 중국어 UILabel 을 한국어로 바꾼다. |
| `bakedcar.py` | 프리팹에 **박혀 있는** 차 이름을 한국 정식 이름으로 고친다. |
| `bakedtext.py` | 프리팹에 박힌 문구 중 **말이 어긋난 것**을 고친다. |
| `swapfont.py` | 중국판의 동적 폰트를 한글 지원 폰트로 갈아끼운다. |
| `fitlabels.py` | 한글화로 넘치는 UILabel 에 줄바꿈 폭(mMaxLineWidth)을 자동으로 넣는다. |
| `scanwidth.py` | 한글화로 문자열이 얼마나 넓어졌는지 전수 조사한다. |
| `freetext.py` | 차 상점의 값 자리에 뜨는 `Free` 문구를 '무료' 로 줄입니다. |
| `report.py` | 라벨 배치표(labels.json)와 문자열 폭을 결합해 '고칠 목록'을 만든다. |

### UI 프리팹 손질

| 파일 | 하는 일 |
|---|---|
| `activate.py` | 프리팹 안의 특정 GameObject 를 활성 상태로 켠다. |
| `atlasadd.py` | NGUI UIAtlas(MonoBehaviour)에 스프라이트 정의를 추가한다. |
| `uiatlas.py` | NGUI UIAtlas(MonoBehaviour) 원시 바이트에서 스프라이트 표를 읽고 쓴다. |
| `hires.py` | 주행 화면 UI 를 **2배 해상도**로 올린다. |
| `fixatlas.py` | UI 아틀라스의 스프라이트 표를 **올바른 레코드 구조로** 다시 쓴다. |
| `fixatlasref.py` | 복제 카드에서 망가진 아틀라스 참조(fileID)를 되돌린다. |
| `clonecard.py` | 프리팹 안의 서브트리(드라이버 카드)를 통째로 복제한다. |
| `renamecard.py` | 복제한 카드 서브트리의 오브젝트 이름 접두 번호를 바꾼다. |
| `setsprite.py` | 복제한 드라이버 카드의 초상화 스프라이트 이름을 바꾼다. |
| `setsprname.py` | UISprite 의 스프라이트 이름을 pathID 로 지목해 바꾼다(길이 달라도 됨). |
| `setpc.py` | 카드의 초상화 UISprite 이름을 임의로 바꾼다(길이 달라도 됨). |
| `movesprite.py` | 아틀라스의 기존 스프라이트 좌표를 제자리에서 바꾼다(크기 불변). |
| `moveobj.py` | 프리팹 안 GameObject 의 Transform 로컬 위치를 옮긴다. |
| `expandarrays.py` | DriverUnit MonoBehaviour 의 배열 3개를 8칸 -> 12칸으로 늘린다. |
| `fixbuttons.py` | 복제 카드의 버튼 배선을 고친다. |
| `fixclip.py` | 드라이버 목록 패널의 클리핑을 조정해 9~12번 카드가 그려지게 한다. |
| `fixkeys.py` | 복제 카드의 UILocalize 키를 복구하고 9~12번용으로 바꾼다. |
| `fixlabels.py` | 복제 카드 UILabel 의 꼬리 손상을 복구한다. |
| `tradeui.py` | 되팔기 팝업 프리팹의 빈 참조들을 메웁니다. |
| `fixaqua.py` | aqua 테마의 풀 재질이 엉뚱한 것을 셰이더로 물고 있는 것을 고친다. |

### 직렬화 파일 다루기

| 파일 | 하는 일 |
|---|---|
| `sfparse.py` | 유니티 SerializedFile(포맷 9) 정밀 파서. |
| `sfedit.py` | 직렬화 파일 안의 오브젝트 하나를 **길이가 달라져도** 갈아 끼운다. |
| `sfx.py` | Unity 4 SerializedFile 의 외부참조(externals) 를 읽는다. |
| `sfmerge.py` | 여러 직렬화 파일을 **하나의** 번들용 직렬화 파일로 합친다. |
| `sfmerge_new.py` | 여러 직렬화 파일을 **하나의** 번들용 직렬화 파일로 합친다. |
| `sfwrite.py` | 직렬화 파일(포맷 9)에 AssetBundle 매니페스트(classID 142)를 합성해 넣는다. |
| `sfwrite2.py` | AssetBundle 매니페스트를 **pathID 1** 에 놓는 변형. |
| `sfwrite3.py` | 직렬화 파일에 AssetBundle 매니페스트를 넣되, pathID 를 **정확히** 재번호한다. |
| `sfwrite_replay.py` | 직렬화 파일(포맷 9)에 AssetBundle 매니페스트(classID 142)를 합성해 넣는다. |
| `setext.py` | 직렬화 파일의 외부참조표를 통째로 다시 쓴다(이름 길이가 달라도 된다). |
| `fixext.py` | 직렬화 파일의 외부 참조 하나를 다른 파일로 갈아끼우고, 그걸 가리키는 PPtr 을 고친다. |
| `derename.py` | 번들에서 **우리가 이름으로 꺼내 쓸 것만** 남기고 나머지 이름을 비켜 준다. |
| `offset.py` | 이식한 세그먼트의 루트 Transform 위치를 보정한다. |
| `xdeps.py` | 이식 자산의 의존 파일을 **이름 충돌 없이** 옮긴다. |
| `deps.py` | 자산 파일이 참조하는 외부 파일을 재귀로 모아 overlay 폴더에 복사한다. |

### 그림 · 메시 · 셰이더

| 파일 | 하는 일 |
|---|---|
| `progshader.py` | 고정기능 셰이더를 **프로그램 셰이더**로 갈아 끼운다. |
| `setshader.py` | 재질이 가리키는 셰이더를 다른 것으로 갈아 끼운다. |
| `texsettings.py` | 텍스처의 샘플러 설정(필터 · 랩 · 이방성)을 고친다. |
| `uncompress.py` | **DXT 텍스처**를 다른 형식으로 다시 굽는다. |
| `meshuncompress.py` | **압축된 메시**를 풀어서 보통 정점 데이터로 다시 저장한다. |
| `dexegl.py` | 유니티의 **EGL 설정 고르는 코드**를 고친다 (Mali 기기에서 3D 가 검게 나오는 문제). |

### 검사 · 조사

| 파일 | 하는 일 |
|---|---|
| `audit.py` | 이식 자산의 바깥 참조가 실제로 무엇에 닿는지 전수 확인한다. |
| `checkbundle.py` | 이식한 맵 번들에서 **참조가 끊긴 조각**을 찾는다. |
| `checkrefs.py` | 번들 안 맵 조각들의 **외부 참조가 실제로 해석되는지** 검사한다. |
| `conflicts.py` | 이식 자산이 가리키는 의존 자산 중, 중국판 것이 자리를 차지해 버린 것을 찾는다. |
| `sharedusage.py` | 이식 대상이 공여판 sharedassets 의 무엇을 실제로 쓰는지 센다. |
| `sharedone.py` | 맵 루트가 실제로 물고 있는 sharedassets 조각을 따라간다. |
| `analyze.py` | 배포판끼리 같은 이름 자산의 해시를 견줘 무엇이 다른지 본다. |
| `vercmp.py` | 배포판별 빌드 시점과 콘텐츠(차량/맵/캐릭터) 보유 현황을 비교한다. |
| `scanaudio.py` | 트리 안의 AudioClip 을 훑어 이름·길이·크기를 뽑는다. |
| `scansplit.py` | 분할(.splitN) 자산과 level* 까지 붙여서 AudioClip 을 훑습니다. |
| `ildis.py` | 특정 메서드의 IL 을 토큰 해석까지 붙여 출력한다. |
| `ildump.py` | 메서드 하나를 분기 목적지까지 붙여 IL 로 푼다. |
| `ilscan.py` | .NET 어셈블리에서 '메서드별 문자열 리터럴'을 추출한다. |
| `typemap.py` | NetRecive.* 응답 클래스의 "키 -> 타입" 표를 IL 에서 통째로 뽑는다. |
| `mkreport.py` | 조사 결과를 훑어보기 좋은 HTML 문서로 만든다. |

### 그 밖

| 파일 | 하는 일 |
|---|---|
| `cutin5.py` | 빠져 있던 **컷인 그림 열 장**을 5.1.0 에서 옮겨 온다. |
| `rankphoto.py` | 주간순위의 **프로필 사진**을 한국 초기판 데모 화면에서 오려 낸다. |

---

## `patch/`

C# 소스. Cecil 패처와, APK 안에 들어가는 코드입니다.

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
| `pausefix.cs` | 주행 중 일시정지로 나가면 로비 BGM 이 안 나오는 것을 고친다. |
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

### 그 밖

| 파일 | 하는 일 |
|---|---|
| `drivercutin.cs` | 드라이버 9~12 번의 컷인이 **전부 나정비 얼굴**로 나오는 것을 고친다. |
| `robotbgm.cs` | 로보카 차(헬리 · 폴리 · 엠버 · 로이)로 달리면 BGM 이 아예 안 나오는 것을 고친다. |

---

## `scripts/`

`adb` 로 폰을 부리는 잔심부름들. 뿌리에서 `sh scripts/이름.sh` 로 돌립니다.

### 이 폴더

| 파일 | 하는 일 |
|---|---|
| `README.md` | `scripts/` — 폰을 부리는 잔심부름 |

### 빌드

| 파일 | 하는 일 |
|---|---|
| `builddll.sh` | Assembly-CSharp.dll 을 처음부터 다시 만든다. |

### 폰에서 돌려 보기

| 파일 | 하는 일 |
|---|---|
| `run.sh` | 약관 동의 -> 카카오 창이 뜨면 취소 -> 게스트 로그인 -> 확인 |
| `play.sh` | 약관 -> 카카오 취소 -> 게스트 로그인 -> 확인 까지 자동 진행 |
| `runlocal.sh` | 로컬 전용 APK 를 설치하고, **서버를 확실히 없앤 상태로** 띄운다. |
| `relaunch.sh` | 이미 설치된 빌드를 다시 띄워 캐릭터 화면 위/아래를 찍는다(빌드 없음). |
| `relaunch2.sh` | 서버를 새로 띄우고 게임을 다시 시작한다. |

### 사진 찍기

| 파일 | 하는 일 |
|---|---|
| `shot.sh` | 테마 하나를 고정한 빌드를 만들어 설치하고, 레이스 중 화면을 한 장 찍는다. |
| `race.sh` | 이미 설치된 빌드로 한 판 달리며 사진을 찍는다. |
| `racecheck.sh` | 지정한 터널 세트로 한 판 달리며 8장을 찍는다. |
| `drv.sh` | 드라이버(캐릭터) 목록 화면까지 들어가 위/아래를 각각 찍는다. |
| `drvshot.sh` | 빌드 -> 설치 -> 캐릭터 화면 위/아래 촬영 |
| `themesweep.sh` | 이식한 테마 11종을 하나씩 시작 맵으로 고정해 주행 화면을 찍는다. |
| `tunnelsweep.sh` | 이식한 터널 세트 3종을 하나씩 고정해 주행 화면을 찍는다. |
| `tryfiles.sh` | overlay 에 지정한 파일들만 추가로 넣고 빌드/설치/레이스까지 확인한다. |
| `drag.sh` | 실제 손가락처럼 여러 단계로 끌어올린다. |
| `dragup.sh` | 화면을 손가락으로 끌어올린다(목록 스크롤). |

### 조사

| 파일 | 하는 일 |
|---|---|
| `sweep.sh` | 차차차2 계열 APK 전부를 풀어 차차차1 흔적 토큰을 훑는다. |
| `probe_cdn.sh` | 살아 있는 호스트 + 알려진 경로 규칙을 조합해 카탈로그를 찾는다. |

---

## `research/`

자산을 뜯어보며 **한 번 쓰고 만** 스크립트들입니다. 다른 데서 부르지 않으니
안 쓰셔도 되고, 무엇을 어떻게 알아냈는지 궁금하실 때 보시면 됩니다.

| 파일 | 하는 일 |
|---|---|
| `README.md` | `research/` — 한 번 쓰고 만 조사용 스크립트 |
| `_here.py` | 조사용 스크립트가 원본 APK 와 작업 폴더를 **스스로 찾게** 해 준다. |
| `addbundle.py` | 1단계 배선: 번들을 내려받아 AssetBundle.Load 가 실제로 동작하는지 실기에서 확인한다. |
| `addnetq.py` | chacnserver.py 에 NetQuery 패킷 자동 응답을 붙인다. |
| `addportraits.py` | 드라이버 9~12번 초상화를 중국판 UI 아틀라스에 추가한다. |
| `allcars.py` | chacnserver.py 의 차량 목록을 '전 차량 보유' 로 바꾼다. |
| `apkcmp.py` | 여러 APK 의 Unity 버전 / 번들 유무 / 로컬 Resources 경로를 비교한다. |
| `atlascrop.py` | 아틀라스에서 조각을 하나하나 PNG 로 잘라 낸다. |
| `atlasdump.py` | APK 나 작업 트리 안의 NGUI 아틀라스를 통째로 뜯어 표로 적는다. |
| `atlasparse.py` | NGUI UIAtlas(MonoBehaviour)의 스프라이트 목록을 원시 바이트에서 해석한다. |
| `axml.py` | AXML(이진 AndroidManifest.xml)을 사람이 읽을 수 있게 푼다. |
| `bestex.py` | 여러 APK 에서 같은 이름의 Texture2D 중 가장 큰 것을 골라 tex8/ 에 PNG 로 뽑는다. |
| `bgdump.py` | 8.apk 의 Background MonoBehaviour 를 직렬화 규칙대로 직접 읽는다. |
| `buildpatched.py` | 차차차 APK 빌더: 안티탬퍼 프록시 제거 + AssetCatalogue 베이스 URL 리다이렉트. |
| `builtincmp.py` | 중국판과 공여판의 유니티 내장 리소스 파일이 같은 배치를 갖는지 본다. |
| `carfix.py` | chacnserver.py 를 클라이언트 실제 규칙에 맞춘다. |
| `catdump.py` | 공여판 mainData 의 ResourceManager 카탈로그에서 맵 항목을 나열한다. |
| `catserver.py` | AssetCatalogue 를 내려주는 부트스트랩 서버 + 전 요청 로깅. |
| `cha8server.py` | 다함께 차차차 v1.3.1 (8.apk) 전용 사설 서버. |
| `chaserver.py` | 다함께 차차차 사설 게임 서버 (파이썬 단독). |
| `clipcensus.py` | 배포판별 AudioClip 전수 조사. |
| `cnpatch.py` | makecnserver.py 가 만든 chacnserver.py 에 뒤에 붙였던 것들을 다시 얹는다. |
| `deadidx.py` | 중국판 색인에서 '실제로 쓰이지 않는/비어 있는' 항목을 찾는다. |
| `depack.py` | 안티탬퍼 프록시 로더를 걷어내고 정품 Unity/Mono 라이브러리를 lib/ 로 되돌린다. |
| `depchk.py` | 이식한 자산의 의존 파일들이 대상에서 제대로 해석되는지 본다. |
| `dex.py` | DEX 파일 머리와 문자열 표를 직접 읽는다. |
| `diffbase.py` | 작업 트리(x77)에서 기준 APK 와 내용이 다른 파일만 추린다. |
| `diffclone.py` | 복제 카드를 원본 카드(7번)와 4바이트 단위로 대조해 손상을 찾아낸다. |
| `findcontent.py` | 게임 컨텐츠 데이터(차량 스탯/아이템/미션)가 APK 안에 있는지 확인한다. |
| `findhost.py` | APK 전체 엔트리를 훑어 CDN/서버 호스트 문자열이 어디에 박혀 있는지 찾는다. |
| `findobj.py` | 폴더 안 자산을 전부 훑어 이름에 걸리는 오브젝트를 찾는다. |
| `fix_scope.py` | 맵 배선 블록을 번들 블록 안으로 옮긴다 (fBundle 등 지역 변수를 쓰기 위해). |
| `fix_sfmerge.py` | 복원한 원본 sfmerge.py 에 꼭 필요한 두 가지만 다시 얹는다. |
| `fix_sfmerge2.py` | sfmerge.py 에 helly 자산을 담기 위한 두 가지를 더 얹는다. |
| `fixcrlf.py` | 한 번 쓰고 만 수선 스크립트 — 문자열표를 CRLF 로 끝나게 고쳤다. |
| `fixline.py` | 한 번 쓰고 만 수선 스크립트 — 문자열표 항목 사이 빈 줄을 맞췄다. |
| `fixschema.py` | apischema.exe 가 놓치는 컨테이너/배열 타입을 IL 에서 직접 읽어 스키마 JSON 에 보정한다. |
| `fixshader.py` | 이식한 머티리얼의 셰이더 참조를 대상 배포판에 맞게 고친다. |
| `front_theme.py` | 추가한 테마를 배열 맨 앞(index 0)에 놓아 첫 구간부터 보이게 한다. |
| `front_theme2.py` | 추가 테마를 배열 맨 앞(index 0)에 놓는다 — 들여쓰기에 무관하게 줄 단위로 처리. |
| `front_theme3.py` | 복사 루프를 new[i+1] = old[i] 로 고친다. |
| `gen_themes.py` | patchcn.cs 를 테마 1종 -> N종 이식용으로 일반화한다. |
| `gendb.py` | 차차차 컨텐츠 DB 9종 생성기. |
| `hellyspec.py` | gogogoracer 1.4.2 의 helly(변신 로봇 차량) 자산 스펙을 만든다. |
| `hook2.py` | 훅이 gbeach01 뿐 아니라 gbeach02 도 같은 자산으로 돌려주게 한다. |
| `inspect_asset.py` | URL 이 박힌 Unity 에셋의 직렬화 구조를 확인한다 (문자열 = int32 길이 + 바이트 + 4바이트 정렬). |
| `logproxy.py` | 전량 기록용 HTTP 프록시. |
| `makecnserver.py` | cha8server.py 를 바탕으로 중국판 전용 서버 chacnserver.py 를 만든다. |
| `mapchk.py` | 이식 대상 맵 프리팹이 어떤 컴포넌트로 이루어졌는지 본다. |
| `mapspec2.py` | 이식할 맵 테마와 터널의 sfmerge 스펙, 그리고 루트 파일 목록을 만든다. |
| `match.py` | 교체 가능한 (소스 맵 -> CN 맵) 짝을 찾는다. |
| `mbscan.py` | MonoBehaviour 헤더를 직접 읽어 스크립트 클래스로 찾는다. |
| `mbstr.py` | MonoBehaviour 데이터에서 길이 접두 문자열을 훑어 낸다. |
| `mkbundle_replay.py` | 유니티 4 용 UnityRaw(무압축) 에셋번들을 만든다. |
| `mp3check.py` | 뽑아낸 MP3 가 정상 프레임을 갖췄는지 확인하고 대략적인 길이를 계산한다. |
| `netcn.py` | 중국판의 NetQuery/NetRecive 패킷 스키마를 뽑아 netcn.json 으로 저장한다. |
| `netmeta.py` | .NET PE 파일의 메타데이터 스트림을 직접 파싱한다. |
| `patch_ability.py` | PlayerAbility::Init 을 try/catch 로 감싼다. |
| `patch_audio.py` | AudioSource.Play() 널 안전화를 login 모드 전용 블록에서 꺼내 항상 적용되게 한다. |
| `patch_car.py` | ChangePlayerModel 절단 지점 바로 앞에 차량(body) 진단 로그를 심는다. |
| `patch_inv.py` | 도로 텍스처 적용 직후, 씬의 모든 Renderer 와 그 재질/텍스처 유무를 한 번만 찍는다. |
| `patch_layout.py` | sfwrite3.py 의 데이터 배치를 '원본 그대로 + 매니페스트 추가' 로 바꾼다. |
| `patch_tex.py` | dbhook.cs 에 '도로 텍스처를 WWW 로 받아 원본 재질에 붙이는' 패치를 추가한다. |
| `patch_tex2.py` | 텍스처를 정적 캐시에 담고, Background 가 새로 만들어질 때마다 재적용하도록 고친다. |
| `patch_tf.py` | tunnelfix.cs 의 4번 패치를 '번들 이름표' 방식으로 갈아 끼운다. |
| `pathids.py` | 양쪽 맵 자산의 (파일, pathID) 를 대조한다. |
| `resnames.py` | assets/bin/Data 의 해시 이름 파일에서 Unity 오브젝트 이름을 추출한다. |
| `scanbg.py` | 두 APK 의 직렬화 자산에서 이름에 Background/Map 이 들어간 오브젝트를 찾는다. |
| `scanlabels.py` | 중국판 전 자산에서 UILabel/UILocalize 를 훑어 '문구가 어디에 쓰이는지' 표를 만든다. |
| `scanmb.py` | MonoBehaviour 를 스크립트 클래스 이름으로 찾는다 (붙어 있는 GameObject 이름도 함께). |
| `scriptmap.py` | 배포판 간 MonoScript pathID 대응표를 만든다(이름 기준). |
| `seedstate.py` | fitlabels 가 이미 손댄 라벨을 찾아 상태 파일(fit_state.json)을 되살린다. |
| `segcmp.py` | 맵 세그먼트의 트랜스폼과 메시 크기를 배포판 간에 비교한다. |
| `segfull.py` | 세그먼트의 트랜스폼 계층과 메시 바운드를 월드 기준으로 환산해 비교한다. |
| `sf2.py` | SerializedFile(포맷 9) 메타데이터를 정확히 파싱한다. |
| `sfhdr.py` | 유니티 SerializedFile(mainData)의 헤더/테이블 구조를 직접 파싱한다. |
| `sfmerge_replay.py` | 여러 직렬화 파일을 **하나의** 번들용 직렬화 파일로 합친다. |
| `splitassets.py` | 자산 파일을 유니티 안드로이드 빌드의 split 조각으로 쪼개 overlay 에 넣는다. |
| `strings.py` | 이진 파일에서 아스키 문자열을 뽑는다(중복 제거). |
| `survey.py` | APK 들을 훑어 버전/유니티/리소스 목록을 뽑는다. |
| `szcmp.py` | 저장 전후로 오브젝트 페이로드가 보존되는지 바이트 단위로 비교한다. |
| `texcmp.py` | 두 APK 의 Texture2D 를 이름별로 모아 해상도/포맷을 비교한다. |
| `themes.py` | 배포판별 맵 '테마'를 센다. |
| `ttprobe.py` | 오브젝트를 타입트리로 읽고(read_typetree) 다시 쓰기(save_typetree)가 되는지 확인한다. |
| `tunspec.py` | 터널 세트의 sfmerge 스펙과 루트 파일 목록을 만든다. |
| `urlscan.py` | 배포판 자산에서 http(s) URL 을 전부 뽑는다(에셋번들 CDN 주소를 찾기 위해). |
| `vdbg.py` | AudioClip 객체의 실제 필드 구성을 들여다본다. |
| `verify.py` | APK 서명(MANIFEST.MF · CERT.SF)의 해시가 맞는지 검산한다. |
| `voice.py` | 카카오판에서 helly 음성 클립을 찾아 재생 가능한 파일로 뽑는다. |
| `voxscan.py` | 모든 배포판에서 _VOX_ 가 든 AudioClip 을 카탈로그와 무관하게 전수 조사한다. |
| `voxspec.py` | 이식할 보이스 클립의 sfmerge 스펙 목록을 만든다. |
| `wdump.py` | 배포판의 맵 세그먼트 메시 바운드를 한 줄씩 찍는다. |
| `wire_map.py` | 새 맵 테마를 로테이션에 **추가**하는 배선을 patchcn.cs 에 넣는다. |
| `wtest.py` | UnityPy 로 mainData(ResourceManager)를 수정·저장할 수 있는지 검증한다. |
| `xplant.py` | 배포판 사이에 자산을 이식한다 (색인을 건드리지 않는 '파일 교체' 방식). |
| `xtest.py` | mainData 의 externals(외부 파일 참조) 목록을 들여다보고 추가가 가능한지 본다. |

---

## `docs/`

| 문서 | 무엇을 적었나 |
|---|---|
| [`CAPTURE.md`](CAPTURE.md) | 요청 스키마 수집기 (Schema Collector) |
| [`CARS5.md`](CARS5.md) | 한국 정식판 5.1.0 에서 건져 온 것들 |
| [`DORMANT.md`](DORMANT.md) | 묻어 둔 기능들 |
| [`FILES.md`](FILES.md) | 이 문서. 파일 하나하나가 하는 일. |
| [`GPU.md`](GPU.md) | 어떤 폰에서는 3D 가 안 나온다 (Mali · 안드로이드 16) |
| [`HIRES.md`](HIRES.md) | 2배 해상도 UI — 그림은 한국 초기판 것으로 |
| [`LOCALAPK.md`](LOCALAPK.md) | 서버 없는 로컬 전용 APK — 완성 (2026-08-21) |
| [`NEWCAR.md`](NEWCAR.md) | 새 차 추가 — 덮어쓰지 않고 한 대를 늘립니다 |
| [`PRESETS.md`](PRESETS.md) | 판 가르기 — 이제 **세이브 파일**입니다 |
| [`README.md`](README.md) | `docs/` — 연구 기록 |
| [`RESTORE.md`](RESTORE.md) | 되살리는 법 |
| [`TOOL.md`](TOOL.md) | chatool — 다함께 차차차 통합 도구 |
| [`TROY.md`](TROY.md) | 트로이 — 잘려 나간 차를 되살리다 |
| [`VOICE.md`](VOICE.md) | 드라이버 보이스 — 한국어가 들리지 않던 까닭 |

---

## 그 밖

| 파일 | 하는 일 |
|---|---|
| `.gitattributes` | 줄 끝을 LF 로 통일합니다. 셸이 CRLF 로 받아 죽는 것을 막습니다. |
| `.gitignore` | **전부 막고 올릴 것만 여는** 방식의 무시 목록. |
| `LICENSE` | MIT. 다만 게임 자산의 권리는 넷마블 · CJ E&M 에 있습니다. |
| `README.md` | 저장소 안내 — 무엇이 되었고, 어떤 APK 가 필요하고, 어떻게 만드는지. |
| `lang/README.md` | `lang/` — 런처의 말 |
| `lang/en.json` | 런처의 말 — 영어. |
| `lang/kr.json` | 런처의 말 — 한국어. |
| `packspec.txt` | 복원 번들에 담을 자산 목록(원본파일:이름:pathID:보정:평탄화). |
