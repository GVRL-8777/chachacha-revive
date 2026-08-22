#!/bin/sh
# 로컬 전용 APK 를 설치하고, **서버를 확실히 없앤 상태로** 띄운다.
#
# 서버가 살아 있으면 "정말 서버 없이 도는가"를 증명할 수 없다. 그래서
#   · chacnserver.py 를 죽이고
#   · adb reverse 를 걷어내
# 폰이 PC 쪽으로 갈 길을 아예 막은 뒤 실행한다.
#
#   sh runlocal.sh [대기초]
cd "$(dirname "$0")"
set -e
W="${1:-60}"

PYTHONIOENCODING=utf-8 python - <<'PYEOF'
import subprocess
o = subprocess.run(["wmic", "process", "where", "name='python.exe'",
                    "get", "ProcessId,CommandLine", "/format:list"],
                   capture_output=True, text=True).stdout
cur = {}
for ln in o.splitlines():
    if "=" not in ln:
        continue
    k, v = ln.split("=", 1)
    cur[k.strip()] = v.strip()
    if k.strip() == "ProcessId" and "chacnserver.py" in cur.get("CommandLine", ""):
        subprocess.run(["taskkill", "/PID", v.strip(), "/F"], capture_output=True)
        print("서버 종료 PID", v.strip())
        cur = {}
print("서버 없음")
PYEOF

adb reverse --remove-all >/dev/null 2>&1 || true
adb install -r --bypass-low-target-sdk-block chacn_local.apk 2>&1 | tail -1
adb shell input keyevent KEYCODE_HOME >/dev/null 2>&1
adb shell am force-stop com.cjenm.chachacharevive
sleep 2
adb logcat -c
adb shell am start -n com.cjenm.chachacharevive/com.cjenm.chachachacn.CustomUnityPlayerActivity >/dev/null 2>&1
sleep "$W"
adb exec-out screencap -p > local.png
echo "--- ChaLocal ---"
adb logcat -d 2>&1 | grep -a "ChaLocal" | head -12
echo "--- 예외 ---"
adb logcat -d 2>&1 | grep -a "Unity" | grep -a -A3 "Exception" | head -20
echo "--- 세이브 ---"
MSYS_NO_PATHCONV=1 adb shell ls -l /storage/emulated/0/Android/data/com.cjenm.chachacharevive/files/ 2>&1 | head
