# `tools/` — 런처 · 서버 · 빌드 도구

이 게임을 되살리는 데 **실제로 쓰는** 프로그램들입니다. 세이브를 고치고,
APK 를 굽고, 자산을 뽑고 넣고, 사설 서버를 띄웁니다.

서로를 불러 쓰기 때문에 한 폴더에 함께 둡니다. **명령은 저장소 뿌리에서**
실행하세요. 도구들은 뿌리를 작업 폴더로 보고 `x77/` · `saves/` · `lang/` 을
찾습니다.

```
python tools/chatool.py          브라우저 런처 (여기서 거의 다 됩니다)
python tools/chapaths.py         원본 APK 가 어디 있는지 확인
```

---

## 담긴 파일 103개

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
| `cardb.py` | 빌드에서 CarDataBase 를 읽어 옵니다 (TextAsset 안의 JSON). |
| `carprice.py` | CarDataBase 안의 차 한 대 값을 고칩니다. |
| `trimcars.py` | CarDataBase 에서 **모델이 없는 차**를 지운다. |
| `chadrv.py` | 드라이버 프로필 — 초상화 · 이름 · 능력 · 값 · 보이스. |
| `drvprice.py` | 캐릭터(드라이버) 값을 프리팹에서 읽어 옵니다. |
| `drvfont.py` | 드라이버 선택 창의 능력 설명 글자 크기를 줄입니다. |
| `chaskill.py` | 스킬 표 — `DataBase/SkillDataBase` 를 읽습니다. |
| `voicefix.py` | 기본 드라이버 4명의 보이스를 딴 판의 것으로 갈아 끼웁니다. |
| `titlevoice.py` | 타이틀 로고 보이스('다함께 차차차!')를 한국어로 바꿉니다. |

### 한글화

| 파일 | 하는 일 |
|---|---|
| `mkkorean.py` | 한국어 문자열표를 만들어 중국판 자산에 써 넣는다. |
| `krtext.py` | tb_systemtext 의 문구를 **길이를 지키며** 바꾼다. |
| `krtitle.py` | 타이틀 로고를 한국판 것으로 바꾼다. |
| `korean_res.py` | 중국 배포판에만 있는 중국어 이미지를 한국판 것으로 바꾼다. |
| `bakedkr.py` | 프리팹에 **박혀 있는** 중국어 UILabel 을 한국어로 바꾼다. |
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

---

전체 목록은 [`docs/FILES.md`](../docs/FILES.md) 에 있습니다.
