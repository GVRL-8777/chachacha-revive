# -*- coding: utf-8 -*-
"""makecnserver.py 가 만든 chacnserver.py 에 뒤에 붙였던 것들을 다시 얹는다.

  · 소지금/트로피를 넉넉하게
  · 보유 차량 목록 (자동차 샵에서 산 것을 기억한다)
  · 골드/타이어 교환, 차량 구매 (구매 직후 잔액을 제대로 돌려준다)
  · 에셋번들(pack.unity3d) 을 GET 으로 내려준다
"""
import ast
import io

p = 'chacnserver.py'
s = io.open(p, encoding='utf-8').read()

s = s.replace('    "carNo": 0, "carSeq": 1, "carClass": "C", "characterNo": 0,',
              '    "carNo": 1, "carSeq": 1, "carClass": "C", "characterNo": 1,')

s = s.replace(
    '"nickName": "Racer", "gold": 50000, "trophyCnt": 10, "tireCnt": 99,',
    '"nickName": "Racer", "gold": 999999, "trophyCnt": 9999, "tireCnt": 99,')

# --- 보유 차량 -------------------------------------------------------------
old = 'DEFAULTS = {"string": ""'
new = '''# 처음부터 가진 차. 나머지는 자동차 샵에서 산다.
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
OWNED_CARS = set(list(range(1, 18)) + [26, 27, 28, 29, 30, 31, 32, 34])

DEFAULTS = {"string": ""'''
assert old in s
s = s.replace(old, new, 1)

old = '''        for k in ("carNo", "carSeq", "carClass"):
            if k in car:
                car[k] = PLAYER[k]
        if "isSelected" in car:
            car["isSelected"] = True
        b[keys[ci]] = [car]
    return b'''
new = '''        cars = []
        for no in sorted(OWNED_CARS):
            c = dict(car)
            if "carNo" in c:
                c["carNo"] = no
            if "carSeq" in c:
                c["carSeq"] = no
            if "carClass" in c:
                c["carClass"] = PLAYER["carClass"]
            if "isSelected" in c:
                c["isSelected"] = (no == PLAYER["carSeq"])
            cars.append(c)
        b[keys[ci]] = cars
    return b'''
assert old in s
s = s.replace(old, new, 1)

# --- 드라이버 12명 ---------------------------------------------------------
# CRSystem.UpdateDriverData 는 받은 목록을 driver[characterNo] 로 색인한다.
# 슬롯을 12개로 넓혀 두었으므로 0~11 을 모두 돌려준다.
old = '''        ch = dict((m, default_of(types.get(m, "int"))) for m in keys[ci + 1:])
        if "characterNo" in ch:
            ch["characterNo"] = PLAYER["characterNo"]
        if "isSelected" in ch:
            ch["isSelected"] = True
        b[keys[ci]] = [ch]
    return b'''
new = '''        ch = dict((m, default_of(types.get(m, "int"))) for m in keys[ci + 1:])
        chars = []
        for no in range(int(__import__('os').environ.get('CHA_DRV','12'))):
            c = dict(ch)
            if "characterNo" in c:
                c["characterNo"] = no + 1
            if "isSelected" in c:
                c["isSelected"] = (no + 1 == PLAYER["characterNo"])
            chars.append(c)
        b[keys[ci]] = chars
    return b'''
assert old in s
s = s.replace(old, new, 1)

old = '# 처음부터 가진 차. 나머지는 자동차 샵에서 산다.'
new = '# 드라이버 슬롯 수 (클라이언트 패치와 맞춰야 한다)\nDRIVER_COUNT = 12\n\n' + old
assert old in s
s = s.replace(old, new, 1)

# --- 상점 ------------------------------------------------------------------
old = 'ROUTES = {\n    "/user/auth/login": ep_login,'
new = '''GOLD_EXCHANGE = [(1, 3000), (5, 18000), (10, 40000), (30, 130000), (50, 230000)]
TIRE_EXCHANGE = [(1, 1), (5, 6), (10, 13), (30, 42), (50, 75)]


def _amount(req, table):
    """요청에 실린 트로피 수로 교환표에서 한 줄을 고른다."""
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
        PLAYER["gold"] += gain
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
        PLAYER["tireCnt"] += gain
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


ROUTES = {
    "/service/resource/messagelist": ep_messagelist,
    "/shop/gold/exchange": ep_exchange_gold,
    "/shop/tire/exchange": ep_exchange_tire,
    "/shop/car/buy": ep_buycar,
    "/user/auth/login": ep_login,'''
assert old in s
s = s.replace(old, new, 1)

