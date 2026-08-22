"""
AssetCatalogue 를 내려주는 부트스트랩 서버 + 전 요청 로깅.

IL 분석(<UpdateResource>c__IteratorBE::MoveNext)에서 확인된 카탈로그 키:
  ConnectServer / httpServerIP / secureHttpServerIP / isCheckingServer
  SocialUserID / alarmMessage / startTime / endTime / QuitApplicationWithoutLogout
  PatchList -> resourcename, version, loadtype

LitJSON 은 없는 키를 인덱싱하면 예외가 나므로, 평탄/중첩 양쪽에 모두 채워
어느 레이아웃이든 걸리도록 한다. 남는 키는 무해하다.
"""
import socketserver, threading, datetime, json, sys, os

SP = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(SP, "cat_hits.log")
GAME = (sys.argv[2] if len(sys.argv) > 2
        else os.environ.get("CHA_URL", "http://127.0.0.1:8888"))
lock = threading.Lock()

def log(m):
    line = "%s  %s" % (datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3], m)
    with lock:
        print(line, flush=True)
        open(LOG, "a", encoding="utf-8").write(line + "\n")

# 게임 로그 피드백 반영:
#  - isCheckingServer 는 System.Boolean 이어야 함 (문자열 "N" 거부됨)
#  - PatchList 는 조회 계층이 달라서 모든 딕셔너리에 넣어준다
# --- IL 역어셈블(AssetBundleManager+<UpdateResource>c__IteratorBE::MoveNext)로 확정한 구조 ---
#   root["Catalogue"]                        GetJSONObject
#        ["ConnectServer"]                   GetJSONObject
#             ["httpServerIP"]               GetString
#             ["secureHttpServerIP"]         GetString
#             ["isCheckingServer"]           GetBoolean
#             ["SocialUserID"]               / alarmMessage / startTime / endTime
#             ["QuitApplicationWithoutLogout"]
#        ["PatchList"]                       GetJSONArray  -> resourcename/version/loadtype
#
# JSONObject::GetValue<T> 는 Get(key)==null 이면 경고 후 default(T) 를 돌려주고,
# 호출부가 그 결과를 바로 인덱싱해서 NullReferenceException 이 난다.
# 빈 배열([])은 Get 이 null 을 돌려주므로 항목이 최소 1개 필요하다.
CONNECT_SERVER = {
    "httpServerIP": GAME,
    "secureHttpServerIP": GAME,
    "isCheckingServer": False,
    "SocialUserID": "",
    "alarmMessage": "",
    "startTime": "",
    "endTime": "",
    "QuitApplicationWithoutLogout": False,
}

# version / loadtype 은 Int32 여야 한다 (게임 로그: "not System.Int32 type ... is System.String")
PATCH_LIST = [
    {"resourcename": "dummy", "version": 1, "loadtype": 0},
]

CATALOGUE = {
    "Catalogue": {
        "ConnectServer": CONNECT_SERVER,
        "PatchList": PATCH_LIST,
    }
}

# 파서가 자체 구현(JSONObject)이라 개행/들여쓰기에 취약할 수 있어 공백 없이 직렬화한다.
BODY = json.dumps(CATALOGUE, ensure_ascii=False, separators=(',', ':')).encode()

UPSTREAM = os.environ.get("CHA_UPSTREAM", "http://localhost:8080")


def forward(target, method, body, hdrs):
    """게임 API 요청을 상류 chachacha-server 로 중계한다."""
    import urllib.request, urllib.error
    url = UPSTREAM.rstrip('/') + target
    req = urllib.request.Request(url, data=body or b"", method=method)
    for k in ("content-type", "accept", "appos", "appversion", "packversion"):
        if k in hdrs:
            req.add_header(k, hdrs[k])
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = r.read()
            ct = r.headers.get("Content-Type", "application/json")
        log("         -> upstream %s  %d bytes" % (url, len(data)))
        return data, ct
    except urllib.error.HTTPError as e:
        data = e.read()
        log("         -> upstream HTTP %d (%d bytes)" % (e.code, len(data)))
        return data, e.headers.get("Content-Type", "application/json")
    except Exception as e:
        log("         -> upstream 실패: %s  (최소 성공 응답으로 대체)" % e)
        return b'{"success":true,"errorCode":null,"token":123456789}', "application/json"


class H(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(15)
            data = b""
            while b"\r\n\r\n" not in data and len(data) < 65536:
                c = self.request.recv(4096)
                if not c: break
                data += c
            if not data: return
            head, _, rest = data.partition(b"\r\n\r\n")
            lines = head.decode("latin-1").split("\r\n")
            reqline = lines[0]
            hdrs = {}
            for l in lines[1:]:
                if ":" in l:
                    k, v = l.split(":", 1); hdrs[k.strip().lower()] = v.strip()
            parts = reqline.split(" ")
            method, target = (parts + ["?", "?"])[:2]
            log("%-6s %s" % (method, target))
            interesting = {k: v for k, v in hdrs.items()
                           if k in ("appos", "appversion", "packversion", "content-type", "accept")}
            if interesting: log("         hdr: %s" % interesting)
            clen = int(hdrs.get("content-length", "0") or 0)
            body = rest
            while len(body) < clen:
                c = self.request.recv(min(8192, clen - len(body)))
                if not c: break
                body += c
            if body:
                try: shown = body.decode("utf-8")
                except UnicodeDecodeError: shown = repr(body[:300])
                log("         BODY(%d): %s" % (len(body), shown[:500]))

            if "AssetCatalogue" in target:
                payload, ctype = BODY, "text/plain; charset=utf-8"
                log("         -> AssetCatalogue 반환 (httpServerIP=%s)" % GAME)
            elif UPSTREAM and target.startswith('/') and 'unity3d' not in target:
                # 게임 API 는 실제 서버(chachacha-server)로 포워딩한다.
                # HttpListener 는 비-localhost 바인딩에 관리자 권한이 필요해서,
                # 외부에 노출된 이 파이썬 서버가 중계 역할을 한다.
                payload, ctype = forward(target, method, body, hdrs)
            else:
                payload = b'{"success":true,"errorCode":null,"token":123456789}'
                ctype = "application/json"
            self.request.sendall(
                b"HTTP/1.1 200 OK\r\nContent-Type: " + ctype.encode() +
                b"\r\nContent-Length: " + str(len(payload)).encode() +
                b"\r\nConnection: close\r\n\r\n" + payload)
        except Exception as e:
            log("  [err] %s" % e)
        finally:
            try: self.request.close()
            except Exception: pass

class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True; daemon_threads = True

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    log("=== catalogue 서버 :%d  게임서버=%s ===" % (port, GAME))
    S(("0.0.0.0", port), H).serve_forever()
