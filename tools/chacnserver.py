# -*- coding: utf-8 -*-
"""
一起车车车 (중국판 5577.com.cjenm.chachachacn) 전용 사설 서버.

7.7.0 과 달리 이 버전은 CDN/에셋번들이 없고(AssetBundleManager 자체가 없음)
모든 자산이 APK 안에 있다. 서버만 세우면 되는 구조.

스키마는 apischema.exe 가 DLL 에서 뽑은 api8.json 을 그대로 쓴다
(응답 클래스의 중첩 eType 열거형 = JSON 키, 게터 IL = 타입).

경로에 **트레일링 슬래시가 없다** (`/user/auth/login`).

사용법: python chacnserver.py [포트]
"""
import socketserver, threading, datetime, json, sys, os, base64, secrets, time, random

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

CODE = os.path.dirname(os.path.abspath(__file__))
# 코드는 tools/ 안에 있지만 **자료는 작업 폴더(그 위)** 에 있다.
# apicn.json · bundles/ · 로그가 전부 거기다.
SP = os.path.dirname(CODE)
LOG = os.path.join(SP, "servercn.log")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
lock = threading.Lock()
CR = chr(13) + chr(10)

SCHEMA = {}
_p = os.path.join(SP, "apicn.json")
if os.path.exists(_p):
    SCHEMA = json.load(open(_p, encoding="utf-8-sig"))

# 경로 -> 응답 클래스 (중국판은 86개 경로를 쓴다. 로그인/로비 임계 경로만 명시하고
# 나머지는 스키마 기반 자동 응답으로 처리한다)
ROUTE_CLASS = {
    "/service/inspection/check": "HTTP_CheckService",
    "/service/notice/get": "HTTP_CheckNotice",
    "/user/auth/login": "HTTP_Login",
    "/user/auth/logout": "HTTP_Logout",
    "/user/auth/withdrawal": "HTTP_WithDrawal",
    "/user/auth/cancelwithdrawal": "HTTP_CancelWithDrawal",
    "/user/info/get": "HTTP_UserInfo",
    "/user/info/update": "HTTP_UpdateUserInfo",
    "/user/tire/check": "HTTP_CheckTire",
    "/user/car/list": "HTTP_GetCarList",
    "/user/car/select": "HTTP_SelectCar",
    "/user/car/upgrade": "HTTP_UpgradeCar",
    "/user/car/tune": "HTTP_TuneCar",
    "/user/car/compensate": "HTTP_TradeBuyValueList",
    "/user/character/list": "HTTP_GetCharacterList",
    "/user/character/select": "HTTP_SelectCharacter",
    "/user/boast/set": "HTTP_BoastAble",
    "/shop/item/list": "HTTP_GetItemList",
    "/shop/item/buy": "HTTP_BuyItem",
    "/shop/car/buy": "HTTP_BuyCar",
    "/shop/car/unlock": "HTTP_UnlockClass",
    "/shop/car/unlockbuy": "HTTP_UnlockBuy",
    "/shop/car/compensate": "HTTP_TradeBuy",
    "/shop/character/buy": "HTTP_BuyCharacter",
    "/shop/gold/exchange": "HTTP_ExchangeGold",
    "/shop/tire/exchange": "HTTP_ExchangeTire",
    "/play/game/start": "HTTP_GameStart",
    "/play/game/finish": "HTTP_GameFinish",
    "/play/item/use": "HTTP_UseItem",
    "/play/item/buyuse": "HTTP_BuyUseItem",
    "/ranking/current/list": "HTTP_GetRank",
    "/ranking/previous/list": "HTTP_GetRank",
    "/ranking/previous/reward": "HTTP_GetPrevRankReward",
    "/tire/present/list": "HTTP_GetGiftList",
    "/tire/present/recv": "HTTP_RecvGiftTire",
    "/tire/present/recvAll": "HTTP_RecvAllGiftTire",
    "/tire/present/send": "HTTP_SendGiftTire",
    "/invitation/list": "HTTP_InviteList",
    "/invitation/invite": "HTTP_Invite",
    "/setting/present/allow": "HTTP_AbleGiftSetting",
    "/event/review/complete": "HTTP_Event",
    "/grandprix/info/get": "HTTP_GrandPrixInfo",
}

# 중국판 클라는 URL 패딩(`/xxxx/`) 때문에 경로 앞에 잉여 세그먼트가 붙는다.
# 알려진 최상위 접두사가 나오는 지점부터 잘라 쓴다.
KNOWN_ROOTS = ("/user/", "/play/", "/service/", "/shop/", "/ranking/", "/skill/",
               "/setting/", "/event/", "/ladder/", "/tire/", "/invitation/",
               "/grandprix/", "/versus/", "/gotya/")


def normalize(path):
    for r in KNOWN_ROOTS:
        i = path.find(r)
        if i > 0:
            return path[i:]
    return path


# 플레이어 상태 (서버가 권위를 가진다)
PLAYER = {
    "nickName": "Racer", "gold": 999999, "trophyCnt": 9999, "tireCnt": 900,
    "carNo": 1, "carSeq": 1, "carClass": "C", "characterNo": 1,
    "bestScore": 0, "bestScoreHurdle": 0, "prevScore": 0, "inviteCnt": 0,
    "maxDistance": 0, "playCount": 0,
}

# 드라이버 슬롯 수 (클라이언트 패치와 맞춰야 한다)
DRIVER_COUNT = 12

# 보유 드라이버(1~12). 상태 파일이 정한다.
DRIVERS_OWNED = set(range(1, 13))

# 처음부터 가진 차. 나머지는 자동차 샵에서 산다.
# 차고 캐러셀은 목록의 차를 차례로 만들어 보므로, 프리팹이 없는 차가 섞이면
# Instantiate(null) 로 깨진다(차량 선택이 통째로 안 먹는다).
# 중국판 Resources 에 player_<이름>_a 프리팹이 있는 25대만 준다.
# 서버의 carNo 는 1부터라 CarIndex+1 이다.
#   없는 차: Lamborghini(21) C7(23) Astonmartin(25) Unicorn(33)
#            Archangel(35) W3(36) Blitz(37) Pluto(38), helly(18)는 번들 확인 뒤에.
# 뒤쪽 S/R 등급 차들은 차고 뷰포트에서 모델이 안 올라와 선택이 멈춘다.
# 기본 로스터 17대만 준다. 나머지는 자동차 샵 쪽에서 따로 손볼 것.
# 중국판 Resources 에 player_<이름>_a 프리팹이 있는 25대.
# (없는 것: Lamborghini 21, C7 23, Astonmartin 25, Unicorn 33, helly 18)
# CarDataBase(editor_/database/cardatabase) 의 CarIndex + 1 과 시작 등급.
#  1 AVEO C / 2 PRIUS B / ... / 21 Lamborghini S / 33 Unicorn S / 34 Meteor A
# 35~38(Archangel W3 Blitz Pluto)은 중국판에 모델이 아예 없어 뺀다.
CAR_CLASS = {1: "C", 2: "B", 3: "B", 4: "B", 5: "B", 6: "B", 7: "A", 8: "A", 9: "A", 10: "C", 11: "B", 12: "B", 13: "A", 14: "B", 15: "A", 16: "A", 17: "A", 18: "A", 21: "S", 23: "S", 25: "S", 26: "C", 27: "C", 28: "C", 29: "B", 30: "C", 31: "C", 32: "C", 33: "S", 34: "A"}

