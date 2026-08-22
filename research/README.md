# `research/` — 한 번 쓰고 만 조사용 스크립트

게임 자산이 어떻게 생겼는지 알아내려고 **그때그때 만들어 쓴** 도구들입니다.
지금은 아무 데서도 부르지 않으니 안 쓰셔도 됩니다.

그래도 지우지 않고 둔 까닭은, 무엇을 어떻게 알아냈는지가 여기 남아 있기
때문입니다. 직렬화 파일의 바이트 배치, 배포판 사이의 자산 대응, 죽은 CDN 의
주소가 어디에 박혀 있었는지 — 같은 것을 다시 파려는 분에게는 이쪽이
완성된 도구보다 쓸모 있을 수 있습니다.

---

## 담긴 파일 94개

| 파일 | 하는 일 |
|---|---|
| `_here.py` | 조사용 스크립트가 원본 APK 와 작업 폴더를 **스스로 찾게** 해 준다. |
| `addbundle.py` | 1단계 배선: 번들을 내려받아 AssetBundle.Load 가 실제로 동작하는지 실기에서 확인한다. |
| `addnetq.py` | chacnserver.py 에 NetQuery 패킷 자동 응답을 붙인다. |
| `addportraits.py` | 드라이버 9~12번 초상화를 중국판 UI 아틀라스에 추가한다. |
| `allcars.py` | chacnserver.py 의 차량 목록을 '전 차량 보유' 로 바꾼다. |
| `apkcmp.py` | 여러 APK 의 Unity 버전 / 번들 유무 / 로컬 Resources 경로를 비교한다. |
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

전체 목록은 [`docs/FILES.md`](../docs/FILES.md) 에 있습니다.
