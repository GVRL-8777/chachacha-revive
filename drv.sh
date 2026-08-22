#!/bin/sh
# 드라이버(캐릭터) 목록 화면까지 들어가 위/아래를 각각 찍는다.
set -e
cd "$(dirname "$0")"
adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1
adb shell am force-stop com.cjenm.chachacharevive
sleep 3
adb logcat -c
adb shell am start -n com.cjenm.chachacharevive/com.cjenm.chachachacn.CustomUnityPlayerActivity >/dev/null 2>&1
sleep 64
adb shell input tap 1164 396; sleep 4      # 랭킹 팝업 닫기
adb exec-out screencap -p > d0.png
echo "메인 화면 d0.png"
