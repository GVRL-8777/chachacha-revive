#!/bin/sh
# 이식한 터널 세트 3종을 하나씩 고정해 주행 화면을 찍는다.
# scripts/ 안에 있지만 일감은 저장소 뿌리에서 돕니다
cd "$(dirname "$0")/.."
# 원본 APK 자리는 chapaths 가 찾습니다 (CHA_APK_DIR 로 덮어쓸 수 있습니다)
CN_APK="${CN_APK:-$(python -c 'import chapaths;print(chapaths.apk("cn"))')}"
for i in 1 2 3; do
  case $i in 1) n=gtunnel;; 2) n=btunnel;; 3) n=bftunnel;; esac
  CHA_TUNNEL=$i ./patchcn.exe mgcn/Assembly-CSharp.dll ACCN.dll mgcnr 300 server random >/dev/null 2>&1
  python buildapk.py "$CN_APK" chacn.apk \
    --url "http://192.168.0.10:8888" \
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
  adb shell input tap 1169 398; sleep 4
  adb shell input tap 1690 984; sleep 20
  adb shell input tap 1690 954; sleep 22
  for k in 1 2 3 4 5 6 7 8; do adb exec-out screencap -p > "tun_${i}_${n}_${k}.png"; sleep 7; done
  echo "$i $n 완료 (터널로그: $(adb logcat -d 2>&1 | grep -aoE '터널 세트: [a-z0-9]*' | head -1))"
done
echo "전체 완료"
