#!/bin/sh
# 지정한 터널 세트로 한 판 달리며 8장을 찍는다. 사용법: sh racecheck.sh <세트번호> <꼬리표>
# scripts/ 안에 있지만 일감은 저장소 뿌리에서 돕니다
: "${CHA_URL:?PC 서버 주소를 알려 주세요 — 예: export CHA_URL=http://192.168.0.100:8888}"

cd "$(dirname "$0")/.."
# 원본 APK 자리는 chapaths 가 찾습니다 (CHA_APK_DIR 로 덮어쓸 수 있습니다)
CN_APK="${CN_APK:-$(python -c 'import chapaths;print(chapaths.apk("cn"))')}"
CHA_TUNNEL="$1" ./patchcn.exe mgcn/Assembly-CSharp.dll ACCN.dll mgcnr 300 server random >/dev/null 2>&1
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
sleep 68
adb shell input tap 303 67;  sleep 4          # 어느 화면이든 홈으로
adb shell input tap 1169 398; sleep 4         # 주간랭킹 팝업 닫기
adb shell input tap 1690 984; sleep 20        # 준비하기
adb shell input tap 1690 954; sleep 22        # 게임 시작
for k in 1 2 3 4 5 6 7 8; do adb exec-out screencap -p > "rk_${2}_${k}.png"; sleep 7; done
python -c "
from PIL import Image
ims=[Image.open('rk_${2}_%d.png'%k).resize((240,108)) for k in range(1,9)]
out=Image.new('RGB',(240*8,108))
for k,i in enumerate(ims): out.paste(i,(k*240,0))
out.save('rkrow_${2}.png')"
echo "${2} 완료 / 터널: $(adb logcat -d 2>&1 | grep -aoE '터널 세트: [a-z0-9]*' | head -1)"
