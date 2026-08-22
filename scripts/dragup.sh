#!/bin/sh
# 화면을 손가락으로 끌어올린다(목록 스크롤). 사용법: sh dragup.sh <반복횟수>
N="${1:-1}"; i=0
while [ $i -lt $N ]; do
  adb shell input motionevent DOWN 620 220 >/dev/null
  y=260
  while [ $y -le 900 ]; do
    adb shell input motionevent MOVE 620 $y >/dev/null
    y=$((y+80))
  done
  adb shell input motionevent UP 620 900 >/dev/null
  sleep 2
  i=$((i+1))
done
