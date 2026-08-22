#!/bin/sh
# 이식한 테마 11종을 하나씩 시작 맵으로 고정해 주행 화면을 찍는다.
# 어느 테마의 지형이 비어 보이는지 눈으로 가려내기 위한 것이다.
# scripts/ 안에 있지만 일감은 저장소 뿌리에서 돕니다
cd "$(dirname "$0")/.."
# 원본 APK 자리는 chapaths 가 찾습니다 (CHA_APK_DIR 로 덮어쓸 수 있습니다)
CN_APK="${CN_APK:-$(python -c 'import chapaths;print(chapaths.apk("cn"))')}"
NAMES="gbeach gbridge gcity gcliff gaqua bbeach bbridge bcity bfield bsand aqua"
i=0
for n in $NAMES; do
  ./patchcn.exe mgcn/Assembly-CSharp.dll ACCN.dll mgcnr 300 server "$i" >/dev/null 2>&1
  python tools/buildapk.py "$CN_APK" chacn.apk \
    --url "http://192.168.0.10:8888" \
    --orig "http://chachacha-server.wanyo.cn" --orig "https://chachacha-server.wanyo.cn" \
    --dll ACCN.dll --ue UECN.dll --overlay overlay >/dev/null 2>&1
  jarsigner -keystore test.keystore -storepass android -keypass android chacn.apk test >/dev/null 2>&1
  adb install -r --bypass-low-target-sdk-block chacn.apk >/dev/null 2>&1
  adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1
  adb shell am force-stop com.cjenm.chachacharevive
  sleep 3
  adb shell am start -n com.cjenm.chachacharevive/com.cjenm.chachachacn.CustomUnityPlayerActivity >/dev/null 2>&1
  sleep 66
  adb shell input tap 1169 398; sleep 4
  adb shell input tap 1690 984; sleep 20
  adb shell input tap 1690 954; sleep 24
  adb exec-out screencap -p > "sweep_${i}_${n}_a.png"
  sleep 16
  adb exec-out screencap -p > "sweep_${i}_${n}_b.png"
  echo "$i $n 완료"
  i=$((i+1))
done
echo "전체 완료"