# 값 = (골드값, 트로피값). 프리미엄 차는 트로피로 산다.
CAR_COST = {1: (0, 0), 2: (5000, 14), 3: (5000, 14), 4: (5000, 14), 5: (5000, 14), 6: (5000, 14), 7: (20000, 50), 8: (20000, 50), 9: (20000, 50), 10: (0, 10), 11: (0, 14), 12: (0, 14), 13: (20000, 50), 14: (5000, 14), 15: (20000, 50), 16: (20000, 50), 17: (20000, 50), 18: (0, 0), 21: (0, 120), 23: (0, 120), 25: (0, 120), 26: (0, 15), 27: (0, 15), 28: (0, 15), 29: (5000, 14), 30: (0, 15), 31: (0, 15), 32: (0, 15), 33: (0, 120), 34: (25000, 60)}

# 자동차 샵에 남겨 둘 차. 전부 갖고 있으면 미보유 목록이 비어
# 자동차 샵 탭이 그냥 되돌아와 먹통처럼 보인다.
SHOP_CARS = {33, 34, 21, 23, 25}

OWNED_CARS = set(CAR_CLASS) - SHOP_CARS

# 차별 튜닝 레벨 (carNo, 항목) -> 0~3. 없으면 0(기본).
# 응답에는 +1 해서 내보낸다. 게터가 1 을 빼기 때문이다.
TUNE = {}

# 클라이언트가 한 겹 안쪽에서 읽는 응답. 게터가 전부 이 컨테이너를 거친다.
#   HTTP_UserInfo.get_gold  ->  get_info()["gold"]
# 평면으로 내보내면 골드 0, 트로피 -1 로 보인다.
CONTAINERS = {
    "HTTP_UserInfo": "info",
    "HTTP_GrandPrixInfo": "bestScore",
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
    forced = CONTAINERS.get(cls or "")
    if forced in keys:
        ci = keys.index(forced)
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
              "takeTrophy": False,
              "newWeek": os.environ.get("CHA_NEWWEEK") == "1", "newPresent": False,
              "newWeekStart": datetime.datetime.now().strftime("%Y%m%d")})
    b["result"] = dict((k, b[k]) for k in ("accountSeq", "registered", "takeTrophy",
                                           "newWeek", "newWeekStart", "newPresent"))
    log("         *** 로그인 발급 key=%s" % key)
    return b


def ep_userinfo(req):
    b = auto("/user/info/get")
    tgt = b["info"] if isinstance(b.get("info"), dict) else b
    tgt.update({
        "nickName": PLAYER["nickName"], "gold": PLAYER["gold"],
        "goldAmt": PLAYER["gold"], "trophyCnt": PLAYER["trophyCnt"],
        "tireCnt": PLAYER["tireCnt"], "tireRemainSecs": 0, "canPresent": True,
        "carNo": PLAYER["carNo"], "carSeq": PLAYER["carSeq"],
        "carClass": CAR_CLASS.get(PLAYER["carNo"], PLAYER["carClass"]),
        "characterNo": PLAYER["characterNo"],
        "maxScore": PLAYER["bestScore"],
        "maxPoint": PLAYER["bestScore"],
        "maxDistance": PLAYER["maxDistance"],
        "playCount": PLAYER["playCount"],
        "friendInviteCnt": PLAYER["inviteCnt"],
        "carAccel": TUNE.get((PLAYER["carNo"], "carAccel"), 0) + 1,
        "carSpeed": TUNE.get((PLAYER["carNo"], "carSpeed"), 0) + 1,
        "carFuleCost": TUNE.get((PLAYER["carNo"], "carFuleCost"), 0) + 1,
    })
    b["missions"] = []
    tgt.pop("missions", None)
    stamp = datetime.datetime.now().strftime("%Y%m%d")
    for k in ("newWeekStart", "totalRankRewardInit"):
        if k in tgt:
            tgt[k] = stamp
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
        cars = []
        for no in sorted(OWNED_CARS):
            c = dict(car)
            if "carNo" in c:
                c["carNo"] = no
            if "carSeq" in c:
                c["carSeq"] = no + 1
            if "carClass" in c:
                c["carClass"] = CAR_CLASS.get(no, "C")
            if "isSelected" in c:
                c["isSelected"] = (no == PLAYER["carNo"])
            for k in ("carAccel", "carSpeed", "carFuleCost"):
                if k in c:
                    c[k] = TUNE.get((no, k), 0) + 1
            cars.append(c)
        b[keys[ci]] = cars
    return b


def ep_charlist(req):
    b = auto("/user/character/list")
    keys, types, ci = _container("HTTP_GetCharacterList")
    if ci is not None:
        ch = dict((m, default_of(types.get(m, "int"))) for m in keys[ci + 1:])
        chars = []
        for no in sorted(DRIVERS_OWNED):
            no -= 1
            c = dict(ch)
            if "characterNo" in c:
                c["characterNo"] = no + 1
            if "isSelected" in c:
                c["isSelected"] = (no + 1 == PLAYER["characterNo"])
            chars.append(c)
        b[keys[ci]] = chars
    return b


def ep_gamestart(req):
    Session.race_value += 1
    no = req.get("carNo")
    if isinstance(no, int) and no in OWNED_CARS:
        PLAYER["carNo"] = no
        PLAYER["carClass"] = CAR_CLASS.get(no, "C")
        seq = req.get("carSeq")
        if isinstance(seq, int) and seq > 0:
            PLAYER["carSeq"] = seq
    b = auto("/play/game/start")
    if "raceValue" in b:
        b["raceValue"] = Session.race_value
    return b


def ep_gamefinish(req):
    r = (req or {}).get("gameFinishReq") or req or {}
    got = int(r.get("gold", 0) or 0)
    add_gold(got)
    sc = int(r.get("score", 0) or 0)
    key = "bestScoreHurdle" if str(r.get("gameMode", "001")) == "002" \
        else "bestScore"
    if sc > PLAYER[key]:
        PLAYER[key] = sc
        log("         *** 최고 기록 %s = %d" % (key, sc))
    PLAYER["maxDistance"] = max(PLAYER["maxDistance"],
                                int(r.get("distance", 0) or 0))
    PLAYER["playCount"] += 1
    log("         *** 레이스 종료: 획득골드=%d -> 보유=%d" % (got, PLAYER["gold"]))
    b = auto("/play/game/finish")
    for k in ("remainGoldAmt", "goldAmt", "gold"):
        if k in b:
            b[k] = PLAYER["gold"]
    if "remainTireCnt" in b:
        b["remainTireCnt"] = PLAYER["tireCnt"]
    return b


GOLD_EXCHANGE = [(5, 2500), (10, 6000), (20, 14000), (30, 24000),
                 (50, 45000), (100, 100000)]
