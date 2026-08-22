#!/bin/sh
# 이미 설치된 빌드로 한 판 달리며 사진을 찍는다. 사용법: sh race.sh <꼬리표> [장수]
# scripts/ 안에 있지만 일감은 저장소 뿌리에서 돕니다
cd "$(dirname "$0")/.."
TAG="${1:-run}"
N="${2:-10}"
adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1
adb shell am force-stop com.cjenm.chachacharevive
sleep 3
adb logcat -c
adb reverse tcp:8888 tcp:8888 >/dev/null 2>&1
adb shell am start -n com.cjenm.chachacharevive/com.cjenm.chachachacn.CustomUnityPlayerActivity >/dev/null 2>&1
sleep 68
adb shell input tap 1796 146; sleep 3          # 튜토리얼 안내 닫기
adb shell input tap 1796 146; sleep 3
adb shell input tap 303 67;   sleep 4          # 어느 화면이든 홈으로
adb shell input tap 1169 398; sleep 4          # 주간랭킹 팝업 닫기
adb shell input tap 1690 984; sleep 20         # 준비하기
adb shell input tap 1690 954; sleep 22         # 게임 시작
k=1
while [ "$k" -le "$N" ]; do
  adb exec-out screencap -p > "rk_${TAG}_${k}.png"
  sleep 7
  k=$((k + 1))
done
python -c "
from PIL import Image
n=$N
ims=[Image.open('rk_${TAG}_%d.png'%k).resize((240,108)) for k in range(1,n+1)]
cols=5; rows=(n+cols-1)//cols
out=Image.new('RGB',(240*cols,108*rows),(20,20,20))
for k,i in enumerate(ims): out.paste(i,((k%cols)*240,(k//cols)*108))
out.save('rkrow_${TAG}.png'); print('rkrow_${TAG}.png')"
echo "터널: $(adb logcat -d 2>&1 | grep -aoE '터널 세트: [a-z0-9]*' | head -1)"
echo "번들: $(adb logcat -d 2>&1 | grep -acE 'CNBUNDLE|CNMAP') 줄"
