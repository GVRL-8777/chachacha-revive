#!/bin/sh
# 실제 손가락처럼 여러 단계로 끌어올린다. 사용법: sh drag.sh <반복횟수>
N="${1:-1}"
i=0
while [ $i -lt $N ]; do
  adb shell input motionevent DOWN 620 900 >/dev/null
  y=860
  while [ $y -ge 220 ]; do
    adb shell input motionevent MOVE 620 $y >/dev/null
    y=$((y-80))
  done
  adb shell input motionevent UP 620 220 >/dev/null
  sleep 2
  i=$((i+1))
done