TIRE_EXCHANGE = [(5, 5), (10, 12), (20, 30), (30, 50), (50, 90), (100, 200)]


# 자리 번호 -> (트로피값, 받는 양)
EXCHANGE_NO = {
    1: (5, 5), 2: (10, 12), 5: (20, 30), 6: (30, 50), 7: (50, 90),
    8: (100, 200),                                   # 타이어
    3: (5, 2500), 4: (10, 6000), 9: (20, 14000), 10: (30, 24000),
    11: (50, 45000), 12: (100, 100000),              # 골드
}


def _amount(req, table):
    """요청의 exchangeNo 로 교환표에서 한 줄을 고른다."""
    no = req.get("exchangeNo")
    if isinstance(no, int) and no in EXCHANGE_NO:
        return EXCHANGE_NO[no]
    want = 0
    for k in ("trophyCnt", "count", "itemCount", "amount", "productNo"):
        v = req.get(k)
        if isinstance(v, int) and v > 0:
            want = v
            break
    for cost, gain in table:
        if cost == want:
            return cost, gain
    return table[0]


def ep_exchange_gold(req):
    cost, gain = _amount(req, GOLD_EXCHANGE)
    if PLAYER["trophyCnt"] >= cost:
        PLAYER["trophyCnt"] -= cost
        add_gold(gain)
    b = auto("/shop/gold/exchange")
    b["remainGoldAmt"] = PLAYER["gold"]
    b["goldAmt"] = PLAYER["gold"]
    b["remainTrophyCnt"] = PLAYER["trophyCnt"]
    b["trophyCnt"] = PLAYER["trophyCnt"]
    log("         *** 골드 교환: 트로피 -%d, 골드 +%d" % (cost, gain))
    return b


def ep_exchange_tire(req):
    cost, gain = _amount(req, TIRE_EXCHANGE)
    if PLAYER["trophyCnt"] >= cost:
        PLAYER["trophyCnt"] -= cost
        add_tire(gain)
    b = auto("/shop/tire/exchange")
    b["remainTrophyCnt"] = PLAYER["trophyCnt"]
    b["trophyCnt"] = PLAYER["trophyCnt"]
    b["remainTireCnt"] = PLAYER["tireCnt"]
    b["tireCnt"] = PLAYER["tireCnt"]
    log("         *** 타이어 교환: 트로피 -%d, 타이어 +%d" % (cost, gain))
    return b


def ep_buycar(req):
    no = 0
    for k in ("carNo", "carSeq", "productNo"):
        v = req.get(k)
        if isinstance(v, int) and v > 0:
            no = v
            break
    cost = req.get("price") if isinstance(req.get("price"), int) else 0
    if no:
        OWNED_CARS.add(no)
        PLAYER["gold"] = max(0, PLAYER["gold"] - cost)
    b = auto("/shop/car/buy")
    b["remainGoldAmt"] = PLAYER["gold"]
    b["goldAmt"] = PLAYER["gold"]
    b["carSeq"] = no
    b["carNo"] = no
    log("         *** 차량 구매: %d (보유 %d대)" % (no, len(OWNED_CARS)))
    return b


def ep_messagelist(req):
    """서버 공지 메시지 목록. 비워서 주면 클라이언트가 널을 만진다."""
    # 빈 배열을 주면 클라이언트 파서가 널을 돌려줘 길이를 재다 죽는다.
    # 알 수 없는 코드는 eMsgType 8 로 떨어져 그냥 건너뛰므로 한 줄만 넣어 둔다.
    b = auto("/service/resource/messagelist")
    b["messages"] = [{"code": "999", "message": ""}]
    return b


# 상한. 트로피는 int32(IntCrypto), 골드는 int64(LongCrypto)로 담기지만
# 화면 자릿수를 생각해 9자리에서 멈춘다. 넘겨 사도 여기서 고정된다.
MAX_GOLD = 999999999
MAX_TROPHY = 999999999
# 타이어는 998 에서 멈춘다. 999(게임 자체 상한)가 되면 클라이언트가
# "보유 타이어가 최대여서…" 를 띄우고 초대를 막는다.
MAX_TIRE = 998


def add_gold(n):
    PLAYER["gold"] = max(0, min(MAX_GOLD, PLAYER["gold"] + n))
    return PLAYER["gold"]


def add_trophy(n):
    PLAYER["trophyCnt"] = max(0, min(MAX_TROPHY, PLAYER["trophyCnt"] + n))
    return PLAYER["trophyCnt"]


def add_tire(n):
    PLAYER["tireCnt"] = max(0, min(MAX_TIRE, PLAYER["tireCnt"] + n))
    return PLAYER["tireCnt"]


def _pick(req, *names):
    for k in names:
        v = req.get(k)
        if isinstance(v, int) and v > 0:
            return v
    return 0


def ep_selectcar(req):
    no = _pick(req, "carNo")
    if no in OWNED_CARS:
        PLAYER["carNo"] = no
        PLAYER["carSeq"] = _pick(req, "carSeq") or (no + 1)
        PLAYER["carClass"] = CAR_CLASS.get(no, "C")
        log("         *** 차 선택: %d (%s class)"
            % (no, PLAYER["carClass"]))
    return auto("/user/car/select")


# 등급별 튜닝 비용. 현재 레벨(0~2)로 색인한다.
# cardatabase 의 TurningCostDB 그대로다.
TUNE_COST = {"C": [200, 400, 700], "B": [1000, 1400, 2000],
             "A": [3000, 4500, 6500], "S": [9000, 12000, 18000],
             "R": [0, 0, 0]}
TUNE_KEY = {1: "carAccel", 2: "carSpeed", 3: "carFuleCost"}
CLASS_UP = {"C": ("B", 5000), "B": ("A", 20000),
            "A": ("S", 60000), "S": ("R", 30000)}


def _carno(req):
    """요청의 carSeq(=carNo+1) 나 carNo 에서 차 번호를 얻는다."""
    no = _pick(req, "carNo")
    if no in OWNED_CARS:
        return no
    seq = _pick(req, "carSeq")
    if seq - 1 in OWNED_CARS:
        return seq - 1
    return PLAYER["carNo"]


def ep_tunecar(req):
    """튜닝. 레벨을 올리고 남은 골드를 정확히 돌려준다."""
    no = _carno(req)
    key = TUNE_KEY.get(_pick(req, "tuneType"), "carAccel")
    cls = CAR_CLASS.get(no, "C")
    lv = TUNE.get((no, key), 0)
    if lv < 3:
        cost = TUNE_COST.get(cls, TUNE_COST["C"])[lv]
        if PLAYER["gold"] >= cost:
            PLAYER["gold"] -= cost
            lv += 1
            TUNE[(no, key)] = lv
            log("         *** 튜닝: %d번차 %s %d레벨 (골드 -%d)"
                % (no, key, lv, cost))
    b = auto("/user/car/tune")
    b["remainGoldAmt"] = PLAYER["gold"]
    b["missions"] = []
    for k in ("carAccel", "carSpeed", "carFuleCost"):
        if k in b:
            b[k] = TUNE.get((no, k), 0)
    return b


