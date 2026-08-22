# -*- coding: utf-8 -*-
"""
다함께 차차차 v1.3.1 (8.apk) 전용 사설 서버.

7.7.0 과 달리 이 버전은 CDN/에셋번들이 없고(AssetBundleManager 자체가 없음)
모든 자산이 APK 안에 있다. 서버만 세우면 되는 구조.

스키마는 apischema.exe 가 DLL 에서 뽑은 api8.json 을 그대로 쓴다
(응답 클래스의 중첩 eType 열거형 = JSON 키, 게터 IL = 타입).

경로에 **트레일링 슬래시가 없다** (`/user/auth/login`).

사용법: python cha8server.py [포트]
"""
import socketserver, threading, datetime, json, sys, os, base64, secrets

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

SP = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(SP, "server8.log")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
lock = threading.Lock()

SCHEMA = {}
_p = os.path.join(SP, "api8.json")
if os.path.exists(_p):
    SCHEMA = json.load(open(_p, encoding="utf-8-sig"))

# 경로 -> 응답 클래스
ROUTE_CLASS = {
    "/service/inspection/check": "HTTP_CheckService",
    "/service/notice/get": "HTTP_CheckNotice",
    "/user/auth/login": "HTTP_Login",
    "/user/auth/logout": "HTTP_Logout",
    "/user/auth/withdrawal": "HTTP_WithDrawal",
    "/user/info/get": "HTTP_UserInfo",
    "/user/tire/check": "HTTP_CheckTire",
    "/user/car/list": "HTTP_GetCarList",
    "/user/car/select": "HTTP_SelectCar",
    "/user/car/upgrade": "HTTP_UpgradeCar",
    "/user/car/tune": "HTTP_TuneCar",
    "/user/character/list": "HTTP_GetCharacterList",
    "/user/character/select": "HTTP_SelectCharacter",
    "/user/boast/set": "HTTP_BoastAble",
    "/shop/item/list": "HTTP_GetItemList",
    "/shop/item/buy": "HTTP_BuyItem",
    "/shop/car/buy": "HTTP_BuyCar",
    "/shop/car/unlock": "HTTP_UnlockClass",
    "/shop/car/unlockbuy": "HTTP_UnlockBuy",
    "/shop/character/buy": "HTTP_BuyCharacter",
    "/shop/gold/exchange": "HTTP_ExchangeGold",
    "/shop/tire/exchange": "HTTP_ExchangeTire",
    "/play/game/start": "HTTP_GameStart",
    "/play/game/finish": "HTTP_GameFinish",
    "/play/item/use": "HTTP_UseItem",
    "/ranking/current/list": "HTTP_GetRank",
    "/ranking/previous/list": "HTTP_GetRank",
    "/tire/present/list": "HTTP_GetGiftList",
    "/tire/present/recv": "HTTP_RecvGiftTire",
    "/tire/present/recvAll": "HTTP_RecvAllGiftTire",
    "/tire/present/send": "HTTP_SendGiftTire",
    "/invitation/list": "HTTP_InviteList",
    "/invitation/invite": "HTTP_Invite",
    "/setting/present/allow": "HTTP_AbleGiftSetting",
    "/event/review/complete": "HTTP_Event",
}

# 플레이어 상태 (서버가 권위를 가진다)
PLAYER = {
    "nickName": "Racer", "gold": 50000, "trophyCnt": 10, "tireCnt": 99,
    "carNo": 0, "carSeq": 1, "carClass": "C", "characterNo": 0,
}

DEFAULTS = {"string": "", "int": 0, "long": 0, "float": 0.0, "double": 0.0,
            "bool": False, "object": {}, "array": [{}],
            "int[]": [0], "long[]": [0], "double[]": [0.0],
            "string[]": [""], "bool[]": [False]}


