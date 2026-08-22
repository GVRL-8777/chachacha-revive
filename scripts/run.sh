#!/bin/sh
# 약관 동의 -> 카카오 창이 뜨면 취소 -> 게스트 로그인 -> 확인
PKG=com.cjenm.chachacha
focus() { adb shell dumpsys window 2>/dev/null | grep -oE "mCurrentFocus=[^}]*" | head -1; }

adb shell am force-stop $PKG; sleep 2
adb logcat -c
adb shell monkey -p $PKG -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1

# 약관 화면 대기 (게임에 포커스가 오고 40초 이내)
sleep 34
adb shell input tap 240 859;  sleep 1
adb shell input tap 1203 859; sleep 1
adb shell input tap 1165 997

# 카카오 창이 뜰 때까지 최대 40초 대기 -> 뜨면 즉시 back
i=0
while [ $i -lt 40 ]; do
  if focus | grep -q "com.kakao.talk"; then
    adb shell input keyevent 4
    break
  fi
  sleep 2; i=$((i+2))
done

# 게임으로 포커스가 돌아올 때까지 대기
i=0
while [ $i -lt 30 ]; do
  if focus | grep -q "$PKG"; then break; fi
  sleep 2; i=$((i+2))
done
sleep 6
adb shell input tap 629 917;  sleep 5   # 게스트 로그인
adb shell input tap 995 707            # 확인
sleep 25