def ep_upgradecar(req):
    """등급 올리기. 올리면 튜닝 레벨은 0 으로 돌아간다."""
    no = _carno(req)
    cur = CAR_CLASS.get(no, "C")
    nxt, cost = CLASS_UP.get(cur, (None, 0))
    if nxt and PLAYER["gold"] >= cost:
        PLAYER["gold"] -= cost
        CAR_CLASS[no] = nxt
        for k in ("carAccel", "carSpeed", "carFuleCost"):
            TUNE.pop((no, k), None)
        if no == PLAYER["carNo"]:
            PLAYER["carClass"] = nxt
        log("         *** 등급: %d번차 %s -> %s (골드 -%d)"
            % (no, cur, nxt, cost))
    b = auto("/user/car/upgrade")
    b["remainGoldAmt"] = PLAYER["gold"]
    b["missions"] = []
    return b


def _getcar(req, path):
    """차 구매 · 해금. 골드값이 0 인 차는 트로피로 산다.

    응답 모양이 경로마다 달라(BuyCar 는 remainGoldAmt, UnlockBuy 는
    remainTrophyCnt) 그 경로의 스키마로 만들어야 한다. 없는 키를 읽으면
    JSONObject.GetLong 이 널참조로 죽는다."""
    no = _pick(req, "carNo")
    if no not in CAR_CLASS:
        no = _pick(req, "carSeq") - 1
    gold, trophy = CAR_COST.get(no, (0, 0))
    # 골드로 사는 길(/shop/car/buy)과 트로피로 여는 길(unlock*)이 따로 있다
    by_gold = path.endswith("/buy")
    if no in CAR_CLASS and no not in OWNED_CARS:
        if by_gold and gold and PLAYER["gold"] >= gold:
            PLAYER["gold"] -= gold
            OWNED_CARS.add(no)
        elif not by_gold and PLAYER["trophyCnt"] >= trophy:
            PLAYER["trophyCnt"] -= trophy
            OWNED_CARS.add(no)
        elif PLAYER["gold"] >= gold and gold:
            PLAYER["gold"] -= gold
            OWNED_CARS.add(no)
        if no in OWNED_CARS:
            log("         *** 차 구매: %d번 (골드 %d / 트로피 %d, 보유 %d대)"
                % (no, gold, trophy, len(OWNED_CARS)))
    b = auto(path)
    b["missions"] = []
    for k in ("remainGoldAmt", "goldAmt", "gold"):
        b[k] = PLAYER["gold"]
    for k in ("remainTrophyCnt", "trophyCnt"):
        b[k] = PLAYER["trophyCnt"]
    b["carSeq"] = no + 1
    b["carNo"] = no
    b["carClass"] = CAR_CLASS.get(no, "C")
    return b


def ep_buycar2(req):
    return _getcar(req, "/shop/car/buy")


def ep_unlockcar(req):
    return _getcar(req, "/shop/car/unlock")


def ep_unlockbuycar(req):
    return _getcar(req, "/shop/car/unlockbuy")


# 수신함. 실제로 선물해 줄 친구가 없으니 타이어 한 통을 놔 둔다.
#   presentType 001=타이어 002=트로피 003=골드
#   recvDate 는 "yyyy-MM-dd HH:mm:ss" 여야 한다. 빈 문자열이면
#   GiftUnit.SetDate 의 DateTime.ParseExact 가 죽어 프리팹에 구워진
#   중국어 기본값("10天前")이 그대로 남는다.
PRESENTS = [{"presentSeq": 1, "accountSeq": 0, "presentType": "001",
             "presentQty": 5}]


def ep_presentlist(req):
    b = auto("/tire/present/list")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    b["presents"] = [dict(p, recvDate=now) for p in PRESENTS]
    return b


def ep_presentrecv(req):
    got = 0
    seq = _pick(req, "presentSeq")
    for p in list(PRESENTS):
        if seq and p["presentSeq"] != seq:
            continue
        got += p["presentQty"]
        PRESENTS.remove(p)
    add_tire(got)
    if got:
        log("         *** 선물 수령: 타이어 +%d (보유 %d)"
            % (got, PLAYER["tireCnt"]))
    b = auto("/tire/present/recv")
    b["recvType"] = "001"
    b["recvQty"] = got
    b["tireCnt"] = PLAYER["tireCnt"]
    return b


# --- 주간순위 -------------------------------------------------------
# CRSystem.SetDefaultRankData 는 userId 를 내 소셜 ID 와 견줘 "나"를 고른다.
# 소셜 플랫폼이 없어 내 소셜 ID 도, 친구 닉네임도 없다.
# rankfix.exe 로 넣은 마무리 블록이 userId 를 이름으로 쓰고,
# "__me__" 표식이면 내 줄로 잡는다.
# gameMode 001=주행 002=허들. carNo 와 ladderClassNo 는 1부터 센다.
RIVALS = [
    ("\uc9c8\uc8fc\ubcf8\ub2a5", 1200000, 9, "S"),
    ("\ub2c8\ud2b8\ub85c\ubd80\uc2a4\ud130", 940000, 8, "A"),
    ("\ub3c4\ub85c\uc704\uc758\ub2ec\ub9bc", 610000, 7, "A"),
    ("\ucd08\ubcf4\ub4dc\ub77c\uc774\ubc84", 250000, 2, "B"),
    ("\uac70\ubd81\uc774\ud0dd\ubc30", 80000, 1, "C"),
]


def _rankrow(uid, seq, score, carno, carcls, mode):
    return {"userId": uid, "gameMode": mode, "accountSeq": seq,
            "score": int(score), "carNo": carno, "carClass": carcls,
            "canPresent": False, "sentPresent": False,
            "boastReject": False, "carX": 0, "carY": 0,
            "matchRejectFlag": False, "grade": "", "isDormancy": False,
            "ladderClassNo": 1}


def _ranklist(mode_scores):
    rows = []
    for mode, my in mode_scores:
        rows.append(_rankrow("__me__", 1, my, PLAYER["carNo"],
                             CAR_CLASS.get(PLAYER["carNo"], "C"), mode))
        for i, (nm, sc, cn, cl) in enumerate(RIVALS):
            rows.append(_rankrow(nm, 100 + i, sc, cn, cl, mode))
    return rows


def ep_ranklist(req):
    b = auto("/ranking/current/list")
    b["friends"] = _ranklist([("001", PLAYER["bestScore"]),
                              ("002", PLAYER["bestScoreHurdle"])])
    return b


def ep_prevranklist(req):
    b = auto("/ranking/previous/list")
    key = "friends" if "friends" in b else "ranks"
    b[key] = _ranklist([("001", PLAYER["prevScore"])])
    return b


# --- 초대 -----------------------------------------------------------
# 이미 초대한 사람 목록은 **늘 비워 둔다.**
# 여기에 쌓아 두면 클라이언트가 그 사람들을 초대 대상에서 걸러 낸다.
# 비워 두면 앱을 껐다 켤 때마다 이웃 5명을 다시 초대할 수 있고,
# 횟수만 서버에 쌓여 30회·50회 보상까지 갈 수 있다.
def ep_invitelist(req):
    b = auto("/invitation/list")
    b["invitations"] = []
    return b


