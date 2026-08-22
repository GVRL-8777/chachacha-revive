#!/bin/sh
# 테마 하나를 고정한 빌드를 만들어 설치하고, 레이스 중 화면을 한 장 찍는다.
# 사용법: sh shot.sh <테마번호> <출력png>
set -e
cd "$(dirname "$0")"
# 원본 APK 자리는 chapaths 가 찾습니다 (CHA_APK_DIR 로 덮어쓸 수 있습니다)
CN_APK="${CN_APK:-$(python -c 'import chapaths;print(chapaths.apk("cn"))')}"
IDX="$1"; OUT="$2"
./patchcn.exe mgcn/Assembly-CSharp.dll ACCN.dll mgcnr 300 server "$IDX" >/dev/null 2>&1
python buildapk.py "$CN_APK" chacn.apk \
  --url "http://192.168.0.10:8888" \
  --orig "http://chachacha-server.wanyo.cn" --orig "https://chachacha-server.wanyo.cn" \
  --dll ACCN.dll --ue UECN.dll --overlay overlay >/dev/null 2>&1
jarsigner -keystore test.keystore -storepass android -keypass android chacn.apk test >/dev/null 2>&1
adb install -r --bypass-low-target-sdk-block chacn.apk >/dev/null 2>&1
# 홈으로 빠져나온 뒤 명시적으로 액티비티를 띄운다(런처 폴더가 열려 있으면 monkey 가 헛돈다)
adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1
adb shell am force-stop com.cjenm.chachacharevive
sleep 3
adb logcat -c
adb shell am start -n com.cjenm.chachacharevive/com.cjenm.chachachacn.CustomUnityPlayerActivity >/dev/null 2>&1
sleep 64
adb shell input tap 1164 396; sleep 3      # 랭킹 팝업 닫기
adb shell input tap 1690 984; sleep 22     # 준비
adb shell input tap 1690 954; sleep 27     # 게임 시작
adb exec-out screencap -p > "$OUT"
echo "$OUT 예외=$(adb logcat -d 2>&1 | grep -E 'Unity *:' | grep -cE 'Exception') 조각=$(adb logcat -d 2>&1 | grep -c '조각 제공') 보이스=$(adb logcat -d 2>&1 | grep -c '번들 성공')"
