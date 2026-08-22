#!/bin/sh
# 이미 설치된 빌드를 다시 띄워 캐릭터 화면 위/아래를 찍는다(빌드 없음).
set -e
cd "$(dirname "$0")"
adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1
adb shell am force-stop com.cjenm.chachacharevive
sleep 3
adb logcat -c
adb shell am start -n com.cjenm.chachacharevive/com.cjenm.chachachacn.CustomUnityPlayerActivity >/dev/null 2>&1
sleep 64
adb shell input tap 1164 396; sleep 5      # 주간랭킹 팝업 닫기
adb shell input tap 2010 420; sleep 5      # 角色 탭
adb exec-out screencap -p > "${1}_top.png"
for i in 1 2 3 4 5; do adb shell input swipe 700 950 700 250 500; sleep 1; done
sleep 3
adb exec-out screencap -p > "${1}_bot.png"
python -c "
from PIL import Image
for s in ['top','bot']:
    im=Image.open('${1}_%s.png'%s); im.crop((150,0,1300,1080)).resize((690,648)).save('${1}_%ss.png'%s)
"
echo "${1} 촬영 완료 / 예외=$(adb logcat -d 2>&1 | grep -E 'Unity *:' | grep -cE 'Exception')"