# 초대 횟수 보상. eMission 값은 열거형 **순번**이다
# (none=0, mission1=1 … mission19=19, mission32=20, mission37=21).
#   30회 -> mission10 = CAT(미아우, carNo 11)
#   50회 -> mission15 = Hummer(허미, carNo 13)
INVITE_REWARD = {
    1: ("tire", 5, 0), 5: ("gold", 4000, 0), 15: ("trophy", 20, 0),
    30: ("car", 11, 10), 50: ("car", 13, 15),
}


def ep_invite(req):
    # 초대 횟수는 계속 쌓이고, 문턱마다 보상을 준다
    PLAYER["inviteCnt"] += 1
    n = PLAYER["inviteCnt"]
    missions = []
    got = INVITE_REWARD.get(n)
    if got:
        kind, amount, mission = got
        if kind == "tire":
            add_tire(amount)
        elif kind == "gold":
            add_gold(amount)
        elif kind == "trophy":
            add_trophy(amount)
        elif kind == "car":
            OWNED_CARS.add(amount)
        if mission:
            missions.append(mission)
        log("         *** 초대 %d회 보상: %s %d" % (n, kind, amount))
    log("         *** 초대 %d회" % n)
    b = auto("/invitation/invite")
    b["inviteCnt"] = n
    b["missions"] = missions
    if got and got[0] == "car":
        b["carNo"] = got[1]
        b["carSeq"] = got[1] + 1
    return b


# --- 결제 -----------------------------------------------------------
# 실물 결제 SDK 는 없다. 클라이언트는 shopfix.exe 로 결제 플랫폼을
# BillingPlatform_Editor 로 바꿔 두어 곧바로 성공을 돌려준다.
# 흐름은 그대로라 서버는 register -> confirm 두 번을 받고,
# confirm 에서 트로피를 준다.
BILLING_ITEMS = {
    "chacha_CN_001": 10, "chacha_CN_002": 35, "chacha_CN_003": 60,
    "chacha_CN_004": 130, "chacha_CN_005": 420, "chacha_CN_006": 750,
    "chacha_CN_008": 60, "chacha_CN_009": 170,
}
PENDING = {}


def ep_billregister(req):
    item = req.get("marketItemId") or ""
    # nonce 는 반드시 **숫자**여야 한다. 문자열로 주면 클라이언트가
    # "nonce object is not System.Int64 type" 하고 0 을 되보낸다.
    nonce = int(time.time() * 1000) % 100000000
    PENDING[nonce] = item
    b = auto("/shop/billing/raven/register")
    b.update({"nonce": nonce, "resCode": "0000",
              "transactionId": str(nonce),
              "rate": 1, "applicationId": "cha", "applicationKey": "cha",
              "privateKey": "cha", "notifyUrl": "", "applicationName": "cha",
              "billRegistResult": {"resCode": "0000", "nonce": nonce}})
    log("         *** 결제 등록: %s (nonce %d)" % (item, nonce))
    return b


def ep_billconfirm(req):
    nonce = req.get("nonce")
    item = PENDING.pop(nonce, None) or req.get("marketItemId") or ""
    got = BILLING_ITEMS.get(item, 0)
    if got:
        add_trophy(got)
        log("         *** 결제 완료: %s 트로피 +%d -> %d"
            % (item, got, PLAYER["trophyCnt"]))
    b = auto("/shop/billing/raven/confirm")
    b["resCode"] = "0000"
    b["trophyCnt"] = PLAYER["trophyCnt"]
    b["remainTrophyCnt"] = PLAYER["trophyCnt"]
    return b


# --- 자동차 가챠 -----------------------------------------------------
# 트로피를 내고 뽑으면 S~C 중 하나가 나온다. 마음에 안 들면 10 트로피로
# 재도전, 창을 닫는 순간 그때 등급으로 확정. S 가 뜨면 더 못 돌린다.
# 대상은 CarDataBase 에서 IsGotyaEvent 인 6대뿐이다.
GACHA_CARS = {26: "Cyclone", 27: "Hurricane", 28: "Phoenix",
              30: "Heavysuricar", 31: "Superemperor", 32: "Thunder"}
GACHA_COST = 15
# 화면에 뜨는 재도전 값과 맞춘다(_GetPremiumGotyaCarBuyRetryTrophyCost).
GACHA_RETRY_COST = 15
# 등급 확률. S 는 드물게.
GACHA_ODDS = [("C", 45), ("B", 30), ("A", 20), ("S", 5)]


def ep_gacha(req):
    no = _pick(req, "carNo")
    retry = bool(req.get("retry"))
    cost = GACHA_RETRY_COST if retry else GACHA_COST
    b = auto("/shop/car/gacha")
    b["missions"] = []
    if no not in GACHA_CARS or PLAYER["trophyCnt"] < cost:
        b["remainTrophyCnt"] = PLAYER["trophyCnt"]
        b["carSeq"] = no + 1
        b["carClass"] = CAR_CLASS.get(no, "C")
        return b
    PLAYER["trophyCnt"] -= cost
    roll = random.randint(1, sum(w for _c, w in GACHA_ODDS))
    cls = "C"
    for name, w in GACHA_ODDS:
        roll -= w
        if roll <= 0:
            cls = name
            break
    CAR_CLASS[no] = cls
    OWNED_CARS.add(no)
    SHOP_CARS.discard(no)
    bonus = random.choice([0, 0, 500, 1000, 2000])
    if bonus:
        add_gold(bonus)
    log("         *** 가챠: %s -> %s 클래스 (트로피 -%d, 보너스 골드 %d)"
        % (GACHA_CARS[no], cls, cost, bonus))
    b["remainTrophyCnt"] = PLAYER["trophyCnt"]
    b["carSeq"] = no + 1
    b["carClass"] = cls
    b["itemNo"] = 0
    b["goldAmt"] = bonus
    return b


# --- 차량 되팔기(보상 판매) -------------------------------------------
# 헌 차를 넘기고 새 차를 싸게 산다. 클라이언트는 우리가 준 표에서
#   같은 등급 줄의 carClassValue + 각 항목이 (레벨+1) 인 줄의 값
# 을 더해 할인폭을 만든다(TradeCarValueDB.GetDiscountTrophy).
# 그래서 등급마다 레벨 1~4 짜리 줄을 넉 줄씩 준다.
TRADE_CLASS_VALUE = {"C": 0, "B": 14, "A": 50, "S": 120, "R": 200}
TRADE_LEVEL_VALUE = {1: 0, 2: 5, 3: 10, 4: 20}


def ep_tradelist(req):
    b = auto("/user/car/compensate")
    rows = []
    for cls, cv in TRADE_CLASS_VALUE.items():
        for lv, lvv in sorted(TRADE_LEVEL_VALUE.items()):
            rows.append({
                "carClass": cls, "carClassTrophy": cv,
                "carAccel": lv, "carAccelTrophy": lvv,
                "carSpeed": lv, "carSpeedTrophy": lvv,
                "carSkill": lv, "carSkillTrophy": lvv,
                "carFuleCost": lv, "carFuleCostTrophy": lvv,
            })
    b["compensateCars"] = rows
    return b