def log(m):
    line = "%s  %s" % (datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3], m)
    with lock:
        print(line, flush=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def default_of(t):
    v = DEFAULTS.get(t, 0)
    return dict(v) if isinstance(v, dict) else (list(v) if isinstance(v, list) else v)


class Session(object):
    key = iv = None
    token = 1000001
    account_seq = 1
    race_value = 0

    @classmethod
    def issue(cls):
        cls.key = secrets.token_bytes(16)
        cls.iv = secrets.token_bytes(16)
        return base64.b64encode(cls.key).decode(), base64.b64encode(cls.iv).decode()

    @classmethod
    def decrypt(cls, blob):
        raw = base64.b64decode(blob)
        d = Cipher(algorithms.AES(cls.key), modes.CBC(cls.iv)).decryptor()
        p = d.update(raw) + d.finalize()
        u = padding.PKCS7(128).unpadder()
        return (u.update(p) + u.finalize()).decode("utf-8")

    @classmethod
    def encrypt(cls, text):
        p = padding.PKCS7(128).padder()
        data = p.update(text.encode("utf-8")) + p.finalize()
        e = Cipher(algorithms.AES(cls.key), modes.CBC(cls.iv)).encryptor()
        return base64.b64encode(e.update(data) + e.finalize()).decode()


def auto(path):
    """스키마 기반 자동 응답. 컨테이너(object/array) 뒤의 키들은 그 안에 넣는다."""
    body = {"success": True, "errorCode": None, "token": Session.token}
    cls = ROUTE_CLASS.get(path)
    info = SCHEMA.get(cls or "", {})
    keys = info.get("keys", [])
    types = info.get("types", {})
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
    return body


def ep_login(req):
    key, iv = Session.issue()
    b = auto("/user/auth/login")
    b.update({"cryptoKey": key, "initialVector": iv,
              "accountSeq": Session.account_seq, "registered": True,
              "takeTrophy": False, "newWeek": False, "newPresent": False,
              "newWeekStart": datetime.datetime.now().strftime("%Y%m%d%H%M")})
    b["result"] = dict((k, b[k]) for k in ("accountSeq", "registered", "takeTrophy",
                                           "newWeek", "newWeekStart", "newPresent"))
    log("         *** 로그인 발급 key=%s" % key)
    return b


def ep_userinfo(req):
    b = auto("/user/info/get")          # 이 버전은 평면 구조 (info 중첩 없음)
    b.update({
        "nickName": PLAYER["nickName"], "gold": PLAYER["gold"],
        "goldAmt": PLAYER["gold"], "trophyCnt": PLAYER["trophyCnt"],
        "tireCnt": PLAYER["tireCnt"], "tireRemainSecs": 0, "canPresent": True,
        "carNo": PLAYER["carNo"], "carSeq": PLAYER["carSeq"],
        "carClass": PLAYER["carClass"], "characterNo": PLAYER["characterNo"],
    })
    return b


def ep_tire(req):
    b = auto("/user/tire/check")
    b.update({"tireCnt": PLAYER["tireCnt"], "remainTime": 0})
    if "result" in b:
        b["result"] = {"tireCnt": PLAYER["tireCnt"], "remainTime": 0}
    return b


def _container(cls_name):
    info = SCHEMA.get(cls_name, {})
    keys = info.get("keys", [])
    types = info.get("types", {})
    ci = next((i for i, k in enumerate(keys) if types.get(k) in ("object", "array")), None)
    return keys, types, ci


def ep_carlist(req):
    b = auto("/user/car/list")
    keys, types, ci = _container("HTTP_GetCarList")
    if ci is not None:
        car = dict((m, default_of(types.get(m, "int"))) for m in keys[ci + 1:])
        for k in ("carNo", "carSeq", "carClass"):
            if k in car:
                car[k] = PLAYER[k]
        if "isSelected" in car:
            car["isSelected"] = True
        b[keys[ci]] = [car]
    return b


def ep_charlist(req):
    b = auto("/user/character/list")
    keys, types, ci = _container("HTTP_GetCharacterList")
    if ci is not None:
        ch = dict((m, default_of(types.get(m, "int"))) for m in keys[ci + 1:])
        if "characterNo" in ch:
            ch["characterNo"] = PLAYER["characterNo"]
        if "isSelected" in ch:
            ch["isSelected"] = True
        b[keys[ci]] = [ch]
    return b


def ep_gamestart(req):
    Session.race_value += 1
    b = auto("/play/game/start")
    if "raceValue" in b:
        b["raceValue"] = Session.race_value
    return b


def ep_gamefinish(req):
    r = (req or {}).get("gameFinishReq", {}) or {}
    got = int(r.get("gold", 0) or 0)
    PLAYER["gold"] += got
    log("         *** 레이스 종료: 획득골드=%d -> 보유=%d" % (got, PLAYER["gold"]))
    b = auto("/play/game/finish")
    for k in ("remainGoldAmt", "goldAmt", "gold"):
        if k in b:
            b[k] = PLAYER["gold"]
    if "remainTireCnt" in b:
        b["remainTireCnt"] = PLAYER["tireCnt"]
    return b


ROUTES = {
    "/user/auth/login": ep_login,
    "/user/info/get": ep_userinfo,
    "/user/tire/check": ep_tire,
    "/user/car/list": ep_carlist,
    "/user/character/list": ep_charlist,
    "/play/game/start": ep_gamestart,
    "/play/game/finish": ep_gamefinish,
}


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

            enc = "crypto" in hdrs.get("content-type", "")
            text = body.decode("utf-8", "replace")
            used_enc = False
            if enc and body and not text.lstrip().startswith(("{", "[")):
                try:
                    text = Session.decrypt(text.strip())
                    used_enc = True
                except Exception as e:
                    log("         [복호화 실패] %s" % e)
                    text = ""
            if text.strip():
                log("         REQ: %s" % text[:300])
            try:
                req = json.loads(text) if text.strip() else {}
            except Exception:
                req = {}

            path = target.split("?")[0].rstrip("/") or "/"
            fn = ROUTES.get(path)
            resp = fn(req) if fn else auto(path)
            if path not in ROUTE_CLASS:
                log("         [미매핑] %s" % path)
            out = json.dumps(resp, ensure_ascii=False, separators=(',', ':'))
            log("         RES: %s" % out[:260])
            payload = (Session.encrypt(out).encode() if used_enc else out.encode("utf-8"))
            ctype = "application/crypto+json" if used_enc else "application/json"
            self.request.sendall(
                ("HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
                 "Connection: close\r\n\r\n" % (ctype, len(payload))).encode() + payload)
        except Exception as e:
            log("  [err] %r" % e)
        finally:
            try:
                self.request.close()
            except Exception:
                pass


class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    log("=== 차차차 v1.3.1 서버 :%d (스키마 %d클래스 / 경로 %d개) ==="
        % (PORT, len(SCHEMA), len(ROUTE_CLASS)))
    S(("0.0.0.0", PORT), H).serve_forever()
