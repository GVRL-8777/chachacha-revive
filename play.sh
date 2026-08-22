#!/bin/sh
# 약관 -> 카카오 취소 -> 게스트 로그인 -> 확인 까지 자동 진행
adb logcat -c
adb shell monkey -p com.cjenm.chachacha -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
sleep 26
adb shell input tap 240 859;  sleep 1
adb shell input tap 1203 859; sleep 1
adb shell input tap 1165 997; sleep 20
adb shell input keyevent 4;   sleep 9
adb shell input tap 629 917;  sleep 5
adb shell input tap 995 707;  sleep 22