def _trade_value(no):
    """헌 차 한 대가 트로피로 얼마인가."""
    v = TRADE_CLASS_VALUE.get(CAR_CLASS.get(no, "C"), 0)
    for k in ("carAccel", "carSpeed", "carFuleCost"):
        v += TRADE_LEVEL_VALUE.get(TUNE.get((no, k), 0) + 1, 0)
    return v


def ep_tradebuy(req):
    """헌 차를 넘기고 새 차를 받는다."""
    no = _pick(req, "carNo")
    junk = _pick(req, "junkCarNo")
    cls = req.get("compensateClass") or CAR_CLASS.get(no, "C")
    b = auto("/shop/car/compensate")
    b["missions"] = []
    if no in CAR_CLASS and junk in OWNED_CARS and junk != no:
        # 값은 **클라이언트 화면과 같은 셈법**으로 매긴다.
        # 화면은 우리가 준 등급표(TRADE_CLASS_VALUE)로 정가를 잡고
        # 헌 차 값을 뺀다. 차값(CAR_COST)으로 매기면 화면에 106 이
        # 떠 놓고 46 만 깎여 어긋난다.
        base = TRADE_CLASS_VALUE.get(cls, CAR_COST.get(no, (0, 0))[1])
        price = max(0, base - _trade_value(junk))
        if PLAYER["trophyCnt"] >= price:
            PLAYER["trophyCnt"] -= price
            OWNED_CARS.discard(junk)
            SHOP_CARS.add(junk)
            for k in ("carAccel", "carSpeed", "carFuleCost"):
                TUNE.pop((junk, k), None)
            OWNED_CARS.add(no)
            SHOP_CARS.discard(no)
            if cls in ("C", "B", "A", "S", "R"):
                CAR_CLASS[no] = cls
            log("         *** 되팔기: %d번 넘기고 %d번 %s 획득 (트로피 -%d)"
                % (junk, no, cls, price))
    b["remainTrophyCnt"] = PLAYER["trophyCnt"]
    b["carSeq"] = no + 1
    return b


def ep_selectchar(req):
    no = _pick(req, "characterNo")
    if 1 <= no <= DRIVER_COUNT:
        PLAYER["characterNo"] = no
        log("         *** 드라이버 선택: %d" % no)
    return auto("/user/character/select")


import chastate as _S

STATE = _S.load()
_state_mtime = [0.0]
_state_last = [""]


def _state_apply():
    """파일 -> 서버 안의 살아 있는 값들."""
    st = STATE
    p = st["player"]
    PLAYER["nickName"] = p.get("nickName", "Racer")
    PLAYER["gold"] = int(p.get("gold", 0))
    PLAYER["trophyCnt"] = int(p.get("trophy", 0))
    PLAYER["tireCnt"] = int(p.get("tire", 0))
    PLAYER["carNo"] = _S.NAME_TO_NO.get(p.get("car", "AVEO"), 1)
    PLAYER["carSeq"] = PLAYER["carNo"] + 1
    PLAYER["characterNo"] = int(p.get("driver", 1))

    r = st["records"]
    for a, b in (("bestScore", "bestScore"),
                 ("bestScoreHurdle", "bestScoreHurdle"),
                 ("prevScore", "prevScore"),
                 ("maxDistance", "maxDistance"),
                 ("playCount", "playCount")):
        PLAYER[b] = int(r.get(a, 0))
    PLAYER["inviteCnt"] = int(st["invite"].get("count", 0))

    # 등급은 시작 등급 위에 파일 값을 덮는다
    for name, cls in st.get("carClass", {}).items():
        no = _S.NAME_TO_NO.get(name)
        if no in CAR_CLASS and cls in ("C", "B", "A", "S", "R"):
            CAR_CLASS[no] = cls
    PLAYER["carClass"] = CAR_CLASS.get(PLAYER["carNo"], "C")

    OWNED_CARS.clear()
    for name in st.get("carsOwned", []):
        no = _S.NAME_TO_NO.get(name)
        if no in CAR_CLASS:
            OWNED_CARS.add(no)
    SHOP_CARS.clear()
    SHOP_CARS.update(set(CAR_CLASS) - OWNED_CARS)

    TUNE.clear()
    keymap = {"accel": "carAccel", "speed": "carSpeed", "oil": "carFuleCost"}
    for name, t in st.get("carTune", {}).items():
        no = _S.NAME_TO_NO.get(name)
        if no is None:
            continue
        for k, v in (t or {}).items():
            if k in keymap and int(v or 0):
                TUNE[(no, keymap[k])] = max(0, min(3, int(v)))

    ITEMS.clear()
    _codes = dict((v, k) for k, v in ITEM_NAME.items())
    for _n, _v in (st.get("items") or {}).items():
        if _n in _codes:
            ITEMS[_codes[_n]] = max(0, min(ITEM_MAX, int(_v or 0)))

    SKILLS.clear()
    import chaskill as _K
    for _r in _K.normalize(st.get("skills") or []):
        SKILLS[(_r['car'], _r['no'])] = {'lv': _r['lv'], 'eq': _r['eq']}

    DRIVERS_OWNED.clear()
    DRIVERS_OWNED.update(int(d) for d in st.get("driversOwned", [])
                         if 1 <= int(d) <= DRIVER_COUNT)
    if not DRIVERS_OWNED:
        DRIVERS_OWNED.add(1)

    kind = {"tire": "001", "trophy": "002", "gold": "003"}
    del PRESENTS[:]
    for i, pr in enumerate(st.get("presents", [])):
        PRESENTS.append({"presentSeq": i + 1, "accountSeq": 0,
                         "presentType": kind.get(pr.get("type"), "001"),
                         "presentQty": int(pr.get("count", 1)),
                         "sender": pr.get("from", "")})


def _state_gather():
    """서버 안의 값 -> 파일 모양."""
    st = STATE
    st["player"].update({
        "nickName": PLAYER["nickName"],
        "gold": PLAYER["gold"], "trophy": PLAYER["trophyCnt"],
        "tire": PLAYER["tireCnt"],
        "car": _S.NO_TO_NAME.get(PLAYER["carNo"], "AVEO"),
        "driver": PLAYER["characterNo"],
    })
    st["records"].update({
        "bestScore": PLAYER["bestScore"],
        "bestScoreHurdle": PLAYER["bestScoreHurdle"],
        "prevScore": PLAYER["prevScore"],
        "maxDistance": PLAYER["maxDistance"],
        "playCount": PLAYER["playCount"],
    })
    st["invite"]["count"] = PLAYER["inviteCnt"]
    st["carsOwned"] = [_S.NO_TO_NAME[n] for n in sorted(OWNED_CARS)
                       if n in _S.NO_TO_NAME]
    st["carClass"] = dict((_S.NO_TO_NAME[n], c) for n, c in CAR_CLASS.items()
                          if n in _S.NO_TO_NAME
                          and c != _S.START_CLASS.get(_S.NO_TO_NAME[n]))
    back = {"carAccel": "accel", "carSpeed": "speed", "carFuleCost": "oil"}
    tune = {}
    for (no, k), v in TUNE.items():
        nm = _S.NO_TO_NAME.get(no)
        if nm and k in back:
            tune.setdefault(nm, {})[back[k]] = v
    st["carTune"] = tune
    st["items"] = dict((ITEM_NAME[c], int(ITEMS.get(c, 0)))
                       for c in ITEM_CODES)
    st["skills"] = [{"car": c, "no": n, "lv": v['lv'], "eq": bool(v['eq'])}
                    for (c, n), v in sorted(SKILLS.items())]
    st["driversOwned"] = sorted(DRIVERS_OWNED)
    label = {"001": "tire", "002": "trophy", "003": "gold"}
    st["presents"] = [{"type": label.get(p["presentType"], "tire"),
                       "count": p["presentQty"],
                       "from": p.get("sender", "")} for p in PRESENTS]
    return st


