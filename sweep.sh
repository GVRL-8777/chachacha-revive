#!/bin/sh
# 차차차2 계열 APK 전부를 풀어 차차차1 흔적 토큰을 훑는다.
cd "$(dirname "$0")"
out=sweep_result.txt
: > "$out"
# 차차차 2 APK 를 모아 둔 폴더. CHA2_DIR 로 알려 주세요.
CHA2="${CHA2_DIR:-../Cha2}"
for f in "$CHA2"/*.apk; do
  n=$(basename "$f" .apk)
  rm -rf tmpx; mkdir -p tmpx
  unzip -q "$f" "assets/bin/Data/*" -d tmpx 2>/dev/null
  echo "=== $n ===" >> "$out"
  grep -rho --binary-files=text -F -f tokens.txt tmpx/assets/bin/Data 2>/dev/null \
    | sort | uniq -c | sort -rn >> "$out"
  echo "" >> "$out"
  rm -rf tmpx
done
echo "완료" >> "$out"