# --- 에셋번들 내려주기 -----------------------------------------------------
CR = chr(13) + chr(10)
old = '            path = normalize(target.split("?")[0]).rstrip("/") or "/"'
new = '\n'.join([
    old,
    '            if path.startswith("/bundle/"):',
    '                fp = os.path.join(SP, "bundles", os.path.basename(path))',
    '                if os.path.exists(fp):',
    '                    blob = open(fp, "rb").read()',
    '                    log("         번들 전송: %s (%d B)"',
    '                        % (os.path.basename(fp), len(blob)))',
    '                    hdr = ("HTTP/1.1 200 OK" + CR',
    '                           + "Content-Type: application/octet-stream" + CR',
    '                           + "Content-Length: %d" % len(blob) + CR',
    '                           + "Connection: close" + CR + CR)',
    '                    self.request.sendall(hdr.encode() + blob)',
    '                else:',
    '                    log("         번들 없음: %s" % fp)',
    '                    self.request.sendall(("HTTP/1.1 404 Not Found" + CR',
    '                                          + "Content-Length: 0" + CR',
    '                                          + "Connection: close" + CR + CR).encode())',
    '                return',
])
assert old in s
s = s.replace(old, new, 1)

# --- 스키마 추출기가 놓친 중첩 컨테이너 ------------------------------------
# HTTP_UserInfo 의 "info" 가 그렇다. 클라이언트는 JSONObject 로 읽는데
# 평면으로 내보내면 "info object is not JSONObject type" 을 내고 로비로 못 간다.
old = '    ci = next((i for i, k in enumerate(keys)\n' \
      '               if types.get(k) in ("object", "array")), None)'
new = old + '\n' + '\n'.join([
    '    if ci is None:',
    '        # 타입이 안 잡힌 키가 사실은 중첩 객체인 경우',
    '        ci = next((i for i, k in enumerate(keys)',
    '                   if k not in types',
    '                   and k not in ("success", "errorCode", "token")',
    '                   and i + 1 < len(keys)), None)',
])
if False:                      # 중첩하면 차량 수치를 0으로 덮어써 차가 안 나간다
    s = s.replace(old, new, 1)

# 타입이 안 잡힌 멤버는 빈 배열로 준다.
# HTTP_UserInfo 의 "missions" 처럼 목록인 것이 0 으로 나가면
# CRSystem.SetUserInfo 가 그 자리를 훑다가 널을 만진다.
old = '        inner = dict((m, default_of(types.get(m, "int"))) for m in members)'
new = '        inner = dict((m, default_of(types[m]) if m in types else [])\n' \
      '                     for m in members)'
if old in s and False:
    s = s.replace(old, new, 1)

# 내 정보는 info 안에 담는다
old = 'def ep_userinfo(req):\n    b = auto("/user/info/get")' \
      '          # 이 버전은 평면 구조 (info 중첩 없음)\n    b.update({'
new = 'def ep_userinfo(req):\n    b = auto("/user/info/get")\n' \
      '    tgt = b["info"] if isinstance(b.get("info"), dict) else b\n    tgt.update({'
assert old in s
s = s.replace(old, new, 1)

# --- 날짜 문자열 -----------------------------------------------------------
# 빈 문자열을 주면 클라이언트가 DateTime.ParseExact 로 읽다가 FormatException 을 낸다.
old = '''        "carClass": PLAYER["carClass"], "characterNo": PLAYER["characterNo"],
    })
    return b'''
new = '''        "carClass": PLAYER["carClass"], "characterNo": PLAYER["characterNo"],
    })
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    for k in ("newWeekStart", "totalRankRewardInit"):
        if k in tgt:
            tgt[k] = stamp
    return b'''
assert old in s
s = s.replace(old, new, 1)

# --- 날짜는 yyyyMMdd 8자리 ---------------------------------------------------
# TitleMenu.GetNewWeekStart 가 DateTime.ParseExact(s, "yyyyMMdd") 로 읽는다.
s = s.replace('"newWeekStart": datetime.datetime.now().strftime("%Y%m%d%H%M")',
              '"newWeekStart": datetime.datetime.now().strftime("%Y%m%d")')
s = s.replace('    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M")',
              '    stamp = datetime.datetime.now().strftime("%Y%m%d")')

# 위에서 쓴 CR 상수를 서버 쪽에도 넣어 준다
s = s.replace('lock = threading.Lock()',
              'lock = threading.Lock()\nCR = chr(13) + chr(10)', 1)

io.open(p, 'w', encoding='utf-8').write(s)
ast.parse(s)
print("chacnserver.py 보강 완료 (구문 OK)")
