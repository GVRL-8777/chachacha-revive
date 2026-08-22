# -*- coding: utf-8 -*-
# 파이썬 단독 사설 서버의 첫 판. 지금은 chacnserver.py 를 쓴다.
"""
다함께 차차차 사설 게임 서버 (파이썬 단독).

catserver.py 는 카탈로그만 내려주고 나머지는 C# 커뮤니티 서버로 넘겼지만,
이 PC 에 .NET SDK 가 없어 그쪽을 고칠 수 없다. 스키마는 이미 DLL 에서 전부 뽑았으므로
(api_schema.txt: NetQuery/NetRecive 의 중첩 eType 열거형 = 각 엔드포인트의 JSON 키 목록)
서버를 파이썬으로 직접 구현한다. Oracle 배포도 이쪽이 간단하다.

전송 규약 (Aes::.ctor / Encrypt / Decrypt 역어셈블로 확인):
  - 로그인 전: application/json 평문
  - 로그인 후: application/crypto+json
      본문 = base64( AES-128-CBC/PKCS7( UTF8(json) ) )
      키/IV = 로그인 응답의 cryptoKey / initialVector 를 base64 디코드한 16바이트

사용법: python chaserver.py [포트] [게임서버URL]
"""
import socketserver, threading, datetime, json, sys, os, base64, secrets, re

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

SP = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(SP, "server.log")
UNIMPL = os.path.join(SP, "unimplemented.log")
SCHEMA = os.path.join(SP, "api_schema.txt")

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
GAME = sys.argv[2] if len(sys.argv) > 2 else "http://192.168.0.10:%d" % PORT

lock = threading.Lock()


