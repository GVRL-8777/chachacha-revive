# 되살리는 법

작업 트리(`x77/`)는 136MB 라 통째로 넣지 않았다. 대신 기준 APK 와
그와 다른 62개 파일만 넣어 두었다. 디스크가 거의 차 있으니 그대로 두는 게 낫다.

```sh
mkdir -p x77 && cd x77 && unzip -o ../base.apk && cd ..
git checkout -- $(cat x77_changed.txt)      # 변경분 덮어쓰기
```

`survey/` `kr/` `gogo142/` 는 다른 배포판을 푼 것이라 넣지 않았다.
원본 APK 는 `chapaths.py` 가 찾는다 — `CHA_APK_DIR` 환경변수, `apk/`,
저장소 폴더, 그 부모 순. `python chapaths.py` 로 무엇이 있는지 본다.

## 빌드 순서

```sh
sh builddll.sh                       # tunnelfix -> notutorial -> x77
python sfmerge.py pack.dat cha @packspec.txt
python derename.py pack.dat
python mkbundle.py bundles/pack.unity3d pack.dat
python pack.py base.apk chacn.apk x77
python setappname.py chacn.apk chacn_ko.apk 一起车车车 "다함께 차차차"
jarsigner -keystore test.keystore -storepass android -keypass android chacn_ko.apk test
adb install -r --bypass-low-target-sdk-block chacn_ko.apk
```

서버는 `sh relaunch2.sh` 하나로 다시 만들고 띄운다
(`makecnserver.py` -> `cnpatch.py` -> `carfix.py` -> 실행).
**서버 코드를 고칠 때는 `chacnserver.py` 가 아니라 `carfix.py` 를 고쳐야 한다.**
그 파일은 매번 새로 만들어지므로 직접 고치면 다음 실행에 사라진다.

## 한국어화 도구

| 파일 | 하는 일 |
|---|---|
| `korean_res.py` | 시작 화면(360手机助手) · 런처 아이콘 |
| `krtitle.py` | 타이틀 로고 一起车车车 -> 다함께 차차차 |
| `notutorial.cs` | 중국판 전용 도움말 팝업 4개 끄기 |
| `setappname.py` | resources.arsc 의 앱 이름 |

## 상태 파일과 런처

서버로 갈 데이터는 전부 `chastate.json` 하나에 들어 있다.
골드·트로피·타이어, 보유 자동차와 등급·튜닝, 드라이버, 아이템, 스킬,
초대 횟수, 휴면 일수, 수신함, 공지사항, 스위치까지.

```sh
python chalauncher.py              # http://localhost:8080 에서 편집
python chalauncher.py 0.0.0.0      # 같은 망의 다른 기기에서도
```

서버는 켜질 때 이 파일을 읽고, 값이 바뀌면 바로 되쓴다.
런처로 파일을 고치면 **서버를 껐다 켤 필요 없이** 다음 요청부터 반영된다
(앱은 다시 켜야 새 값을 받아 간다).
나중에 오라클로 옮기면 이 파일이 그대로 계정 하나의 저장 내용이 된다.
