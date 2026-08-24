# 묻어 둔 기능들

살릴 수 있다는 것까지 확인해 놓고 **일부러 덮어 둔** 것들이다.
나중에 꺼내 쓸 때 처음부터 다시 파지 않도록, 어디까지 됐고 무엇이 남았는지 적는다.

배경 분석은 두 문서에 있다.
- 잠들어 있는 네 기능 — 그랑프리 · 전국민 랭킹 · 대전 · 내차고 이벤트
- 증축 노트 — 나머지 잠긴 서버 기능, 그리고 맵·차 만드는 규격

---

## 살려 둔 것

| 기능 | 상태 |
|---|---|
| **자동차 가챠** | 완료. `/shop/car/gacha`. 뽑기 → 결과 팝업 → 재도전 → 확정까지 실기 확인 |
| **장애물(허들) 모드** | 완료. `modesfix.exe hurdle`. 주간순위에 '장애물순위' 탭까지 |
| **차량 되팔기(보상 판매)** | 완료. 내차고 '보상 판매' 탭. 아래 참조 |
| 주간순위 · 지난주 순위 · 초대 · 수신함 · 결제 · 튜닝 · 등급업 · 차량 구매 | 완료 |
| **서버 없는 로컬 전용 APK** | 완료. `chatool build --mode local`. `LOCALAPK.md` |
| **통합 도구 chatool** | 완료. 세이브 런처 + 자산 뽑기/칠하기/들여오기 + 빌드. `TOOL.md` |
| **정식판 자원 복원** | 완료. 차 8대 · 보이스 3벌 · 컷인 10장을 한국 5.1.0 에서. `CARS5.md` |

### 가챠 손댈 곳
`research/carfix.py` 의 `GACHA_CARS` · `GACHA_COST` · `GACHA_RETRY_COST` · `GACHA_ODDS`.
지금 확률은 C 45 / B 30 / A 20 / **S 5** 다. 대상은 CarDataBase 에서
`IsGotyaEvent` 인 6대(사이클론 · 허리케인 · 피닉스 · 헤비수리카 · 슈퍼엠페러 · 썬더).

---

## 되살린 것 — 차량 되팔기 (2026-08-21 완료)

내차고의 **'보상 판매'** 탭에서 헌 차를 넘기고 새 차를 받는다. 실기 확인 완료
(메테오를 받고 헤비수리카를 넘기며 트로피 10 차감).

중국판이 이 기능을 **소스 수준에서 들어내** 세 겹으로 막혀 있었다.
| 막힌 곳 | 증상 | 푼 방법 |
|---|---|---|
| `_IsEnableTradeCar` 가 스위치 AND `EventDataBase.tradeCarDataBase.isEventActive` | 탭 자체가 안 뜸. 이벤트DB 빌더(`_BuildEventTradeCarDataBase`)가 `ret` 하나뿐이라 영영 false | `modesfix.exe` 가 판정함수 본문을 `ldc.i4.1; ret` 로 교체 |
| `TradeCarPop.m_CarList` (Dictionary) 를 **아무 데서도 생성하지 않음**. 생성자가 7바이트 | 팝업 열자마자 `Build()` 첫 `Add` 에서 널참조 | `tradefix.exe` 가 생성자 `ret` 앞에 `newobj Dictionary` 추가 |
| `m_CarClassSprite_SellName/BuyName` 프리팹 참조가 (0,0), `m_TitleName` 은 아예 직렬화 안 됨 | `SetCarNameBoard`·`Build` 에서 널참조 | `tradeui.py` 가 프리팹 PPtr 2곳을 살아 있는 스프라이트로 교체(길이 보존), `tradefix.exe` 가 제목라벨 문장을 IL 에서 제거 |

