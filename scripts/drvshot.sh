#!/bin/sh
# 빌드 -> 설치 -> 캐릭터 화면 위/아래 촬영
: "${CHA_URL:?PC 서버 주소를 알려 주세요 — 예: export CHA_URL=http://192.168.0.100:8888}"

set -e
# scripts/ 안에 있지만 일감은 저장소 뿌리에서 돕니다
cd "$(dirname "$0")/.."
# 원본 APK 자리는 chapaths 가 찾습니다 (CHA_APK_DIR 로 덮어쓸 수 있습니다)
CN_APK="${CN_APK:-$(python -c 'import chapaths;print(chapaths.apk("cn"))')}"
python tools/buildapk.py "$CN_APK" chacn.apk \
  --url "$CHA_URL" \
  --orig "http://chachacha-server.wanyo.cn" --orig "https://chachacha-server.wanyo.cn" \
  --dll ACCN.dll --ue UECN.dll --overlay overlay >/dev/null 2>&1
jarsigner -keystore test.keystore -storepass android -keypass android chacn.apk test >/dev/null 2>&1
adb install -r --bypass-low-target-sdk-block chacn.apk >/dev/null 2>&1
adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1
adb shell am force-stop com.cjenm.chachacharevive
sleep 3
adb logcat -c
adb shell am start -n com.cjenm.chachacharevive/com.cjenm.chachachacn.CustomUnityPlayerActivity >/dev/null 2>&1
sleep 64
adb shell input tap 1164 396; sleep 4      # 랭킹 팝업 닫기
adb shell input tap 2010 420; sleep 4      # 角色(캐릭터) 탭
adb exec-out screencap -p > "${1}_top.png"
for i in 1 2 3 4 5; do adb shell input swipe 700 950 700 250 500; sleep 1; done
sleep 3
adb exec-out screencap -p > "${1}_bot.png"
python -c "
from PIL import Image
import sys
for s in ['top','bot']:
    im=Image.open('${1}_%s.png'%s); im.crop((150,0,1300,1080)).resize((690,648)).save('${1}_%ss.png'%s)
"
echo "${1} 촬영 완료 / 예외=$(adb logcat -d 2>&1 | grep -E 'Unity *:' | grep -cE 'Exception')"
