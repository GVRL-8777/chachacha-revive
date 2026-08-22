#!/bin/sh
# 서버를 새로 띄우고 게임을 다시 시작한다. 사용법: sh relaunch2.sh [대기초]
# scripts/ 안에 있지만 일감은 저장소 뿌리에서 돕니다
cd "$(dirname "$0")/.."
# 패치가 하나라도 실패하면 멈춘다.
# (예전에 carfix.py 가 죽어도 그냥 진행해 반쪽짜리 서버가 떴다)
set -e
W="${1:-80}"
PYTHONIOENCODING=utf-8 python tools/makecnserver.py >/dev/null 2>&1
PYTHONIOENCODING=utf-8 python tools/cnpatch.py 2>&1 | tail -1
PYTHONIOENCODING=utf-8 python tools/carfix.py 2>&1 | tail -1
# chacnserver.py 를 돌리는 파이썬을 확실히 끝낸다
#  (포트로만 찾으면 옛 서버가 살아남아 예전 코드로 계속 응답한다)
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
        subprocess.run(["taskkill", "/PID", v.strip(), "/F"],
                       capture_output=True)
        print("서버 종료 PID", v.strip())
        cur = {}
PYEOF
sleep 2
rm -f servercn.log
(PYTHONIOENCODING=utf-8 python tools/chacnserver.py 8888 > server_stdout.log 2>&1 &)
sleep 3
adb reverse tcp:8888 tcp:8888 >/dev/null 2>&1
adb shell am force-stop com.cjenm.chachacharevive
sleep 3
adb logcat -c
adb shell am start -n com.cjenm.chachacharevive/com.cjenm.chachachacn.CustomUnityPlayerActivity >/dev/null 2>&1
sleep "$W"
adb exec-out screencap -p > shot.png
adb logcat -d 2>&1 | grep -a "Unity" | grep -a -A3 "Exception" | head -12