값은 `research/carfix.py` 의 `TRADE_CLASS_VALUE`(C 0 / B 14 / A 50 / S 120 / R 200) 와
`TRADE_LEVEL_VALUE`(레벨 1~4 → 0 / 5 / 10 / 20)에 있다. 클라이언트는
**같은 등급 줄의 값 + 각 항목이 (레벨+1) 인 줄의 값**을 더한다
(`TradeCarValueDB.GetDiscountTrophy`). 1부터 세는 규칙이 여기도 적용된다.
가격 자체(`originPrice`=120)는 프리팹에 구워져 있다.

## 묻어 둔 것

전부 **자산과 화면은 살아 있고 서버만 없다.** 켜는 법도 안다.

### 그랑프리
- `modesfix.exe grandprix` 로 스위치는 켜진다
- 서버: `/event/grandprix/info`(status · titleName · limitCarNo · myRate) 와
  `/event/grandprix/regist`(remainTrophyCnt)
- **막히는 곳**: 순위표와 시상이 죽은 `netmarble.net` 웹뷰에 있다.
  대회 개최와 점수 등록까지만 재현되고, 순위표는 우리가 웹페이지를 만들어야 한다
- `status` 가 `"004"` 면 종료로 친다

### 전국민 랭킹
- `modesfix.exe globalranking`
- 서버: `/ladder/get/myInfo` · `/ladder/get/myGroup` · `/ladder/reward` ·
  `/ladder/roulette/*`
- **막히는 곳**: 혼자 하는 리그라 그룹·승급·강등이 의미가 없다.
  현물 상품(재고 · 이미지 · 수령인 정보 · 배송)은 재현 대상이 아니다
- 되살린다면 클래스 표시와 카운트다운만 흉내 내는 선

### 1:1 대전
- `modesfix.exe` 에 항목이 없다(스펙 스위치가 아니라 `HTTP_VersusAble` 쪽)
- 서버: `/play/versus/list` · `/giveup` · `/reward` · `/setting/versus/allow`
- **가장 살릴 만하다.** 비동기라 상대가 접속해 있을 필요가 없고,
  `matches[]` 한 줄에 내 기록과 상대 기록이 같이 들어간다.
  주간순위에 심어 둔 라이벌 다섯을 그대로 상대로 쓰면 된다
- 빠지는 것은 카톡 신청 메시지뿐 — 초대 목록을 채운 방식으로 우회 가능

### 내차고 이벤트 탭
- 탭 자체는 이미 보인다. 다만 **`EventCar` 플래그가 켜진 차가 한 대도 없어** 목록이 빈다
- 살리려면 `trimcars.py` 처럼 CarDataBase 에서 몇 대의 `EventCar` 를 켠다
- 이벤트 세일은 `/shop/package/buy` 와 할인가 정의가 필요하다

### 아이템 7종
- **회수가 가장 크다.** 상점에 일곱 칸이 이미 다 보이고 전부 0개다
- 서버: `/shop/item/list`(items[itemCode · itemCount] · toolboxRetryCount ·
  toolboxRebuyGoldAmt) · `/shop/item/buy` · `/shop/item/rebuy` ·
  `/play/item/use` · `/play/item/buyuse`
- 코드 순서: `BestOil · Nos · FrontSensor · ToolBox · OneShot · Emergency · Turbo`
- 강화공구상자는 그 자체가 뽑기다 — `TB_BestOil · TB_Nos · TB_Magnet ·
  TB_DoubleGold · TB_Emergency` 중 하나
- **수량은 이미 `chastate.json` 의 `items` 에 들어 있다.** 서버만 붙이면 된다

### 차량 스킬
- 서버: `/skill/get/list`(skillList[skillNo · carNo · skillLevel · equipFlag ·
  skillType]) · `/skill/buy` · `/skill/equip` · `/skill/upgrade`
- 스킬 정의는 `database/skilldatabase` 에 11.8KB 통째로 있다
- **보유 상태는 이미 `chastate.json` 의 `skills` 에 자리를 잡아 뒀다**