def _state_pull():
    """런처가 파일을 고쳤으면 다시 읽는다."""
    try:
        m = os.path.getmtime(_S.STATE_PATH)
    except OSError:
        return
    if m <= _state_mtime[0]:
        return
    _state_mtime[0] = m
    fresh = _S.load()
    STATE.clear()
    STATE.update(fresh)
    _state_apply()
    _state_last[0] = json.dumps(STATE, ensure_ascii=False, sort_keys=True)
    log("         *** 상태 파일을 다시 읽었다")


def _state_push():
    """값이 바뀌었으면 파일에 남긴다."""
    st = _S.clamp(_state_gather())
    blob = json.dumps(st, ensure_ascii=False, sort_keys=True)
    if blob == _state_last[0]:
        return
    _state_last[0] = blob
    try:
        _S.save(st)
        _state_mtime[0] = os.path.getmtime(_S.STATE_PATH)
    except OSError as e:
        log("  [상태 저장 실패] %r" % e)


def ep_updateuserinfo(req):
    """이름 바꾸기. 빈 이름이면 지금 이름을 지킨다."""
    nm = (req or {}).get("nickName")
    if isinstance(nm, str) and nm.strip():
        nm = nm.strip()[:16]
        if nm != PLAYER["nickName"]:
            log("         *** 이름 바꿈: %s -> %s" % (PLAYER["nickName"], nm))
        PLAYER["nickName"] = nm
    b = auto("/user/info/update")
    b["nickName"] = PLAYER["nickName"]
    return b


# CRSystem/eItemCode 그대로. 8~12 는 공구상자 안쪽 코드라 상점에 안 나온다.
ITEM_CODES = [1, 2, 3, 4, 5, 6, 7]
ITEM_NAME = {1: "BestOil", 2: "Nos", 3: "FrontSensor", 4: "ToolBox",
             5: "OneShot", 6: "Emergency", 7: "Turbo"}
# 값은 클라이언트 Generic_ShopMain/eItemCost 와 같은 값이어야 한다(골드).
ITEM_COST = {1: 900, 2: 800, 3: 700, 4: 600, 5: 1000, 6: 1500, 7: 300}
ITEM_MAX = 99
ITEMS = {}


def ep_itemlist(req):
    b = auto("/shop/item/list")
    b["items"] = [{"itemCode": c, "itemCount": int(ITEMS.get(c, 0))}
                  for c in ITEM_CODES]
    b["toolboxRetryCount"] = 0
    b["toolboxRebuyGoldAmt"] = 0
    return b


def ep_buyitem(req):
    """아이템 한 개 구매. 값은 클라이언트 표와 같다."""
    code = _pick(req, "itemCode")
    cost = ITEM_COST.get(code, 0)
    if code in ITEM_COST and PLAYER["gold"] >= cost:
        PLAYER["gold"] -= cost
        ITEMS[code] = min(ITEM_MAX, int(ITEMS.get(code, 0)) + 1)
        log("         *** 아이템 구매: %s (골드 -%d, 보유 %d)"
            % (ITEM_NAME[code], cost, ITEMS[code]))
    b = auto("/shop/item/buy")
    b["remainGoldAmt"] = PLAYER["gold"]
    b["toolboxItemNo"] = 0
    return b


def ep_useitem(req):
    code = _pick(req, "itemCode")
    if int(ITEMS.get(code, 0)) > 0:
        ITEMS[code] = int(ITEMS[code]) - 1
    b = auto("/play/item/use")
    b["remainGoldAmt"] = PLAYER["gold"]
    return b


# 캐릭터 값은 DB 에 없고 **캐릭터 화면 카드에 박혀 있다.**
# 화면에 뜨는 값과 실제로 깎는 값이 어긋나면 안 되므로 그대로 옮겼다.
#   1 도 강현  = 기본 드라이버(무료)
#   2 Sarah Cha 60 · 3 빈 경유 40 · 4 나 연비 50
#   5~12       120  (슬롯을 늘리며 붙인 자리까지 같은 값)
# 골드로도 살 수 있게 하되 환율은 게임 자체의 골드 교환표를 따른다
# (5 트로피 = 2,500 골드 → 트로피 1 = 500 골드).
DRIVER_COST = {1: 0, 2: 60, 3: 40, 4: 50}
DRIVER_COST_DEFAULT = 120
DRIVER_GOLD_PER_TROPHY = 500


def ep_buycharacter(req):
    """캐릭터 구매. 트로피가 모자라면 골드로 받는다.

    응답 클래스에 골드 칸이 없어서 화면의 골드는 다음 새로고침 때 맞는다."""
    no = _pick(req, "characterNo")
    cost = DRIVER_COST.get(no, DRIVER_COST_DEFAULT)
    gold_price = cost * DRIVER_GOLD_PER_TROPHY
    if 1 <= no <= DRIVER_COUNT and no not in DRIVERS_OWNED:
        if PLAYER["trophyCnt"] >= cost:
            PLAYER["trophyCnt"] -= cost
            DRIVERS_OWNED.add(no)
            log("         *** 캐릭터 구매: %d번 (트로피 -%d)" % (no, cost))
        elif PLAYER["gold"] >= gold_price:
            PLAYER["gold"] -= gold_price
            DRIVERS_OWNED.add(no)
            log("         *** 캐릭터 구매: %d번 (골드 -%d)" % (no, gold_price))
    b = auto("/shop/character/buy")
    b["remainTrophyCnt"] = PLAYER["trophyCnt"]
    b["missions"] = []
    return b


def ep_notice(req):
    """공지사항. 내용은 상태 파일에서 온다."""
    b = auto("/service/notice/get")
    n = STATE.get("notice", {})
    for k in ("notice", "noticeMessage", "message", "content"):
        b[k] = n.get("body", "")
    for k in ("noticeTitle", "title"):
        b[k] = n.get("title", "")
    for k in ("noticeUrl", "url"):
        b[k] = n.get("url", "")
    return b