def log(m):
    line = "%s  %s" % (datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3], m)
    with lock:
        print(line, flush=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")


# ---------------------------------------------------------------- 카탈로그
# IL(<UpdateResource>c__IteratorBE::MoveNext)로 확정한 구조.
# isCheckingServer 는 불리언, version/loadtype 은 Int32,
# PatchList 는 빈 배열이면 null 취급되어 NRE 가 나므로 더미 1건을 넣는다.
CATALOGUE = {"Catalogue": {
    "ConnectServer": {
        "httpServerIP": GAME, "secureHttpServerIP": GAME,
        "isCheckingServer": False, "SocialUserID": "",
        "alarmMessage": "", "startTime": "", "endTime": "",
        "QuitApplicationWithoutLogout": False,
    },
    "PatchList": [{"resourcename": "dummy", "version": 1, "loadtype": 0}],
}}
CATALOGUE_BODY = json.dumps(CATALOGUE, ensure_ascii=False, separators=(',', ':')).encode()


# ---------------------------------------------------------------- 암복호화
# 로그인 전 요청은 Aes 의 3번째 생성자(키=IV=OSPlatform.GetSystemSecretKey() 앞 16바이트)로
# 암호화되어 온다. 원래는 기기 파생값이라 알 수 없지만 dbhook 이 고정키로 바꿔놨다.
PRELOGIN_KEY = b"ChaChaChaKey2026"


def _dec(blob, key, iv):
    raw = base64.b64decode(blob)
    d = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    plain = d.update(raw) + d.finalize()
    un = padding.PKCS7(128).unpadder()
    return (un.update(plain) + un.finalize()).decode("utf-8")


def _enc(text, key, iv):
    p = padding.PKCS7(128).padder()
    data = p.update(text.encode("utf-8")) + p.finalize()
    e = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return base64.b64encode(e.update(data) + e.finalize()).decode()


class Session(object):
    """로그인 시 발급한 키를 들고 있는다. 단일 사용자 기준."""
    key = None
    iv = None
    account_seq = 1
    token = 1000001

    @classmethod
    def issue(cls):
        cls.key = secrets.token_bytes(16)
        cls.iv = secrets.token_bytes(16)
        return base64.b64encode(cls.key).decode(), base64.b64encode(cls.iv).decode()

    @classmethod
    def candidates(cls):
        """세션 키 먼저, 그다음 로그인 전 고정키."""
        out = []
        if cls.key:
            out.append((cls.key, cls.iv, "session"))
        out.append((PRELOGIN_KEY, PRELOGIN_KEY, "prelogin"))
        return out

    @classmethod
    def decrypt(cls, blob):
        """복호화에 성공한 키를 함께 돌려준다. 응답도 같은 키로 암호화해야 한다."""
        last = None
        for key, iv, tag in cls.candidates():
            try:
                return _dec(blob, key, iv), (key, iv, tag)
            except Exception as e:
                last = e
        raise last

    @staticmethod
    def encrypt(text, keypair):
        key, iv, _ = keypair
        return _enc(text, key, iv)


# ---------------------------------------------------------------- 스키마
TYPES_FILE = os.path.join(SP, "api_types.json")


def load_schema():
    """api_schema.txt -> ({경로: [응답 키(열거형 순서)]}, {경로: NetRecive 클래스명})"""
    if not os.path.exists(SCHEMA):
        return {}, {}
    paths, keys = {}, {}
    cur = None
    for line in open(SCHEMA, encoding="utf-8", errors="replace"):
        m = re.match(r"^### (\S+)(?:\s+PATH (\S+))?", line)
        if m:
            cur = m.group(1)
            if m.group(2):
                paths[cur] = m.group(2)
            continue
        m = re.match(r"^\s+\S+\.eType = (.+)$", line)
        if m and cur:
            keys[cur] = [k.strip() for k in m.group(1).split(",")
                         if k.strip() not in ("Count", "MaxCount")]
    out, cls = {}, {}
    for q, path in paths.items():
        recv = q.replace("NetQuery.", "NetRecive.")
        if recv in keys:
            out[path] = keys[recv]
            cls[path] = recv
    return out, cls


SCHEMA_KEYS, SCHEMA_CLASS = load_schema()
API_TYPES = (json.load(open(TYPES_FILE, encoding="utf-8"))
             if os.path.exists(TYPES_FILE) else {})

# typemap.py 가 IL 에서 뽑은 타입 이름 -> 기본값.
# 배열은 절대 비워두면 안 된다 (JSONObject 가 빈 배열을 null 로 읽어 NRE).
DEFAULTS = {
    "string": "", "int": 0, "long": 0, "float": 0.0, "double": 0.0,
    "bool": False, "object": {}, "array": None,      # array 는 원소를 따로 채운다
    "int[]": [0], "long[]": [0], "double[]": [0.0],
    "string[]": [""], "bool[]": [False],
}


def default_of(t):
    v = DEFAULTS.get(t, 0)
    return dict(v) if isinstance(v, dict) else (list(v) if isinstance(v, list) else v)


# ---------------------------------------------------------------- 엔드포인트
def ep_inspection(req):
    return {"success": True, "errorCode": None, "token": Session.token,
            "ClientFlag": 0}


def ep_login(req):
    key, iv = Session.issue()
    # NetRecive.Login.eType 에 있는 키 전부. 게터가 result 안쪽을 보는지
    # 루트를 보는지 확실하지 않아 양쪽에 동일하게 채운다(여분 키는 무해).
    result = {
        "accountSeq": Session.account_seq,
        "registered": True,
        "takeTrophy": False,
        "newWeek": False,
        "newWeekStart": datetime.datetime.now().strftime("%Y%m%d"),
        "newPresent": False,
        "purchased": False,
    }
    body = {
        "success": True, "errorCode": None, "token": Session.token,
        "cryptoKey": key, "initialVector": iv,
        "blockExpire": "",
        "securityToken": 0,
        "result": result,
        "attend_resultCode": 0, "attend_ivalue": 0,
        "awardYN": False, "presentTypeCd": "",
    }
    body.update(result)
    log("         *** 로그인 발급: key=%s iv=%s" % (key, iv))
    return body


def ep_server_control(req):
    # eType = ..., feature, featureName, isEnable
    # 배열 키(feature) 뒤에 원소 키(featureName/isEnable)가 이어지는 구조.
    # 스칼라로 주면 "feature object is not JSONObject[] type" 경고 후 NRE 가 난다.
    return {
        "success": True, "errorCode": None, "token": Session.token,
        "isRewardStart": False, "isPointUseStart": False,
        "chanceFirstTrophy": 0, "chanceRetryTrophy": 0,
        "AddCarViewFlag": False,
        "feature": [],
    }


# 플레이어 초기 상태. 서버가 권위를 가지는 값이라 여기서 정한다.
PLAYER = {
    "nickName": "Racer",
    "gold": 50000,
    "trophyCnt": 10,
    "tireCnt": 5,
    "carNo": 1,          # CarInfoDB 의 CarIndex
    "carSeq": 1,         # 보유 차량 고유번호
    "carClass": "C",     # eCarClassType
    "characterNo": 1,
}


def ep_user_info(req):
    """NetRecive.UserInfo: info 객체 안에 나머지 49개 키가 들어간다.
       타입은 api_types.json(IL 추출) 그대로, 값만 우리가 정한다."""
    types = API_TYPES.get("NetRecive.UserInfo", {})
    keys = SCHEMA_KEYS.get("/user/info/get/", [])
    info = {}
    for k in keys:
        if k == "info":
            continue
        info[k] = default_of(types.get(k, "int"))
    info.update({
        "nickName": PLAYER["nickName"],
        "pictureUrl": "",
        "gold": PLAYER["gold"],
        "goldAmt": PLAYER["gold"],
        "trophyCnt": PLAYER["trophyCnt"],
        "tireCnt": PLAYER["tireCnt"],
        "tireRemainSecs": 0,
        "carNo": PLAYER["carNo"],
        "carSeq": PLAYER["carSeq"],
        "carClass": PLAYER["carClass"],
        "carAccel": 0, "carSpeed": 0, "carFuleCost": 0,
        "characterNo": PLAYER["characterNo"],
        "randomCharacterNo": 0,
        "canPresent": True,
        "newWeekStart": datetime.datetime.now().strftime("%Y%m%d"),
        "totalRankRewardInit": datetime.datetime.now().strftime("%Y%m%d"),
        "missions": [0],
    })
    return {"success": True, "errorCode": None, "token": Session.token, "info": info}


def ep_car_list(req):
    """HTTP_GetCarList: cars[{carSeq,carNo,carClass,carAccel,carSpeed,carFuleCost,isSelected}]
       빈 배열이면 "cars object is null" 로 NRE 가 난다."""
    return {"success": True, "errorCode": None, "token": Session.token,
            "cars": [{
                "carSeq": PLAYER["carSeq"],
                "carNo": PLAYER["carNo"],
                "carClass": PLAYER["carClass"],
                "carAccel": 0, "carSpeed": 0, "carFuleCost": 0,
                "isSelected": True,
            }]}


def ep_character_list(req):
    """HTTP_GetCharacterList: characters[{characterNo,characterType,isSelected}]"""
    return {"success": True, "errorCode": None, "token": Session.token,
            "characters": [{
                "characterNo": PLAYER["characterNo"],
                "characterType": 0,
                "isSelected": True,
            }]}


ROUTES = {
    "/service/inspection/check/": ep_inspection,
    "/user/auth/login/": ep_login,
    "/setting/control/": ep_server_control,
    "/user/info/get/": ep_user_info,
    "/user/car/list/": ep_car_list,
    "/user/character/list/": ep_character_list,
}


def route(path, req):
    fn = ROUTES.get(path)
    if fn:
        return fn(req)
    # 미구현: 스키마 + IL 에서 뽑은 타입 표로 자동 응답한다.
    #
    # eType 열거형은 거의 항상  success, errorCode, token, <컨테이너>, <컨테이너의 멤버들...>
    # 순서다 (Login=result{...}, ServerEventControl=feature[{...}], UserInfo=info{50개}).
    # 컨테이너인지 여부와 각 필드 타입은 추측이 아니라 api_types.json(IL 추출)에서 가져온다.
    keys = SCHEMA_KEYS.get(path)
    types = API_TYPES.get(SCHEMA_CLASS.get(path, ""), {})
    body = {"success": True, "errorCode": None, "token": Session.token}
    if keys:
        ci = next((i for i, k in enumerate(keys)
                   if types.get(k) in ("object", "array")), None)
        if ci is not None:
            container, members = keys[ci], keys[ci + 1:]
            inner = dict((m, default_of(types.get(m, "int"))) for m in members)
            body[container] = [inner] if types.get(container) == "array" else inner
            for k in keys[:ci]:
                body.setdefault(k, default_of(types.get(k, "int")))
        else:
            for k in keys:
                body.setdefault(k, default_of(types.get(k, "int")))
    with lock:
        with open(UNIMPL, "a", encoding="utf-8") as f:
            f.write("%s  %s  req=%s\n  -> %s\n"
                    % (datetime.datetime.now().strftime("%H:%M:%S"), path,
                       json.dumps(req, ensure_ascii=False)[:400],
                       json.dumps(body, ensure_ascii=False)[:400]))
    log("         [미구현] %s  (스키마 키 %d개로 자동 응답)" % (path, len(keys or [])))
    return body


# ---------------------------------------------------------------- HTTP
class H(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            self.request.settimeout(20)
            data = b""
            while b"\r\n\r\n" not in data and len(data) < 65536:
                c = self.request.recv(4096)
                if not c:
                    break
                data += c
            if not data:
                return
            head, _, rest = data.partition(b"\r\n\r\n")
            lines = head.decode("latin-1").split("\r\n")
            parts = lines[0].split(" ")
            method, target = (parts + ["?", "?"])[:2]
            hdrs = {}
            for l in lines[1:]:
                if ":" in l:
                    k, v = l.split(":", 1)
                    hdrs[k.strip().lower()] = v.strip()
            clen = int(hdrs.get("content-length", "0") or 0)
            body = rest
            while len(body) < clen:
                c = self.request.recv(min(8192, clen - len(body)))
                if not c:
                    break
                body += c

            log("%-5s %s" % (method, target))

            if "AssetCatalogue" in target:
                self.send(CATALOGUE_BODY, "text/plain; charset=utf-8")
                log("         -> AssetCatalogue (httpServerIP=%s)" % GAME)
                return
            if target.endswith(".unity3d"):
                self.send(b"", "application/octet-stream", 404)
                return

            ctype = hdrs.get("content-type", "")
            encrypted = "crypto" in ctype
            keypair = None
            text = body.decode("utf-8", "replace")
            # 헤더가 crypto+json 이어도 본문이 그냥 '{}' 인 경우가 있다(빈 요청은 암호화 안 함).
            # JSON 으로 바로 읽히면 평문으로 취급한다.
            if encrypted and body and not text.lstrip().startswith(("{", "[")):
                try:
                    text, keypair = Session.decrypt(text.strip())
                except Exception as e:
                    log("         [복호화 실패] %s  RAW(%d): %r" % (e, len(body), body[:120]))
                    text = ""
            if text.strip():
                log("         REQ%s: %s"
                    % ("(%s키)" % keypair[2] if keypair else "", text[:400]))
            try:
                req = json.loads(text) if text.strip() else {}
            except Exception:
                req = {}

            path = target.split("?")[0]
            if not path.endswith("/"):
                path += "/"
            resp = route(path, req)
            out = json.dumps(resp, ensure_ascii=False, separators=(',', ':'))
            log("         RES: %s" % out[:300])
            if encrypted and keypair:
                self.send(Session.encrypt(out, keypair).encode(), "application/crypto+json")
            else:
                self.send(out.encode("utf-8"), "application/json")
        except Exception as e:
            log("  [err] %r" % e)
        finally:
            try:
                self.request.close()
            except Exception:
                pass

    def send(self, payload, ctype, code=200):
        self.request.sendall(
            ("HTTP/1.1 %d OK\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
             "Connection: close\r\n\r\n" % (code, ctype, len(payload))).encode()
            + payload)


class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    log("=== 차차차 서버 :%d  (스키마 %d개 경로 로드) ===" % (PORT, len(SCHEMA_KEYS)))
    S(("0.0.0.0", PORT), H).serve_forever()