### 드라이버 구매 · 뽑기
- `/shop/character/buy` · `/shop/character/random/buy` · `/user/character/random/select`
- 지금은 `chastate.json` 의 `driversOwned` 가 12명 전원이라 상점 흐름이 죽어 있다.
  몇 명을 빼면 살아난다(자동차 샵과 같은 방식)

### 타이어 선물 보내기 · 휴면 복귀
- `/tire/present/send` · `/setting/present/allow` · `/tire/present/dormancyReward`
- 휴면 일수는 `chastate.json` 의 `dormancy` 에 자리가 있다

---

## 공통 규칙 (다시 팔 때 잊지 말 것)

- **번호는 1부터.** carNo · characterNo · 튜닝 레벨 전부 게터가 1을 뺀다
- 요청 본문은 `{"xxxReq": {...}}` 한 겹 — `unwrap()` 이 벗겨 준다
- 응답은 **그 경로의 스키마로** 만든다. 없는 키를 읽으면 널참조로 죽는다
- 목록이 비면 탭이 그냥 되돌아온다(먹통처럼 보인다)
- 자산과 화면은 거의 다 살아 있다. 없는 것은 **서버와 웹페이지와 다른 사람**뿐이다

---

## 못 살린 것 — 자료가 아예 없다

가진 판 여섯(중국 7.7 · x77o · 한국 초기판 1.2.3 · 정식 5.0.1 · 5.1.0 ·
한국 7.7.0)을 전수로 훑어 확인한 것이다. 자세한 것은 `CARS5.md`.

### 포마(Poma) — 이름만 남았다

한국 7.7.0 문자열표의 `CarName_Poma = 포마` 한 줄이 전부다. 모델도 아이콘도
수치도 없다. 7.7.0 은 차를 **전부 내려받는** 구조라 APK 의 `car/` 에는
교통 차량 열한 칸(`car_01`~`car_11`)만 들어 있고 `database/cardatabase` 도
알맹이 없는 껍데기다.

7.7.0 에만 있는 후기 차 열넷 — 포마 · 포니 · 새턴 · 머큐리 · 팬텀 ·
스트라이커 · 육공이 · 나폴리 · 스파이카 · 파이로매니악 · 지미 · 엑시아 ·
아이카 · 주피터. 살아남은 그림은 아이콘 한 조각(`Pony_A_00`)뿐이다.

### 쌈바여인 · 한이 가희 — 보이스도 컷인도 없다

드라이버 카드는 프리팹에 있어 목록에 뜨고 살 수도 있다. 그런데 보이스는
어느 판에도 없고(7.7.0 은 보이스도 내려받아 APK 안 VOX 색인이 0줄),
컷인 그림도 없다. 지금은 컷인이 **빈 판**으로 뜬다 — 남의 얼굴을
뒤집어쓰는 것보다 낫다고 보았다. 목록에서 감추려면 `DRIVER_COUNT` 를 10 으로.

나정비 · 안별이는 5.1.0 에 다 있어서 옮겨 넣었다(보이스 20줄씩 · 컷인 C13/C14).

## 안 살린 것 — 남아 있지만 손이 크다

### 보스 모드

우리 빌드(중국 7.7 바탕)에는 **클래스도 자원도 0개**, 문자열 한 줄
(`CarName_Boss = 보스`)뿐이다. 한국 7.7.0 에는 다 있다.

```
BossEnemyManager   BossData   BossDataBase   BossTimer
BossSkillBasic     BossSkillFireWall   BossSkillLaser
BossAppearCutin    BossResultCutin     BossUnlockNoticePop
```

자원도 0.47 MB 남아 있다 — 방패 · 화염벽 · 김치전 파 · 막걸리 · DANGER
글자 · 위험등, 그리고 `car/bossenemymanager` 프리팹. 문자열도 보스 모드 ·
보스퇴치점수 · 보스순위 · 히든 보스 포인트가 있다.