# ------------------------------------------------------------------ 스킬
# 스킬은 **차마다** 붙는다. 살아 있는 값은 (차번호, 스킬번호) -> {레벨, 장착}.
# 표(값·최대 레벨)는 게임의 SkillDataBase 를 그대로 읽어 쓴다.
SKILLS = {}


def _skilltab():
    import chaskill
    return dict((s['no'], s) for s in chaskill.table('x77'))


def ep_skilllist(req):
    import chaskill
    b = auto("/skill/get/list")
    rows = [{'car': c, 'no': n, 'lv': v['lv'], 'eq': v['eq']}
            for (c, n), v in sorted(SKILLS.items())]
    b["skillList"] = chaskill.as_list(rows)
    return b


def ep_skillbuy(req):
    """스킬 한 개 구매. 값은 게임 표 그대로(골드 10,000 또는 트로피 50)."""
    no = _pick(req, "skillNo")
    car = _pick(req, "carNo")
    tb = _skilltab()
    s = tb.get(no)
    if s and (car, no) not in SKILLS:
        if s['costType'] == 'Trophy' and PLAYER["trophyCnt"] >= s['cost']:
            PLAYER["trophyCnt"] -= s['cost']
            SKILLS[(car, no)] = {'lv': 1, 'eq': False}
        elif s['costType'] != 'Trophy' and PLAYER["gold"] >= s['cost']:
            PLAYER["gold"] -= s['cost']
            SKILLS[(car, no)] = {'lv': 1, 'eq': False}
        if (car, no) in SKILLS:
            log("         *** 스킬 구매: %d번차 %s (%s %d)"
                % (car, s['code'], s['costType'], s['cost']))
    b = auto("/skill/buy")
    # 이름이 차·아이템 쪽과 다르다. Amount/Count 다.
    b["remainGoldAmount"] = PLAYER["gold"]
    b["remainTrophyCount"] = PLAYER["trophyCnt"]
    return b


def ep_skillequip(req):
    no = _pick(req, "skillNo")
    car = _pick(req, "carNo")
    on = str(req.get("equipFlag") or "Y").upper().startswith("Y")
    cur = SKILLS.get((car, no))
    if cur is not None:
        cur['eq'] = on
    return auto("/skill/equip")


def ep_skillupgrade(req):
    no = _pick(req, "skillNo")
    car = _pick(req, "carNo")
    tb = _skilltab()
    s = tb.get(no)
    cur = SKILLS.get((car, no))
    b = auto("/skill/upgrade")
    if s and cur:
        nxt = cur['lv'] + 1
        costs = s['upgrade'] or []
        cost = costs[cur['lv'] - 1] if cur['lv'] - 1 < len(costs) else 0
        if nxt <= s['max'] and PLAYER["gold"] >= cost:
            PLAYER["gold"] -= cost
            cur['lv'] = nxt
            log("         *** 스킬 올림: %d번차 %s -> %d레벨 (골드 -%d)"
                % (car, s['code'], nxt, cost))
        b["skillLevel"] = cur['lv']
    else:
        b["skillLevel"] = 1
    b["remainGoldAmount"] = PLAYER["gold"]
    return b


ROUTES = {
    "/skill/get/list": ep_skilllist,
    "/skill/buy": ep_skillbuy,
    "/skill/equip": ep_skillequip,
    "/skill/upgrade": ep_skillupgrade,
    "/service/resource/messagelist": ep_messagelist,
    "/user/car/select": ep_selectcar,
    "/user/character/select": ep_selectchar,
    "/user/car/tune": ep_tunecar,
    "/user/car/upgrade": ep_upgradecar,
    "/shop/car/buy": ep_buycar2,
    "/shop/car/unlock": ep_unlockcar,
    "/shop/car/unlockbuy": ep_unlockbuycar,
    "/tire/present/list": ep_presentlist,
    "/tire/present/recv": ep_presentrecv,
    "/tire/present/recvAll": ep_presentrecv,
    "/ranking/current/list": ep_ranklist,
    "/ranking/previous/list": ep_prevranklist,
    "/invitation/list": ep_invitelist,
    "/invitation/invite": ep_invite,
    "/shop/billing/raven/register": ep_billregister,
    "/shop/billing/raven/confirm": ep_billconfirm,
    "/service/notice/get": ep_notice,
    "/shop/item/list": ep_itemlist,
    "/shop/item/buy": ep_buyitem,
    "/play/item/use": ep_useitem,
    "/shop/character/buy": ep_buycharacter,
    "/user/info/update": ep_updateuserinfo,
    "/shop/car/gacha": ep_gacha,
    "/user/car/compensate": ep_tradelist,
    "/shop/car/compensate": ep_tradebuy,
    "/shop/gold/exchange": ep_exchange_gold,
    "/shop/tire/exchange": ep_exchange_tire,
    "/shop/car/buy": ep_buycar,
    "/user/auth/login": ep_login,
    "/user/info/get": ep_userinfo,
    "/user/tire/check": ep_tire,
    "/user/car/list": ep_carlist,
    "/user/character/list": ep_charlist,
    "/play/game/start": ep_gamestart,
    "/play/game/finish": ep_gamefinish,
}


def unwrap(req):
    """{"xxxReq": {...}} 한 겹을 벗겨 안쪽 dict 를 돌려준다."""
    if isinstance(req, dict) and len(req) == 1:
        v = list(req.values())[0]
        if isinstance(v, dict):
            return v
    return req


_state_apply()
_state_mtime[0] = os.path.getmtime(_S.STATE_PATH) \
    if os.path.exists(_S.STATE_PATH) else 0.0
_state_last[0] = json.dumps(STATE, ensure_ascii=False, sort_keys=True)


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

            path = normalize(target.split("?")[0]).rstrip("/") or "/"
            if path.startswith("/bundle/"):
                fp = os.path.join(SP, "bundles", os.path.basename(path))
                if os.path.exists(fp):
                    blob = open(fp, "rb").read()
                    log("         번들 전송: %s (%d B)"
                        % (os.path.basename(fp), len(blob)))
                    hdr = ("HTTP/1.1 200 OK" + CR
                           + "Content-Type: application/octet-stream" + CR
                           + "Content-Length: %d" % len(blob) + CR
                           + "Connection: close" + CR + CR)
                    self.request.sendall(hdr.encode() + blob)
                else:
                    log("         번들 없음: %s" % fp)
                    self.request.sendall(("HTTP/1.1 404 Not Found" + CR
                                          + "Content-Length: 0" + CR
                                          + "Connection: close" + CR + CR).encode())
                return
            _state_pull()
            fn = ROUTES.get(path)
            resp = fn(unwrap(req)) if fn else auto(path)
            if path not in ROUTE_CLASS:
                log("         [미매핑] %s" % path)
            out = json.dumps(resp, ensure_ascii=False, separators=(',', ':'))
            log("         RES: %s" % out[:260])
            _state_push()
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
    log("=== 중국판 차차차 서버 :%d (스키마 %d클래스 / 경로 %d개) ==="
        % (PORT, len(SCHEMA), len(ROUTE_CLASS)))
    S(("0.0.0.0", PORT), H).serve_forever()