**다만 보스 정의 표(`BossDataBase` 알맹이)는 서버가 내려주던 것이라 없다.**
옮겨 오려면 클래스 열 남짓을 우리 DLL 로 이식하고, 그 표를 사설 서버가
지어내야 한다. 7.7.0 의 `Assembly-CSharp` 은 1.45 MB 로 우리 것(1.10 MB)과
사이가 멀어 작은 패치로 될 일이 아니다.

### 주간순위 프로필 사진

초기판 `LOBBY_ATLAS` 에 데모 순위표가 그림으로 박혀 있어 얼굴 다섯 장을
꺼낼 수 있다(`tools/rankphoto.py` → `export/rank/`). 그런데 `imageUrl` 을
채우는 곳은 `CRSystem::SetDefaultRankData` 뿐이고 거기서 **소셜 친구
정보만** 본다 — 응답 JSON 에 넣어 줘도 안 읽는다. 그 메서드에 IL 을 덧대
보았으나 `localfix` 끝자리 · `rankfix` 블록 **두 번 다 모노 JIT 이 죽었다**
(네이티브 크래시). 이름과 기록만 살렸다.

---

## 만들었다가 뺀 것 — 태극호 (자작 차량)

사진 한 장으로 새 S급 차를 만들어 **차고·상점·주행까지 전부 동작**시켰지만,
저폴리곤 손모델링 품질이 게임 원본 차들과 격차가 커서 2026-08-21 에 뺐다.

**남겨 둔 재료** (작업 폴더에 그대로 있다)
- `carmesh.py` — 절차적 차체 생성기 (단면 프로파일 + 바퀴 + 자동 감기 정렬 `_orient()`)
- `mktaegeuk.py` — taegeuk.assets 생성기 (압축 메시 인코딩 · 텍스처 · 프리팹 복제)
- `addtaegeuk.py` — CarDataBase(CarIndex 18)·이름표 등록기
- `taegeuk.assets` — 마지막 빌드 산출물

**되살리는 법** (역순으로 뺐으니 그대로 다시 하면 된다)
1. `python tools/addtaegeuk.py` — CarDataBase 와 이름표 등록 (→ APK 재조립·설치)
2. `packspec.txt` 마지막에 한 줄:
   `taegeuk.assets:car/taegeukho/player_taegeukho_s:11:0:keepscript:also=car/taegeukho/materials/taegeukho@3:also=car/taegeukho/materials/taegeukho_low@3:also=car/taegeukho/taegeukho_low@11:also=car/taegeukho/taegeukho@11:also=car/taegeukho/player_taegeukho_s_low@11:mbptr=26@36:mbptr=26@44`
3. `research/carfix.py` 에 등급 · 값 · `SHOP_CARS` 등록,
   `chastate.py` CARS 에 한 줄

   **번호가 옮겨졌다.** 이 글을 쓸 때는 CarIndex 18 이 비어 있었지만,
   `addcars5.py` 로 정식 차 표(37대)를 들여오면서 18 은 로이의 자리가
   되었다. 지금 빈 번호는 38부터다(37 은 트로이). `chastate.py` 의 CARS 는
   이제 CarDataBase 에서 떠 오므로 손으로 적지 않아도 된다
   (`addcars5.patch_cars_table`).
4. sfmerge → mkbundle → relaunch2

**다시 잡을 때 절대 잊지 말 것** (자세한 건 메모리 문서에)
- 삼각형 감기: 앞면은 바깥쪽. 차고에선 감기가 뒤집혀도 멀쩡해 보인다 —
  **검증은 주행 화면으로.**
- 메시는 원본처럼 m_CompressedMesh 비트팩. 텍스처는 DXT1.
- `ChangeTextureMaterial` 이 재질을 덮어쓴다 → mbptr 재배선 필수.
- 품질을 올리려면: 손으로 단면을 늘리기보다, 원본 차 메시(993정점급)를
  뜯어 개조하거나 외부 모델(obj)을 들여오는 변환기를 만드는 쪽이 낫다.
