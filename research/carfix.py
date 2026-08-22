# -*- coding: utf-8 -*-
"""chacnserver.py 를 클라이언트 실제 규칙에 맞춘다. (cnpatch.py 다음에 돌린다)

Assembly-CSharp 의 IL 을 다시 읽어 확정한 것들이다.

0) 튜닝 레벨(carAccel carSpeed carFuleCost)도 게터가 1 을 뺀다.
   0 을 주면 레벨이 -1 이 되어 TurningCostDB.GetCostByLevel(-1) 이
   IndexOutOfRange 를 내고 **업그레이드 버튼이 통째로 먹통**이 된다.
   레벨 0(기본)은 1 로 보내야 한다. 최대는 3 이니 1~4 를 쓴다.

1) HTTP_UserInfo 는 모든 값을 get_info() 를 거쳐 읽는다.
   info 를 중첩하지 않으면 골드는 0, 트로피는 -1(ldc.i4.m1)로 나온다.
   예전에 "중첩하면 차량 수치가 0 이 된다"고 껐었는데, carAccel/carSpeed/
   carFuleCost 는 능력치가 아니라 튜닝 '레벨'(set_accelLevel 등)이라
   0 이 기본값이고 정상이다. GetEarlyAccelAbility = 기본 + 레벨*계수.

2) 차 번호(carNo)와 드라이버 번호(characterNo)는 **1 부터** 센다.
   게터가 마지막에 1 을 뺀다(ldc.i4.1; sub). 그래서 서버 값은 CarIndex + 1 이다.
   실제 CarIndex: 0~16, 20, 22, 24, 25~33 → 서버 carNo 1~17, 21, 23, 25, 26~34.
   (34~37 Archangel/W3/Blitz/Pluto 는 중국판에 모델이 아예 없어 뺀다)
   0 을 주면 GetCarDataByIndex(-1) 이 널이라 SetUserInfo 가 널참조로 죽고,
   그 예외로 로비 초기화가 끊겨 상점·내차고 버튼이 먹통이 된다.

3) 차 등급(carClass)은 차마다 다르다. 차고 모델 이름이
   player_<이름>_<등급> 이라, S 부터 시작하는 차에 "C" 를 주면
   player_lamborghini_c 를 찾다가 Instantiate(null) 로 죽는다.
   또 CarClassDataArray 에 그 등급이 없어 능력치도 못 읽는다.

4) 드라이버도 마찬가지로 1~12 를 준다. 게터가 1 을 빼서 driver[0..11] 이 된다.
   0 을 주면 driver[-1] 로 IndexOutOfRange 가 난다.
"""
import ast
import io

p = 'chacnserver.py'
s = io.open(p, encoding='utf-8').read()

# --- 1. 차 목록과 등급 ------------------------------------------------------
# 키는 서버 carNo(= CarIndex + 1), 값은 그 차의 시작 등급.
# 18 은 이식해 넣은 helly(로봇 변신차)다.
CAR_CLASS = {
    1: "C", 2: "B", 3: "B", 4: "B", 5: "B", 6: "B", 7: "A", 8: "A", 9: "A",
    10: "C", 11: "B", 12: "B", 13: "A", 14: "B", 15: "A", 16: "A", 17: "A",
    18: "A", 21: "S", 23: "S", 25: "S", 26: "C", 27: "C", 28: "C", 29: "B",
    30: "C", 31: "C", 32: "C", 33: "S", 34: "A"}

# 값 = (골드값, 트로피값). 프리미엄 차는 트로피로 산다.
CAR_COST = {
    1: (0, 0), 2: (5000, 14), 3: (5000, 14), 4: (5000, 14), 5: (5000, 14),
    6: (5000, 14), 7: (20000, 50), 8: (20000, 50), 9: (20000, 50),
    10: (0, 10), 11: (0, 14), 12: (0, 14), 13: (20000, 50), 14: (5000, 14),
    15: (20000, 50), 16: (20000, 50), 17: (20000, 50), 18: (0, 0),
    21: (0, 120), 23: (0, 120), 25: (0, 120), 26: (0, 15), 27: (0, 15),
    28: (0, 15), 29: (5000, 14), 30: (0, 15), 31: (0, 15), 32: (0, 15),
    33: (0, 120), 34: (25000, 60)}

# 자동차 샵에 남겨 둘 차. 전부 갖고 있으면 '미보유' 목록이 비어
# 자동차 샵 탭이 그냥 되돌아와 먹통처럼 보인다.
# 트로피·골드가 넉넉하니 눌러서 바로 살 수 있다.
SHOP_CARS = {21, 23, 25, 33, 34}

# newcar.py 로 새로 넣은 차. 표에 얹어 준다(상점에 매물로 둔다).
def _newcars():
    import io as _io, json as _json, os as _os
    p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                      'newcars.json')
    if not _os.path.exists(p):
        return []
    try:
        return _json.load(_io.open(p, encoding='utf-8'))
    except Exception:
        return []


for _c in _newcars():
    _no = int(_c['carNo'])
    CAR_CLASS[_no] = _c['class']
    CAR_COST[_no] = (int(_c.get('gold', 0)), int(_c.get('trophy', 0)))
    SHOP_CARS.add(_no)

old = 'OWNED_CARS = set(list(range(1, 18)) + [26, 27, 28, 29, 30, 31, 32, 34])'
new = '\n'.join([
    '# CarDataBase(editor_/database/cardatabase) 의 CarIndex + 1 과 시작 등급.',
    '#  1 AVEO C / 2 PRIUS B / ... / 21 Lamborghini S / 33 Unicorn S / 34 Meteor A',
    '# 35~38(Archangel W3 Blitz Pluto)은 중국판에 모델이 아예 없어 뺀다.',
    'CAR_CLASS = ' + repr(CAR_CLASS).replace("'", '"'),
    '',
    '# 값 = (골드값, 트로피값). 프리미엄 차는 트로피로 산다.',
    'CAR_COST = ' + repr(CAR_COST),
    '',
    '# 자동차 샵에 남겨 둘 차. 전부 갖고 있으면 미보유 목록이 비어',
    '# 자동차 샵 탭이 그냥 되돌아와 먹통처럼 보인다.',
    'SHOP_CARS = ' + repr(SHOP_CARS),
    '',
    'OWNED_CARS = set(CAR_CLASS) - SHOP_CARS',
    '',
    '# 차별 튜닝 레벨 (carNo, 항목) -> 0~3. 없으면 0(기본).',
    '# 응답에는 +1 해서 내보낸다. 게터가 1 을 빼기 때문이다.',
    'TUNE = {}',
])
assert old in s, '차 목록 줄을 못 찾았다'
s = s.replace(old, new, 1)

# 주간순위·초대에 쓸 누적값을 PLAYER 에 더 넣는다
old = '    "carNo": 1, "carSeq": 1, "carClass": "C", "characterNo": 1,'
new = old + '\n' + '\n'.join([
    '    "bestScore": 0, "bestScoreHurdle": 0, "prevScore": 0, "inviteCnt": 0,',
    '    "maxDistance": 0, "playCount": 0,',
])
assert old in s, 'PLAYER 줄을 못 찾았다'
s = s.replace(old, new, 1)

# 껍데기는 unwrap() 이 이미 벗겨 준다. 여기서 또 벗기면 빈 dict 가 되어
# 레이스 보상 골드가 통째로 사라진다.
old = '    r = (req or {}).get("gameFinishReq", {}) or {}'
new = '    r = (req or {}).get("gameFinishReq") or req or {}'
assert old in s, 'ep_gamefinish 의 요청 처리 줄을 못 찾았다'
s = s.replace(old, new, 1)

# 레이스가 끝나면 최고 기록을 갱신한다(주간순위가 이 값을 쓴다)
old = '''    got = int(r.get("gold", 0) or 0)
    PLAYER["gold"] += got'''
new = '''    got = int(r.get("gold", 0) or 0)
    PLAYER["gold"] += got
    sc = int(r.get("score", 0) or 0)
    key = "bestScoreHurdle" if str(r.get("gameMode", "001")) == "002" \\
        else "bestScore"
    if sc > PLAYER[key]:
        PLAYER[key] = sc
        log("         *** 최고 기록 %s = %d" % (key, sc))
    PLAYER["maxDistance"] = max(PLAYER["maxDistance"],
                                int(r.get("distance", 0) or 0))
    PLAYER["playCount"] += 1'''
assert old in s, '레이스 종료 처리를 못 찾았다'
s = s.replace(old, new, 1)

# --- 2. 차 목록 응답 --------------------------------------------------------
old = '\n'.join([
    '            if "carSeq" in c:',
    '                c["carSeq"] = no',
    '            if "carClass" in c:',
    '                c["carClass"] = PLAYER["carClass"]',
    '            if "isSelected" in c:',
    '                c["isSelected"] = (no == PLAYER["carSeq"])',
])
new = '\n'.join([
    '            if "carSeq" in c:',
    '                c["carSeq"] = no + 1',
    '            if "carClass" in c:',
    '                c["carClass"] = CAR_CLASS.get(no, "C")',
    '            if "isSelected" in c:',
    '                c["isSelected"] = (no == PLAYER["carNo"])',
    '            for k in ("carAccel", "carSpeed", "carFuleCost"):',
    '                if k in c:',
    '                    c[k] = TUNE.get((no, k), 0) + 1',
])
assert old in s, '차 목록 응답 부분을 못 찾았다'
s = s.replace(old, new, 1)

# --- 3. info 중첩 -----------------------------------------------------------
# 스키마 추출기가 "info" 의 타입을 못 잡아 평면으로 나가고 있었다.
old = '''    ci = next((i for i, k in enumerate(keys)
               if types.get(k) in ("object", "array")), None)'''
new = old + '\n' + '\n'.join([
    '    forced = CONTAINERS.get(cls or "")',
    '    if forced in keys:',
    '        ci = keys.index(forced)',
])
assert old in s, 'auto() 컨테이너 판정 부분을 못 찾았다'
s = s.replace(old, new, 1)

old = 'DEFAULTS = {"string": ""'
new = '\n'.join([
    '# 클라이언트가 한 겹 안쪽에서 읽는 응답. 게터가 전부 이 컨테이너를 거친다.',
    '#   HTTP_UserInfo.get_gold  ->  get_info()["gold"]',
    '# 평면으로 내보내면 골드 0, 트로피 -1 로 보인다.',
    'CONTAINERS = {',
    '    "HTTP_UserInfo": "info",',
    '    "HTTP_GrandPrixInfo": "bestScore",',
    '}',
    '',
    old,
])
assert old in s
s = s.replace(old, new, 1)

# missions 는 최상위 int 배열이다(_getIntArrayData). 컨테이너 안에 있으면 꺼낸다.
# (타입 없는 키를 통째로 [] 로 바꾸면 HTTP_GetRank 의 friends 필드가 전부
#  배열이 되어 JSONObject.GetLong 이 널참조로 죽는다. missions 만 손댄다)
old = '''    stamp = datetime.datetime.now().strftime("%Y%m%d")'''
new = '\n'.join([
    '    b["missions"] = []',
    '    tgt.pop("missions", None)',
    old,
])
assert old in s
s = s.replace(old, new, 1)

# 내 차의 등급도 그 차의 시작 등급으로 맞춘다.
old = '        "carClass": PLAYER["carClass"], "characterNo": PLAYER["characterNo"],'
new = '        "carClass": CAR_CLASS.get(PLAYER["carNo"], PLAYER["carClass"]),\n' \
      '        "characterNo": PLAYER["characterNo"],\n' \
      '        "maxScore": PLAYER["bestScore"],\n' \
      '        "maxPoint": PLAYER["bestScore"],\n' \
      '        "maxDistance": PLAYER["maxDistance"],\n' \
      '        "playCount": PLAYER["playCount"],\n' \
      '        "friendInviteCnt": PLAYER["inviteCnt"],\n' \
      '        "carAccel": TUNE.get((PLAYER["carNo"], "carAccel"), 0) + 1,\n' \
      '        "carSpeed": TUNE.get((PLAYER["carNo"], "carSpeed"), 0) + 1,\n' \
      '        "carFuleCost": TUNE.get((PLAYER["carNo"], "carFuleCost"), 0) + 1,'
assert old in s
s = s.replace(old, new, 1)

# --- 5. 고른 차·드라이버를 기억한다 -----------------------------------------
# 차고에서 고른 차가 서버에 남지 않으면 다시 켰을 때 기본차로 돌아간다.
old = 'ROUTES = {\n    "/service/resource/messagelist": ep_messagelist,'
new = '\n'.join([
    '# 상한. 트로피는 int32(IntCrypto), 골드는 int64(LongCrypto)로 담기지만',
    '# 화면 자릿수를 생각해 9자리에서 멈춘다. 넘겨 사도 여기서 고정된다.',
    'MAX_GOLD = 999999999',
    'MAX_TROPHY = 999999999',
    '# 타이어는 998 에서 멈춘다. 999(게임 자체 상한)가 되면 클라이언트가',
    '# "보유 타이어가 최대여서…" 를 띄우고 초대를 막는다.',
    'MAX_TIRE = 998',
    '',
    '',
    'def add_gold(n):',
    '    PLAYER["gold"] = max(0, min(MAX_GOLD, PLAYER["gold"] + n))',
    '    return PLAYER["gold"]',
    '',
    '',
    'def add_trophy(n):',
    '    PLAYER["trophyCnt"] = max(0, min(MAX_TROPHY, PLAYER["trophyCnt"] + n))',
    '    return PLAYER["trophyCnt"]',
    '',
    '',
    'def add_tire(n):',
    '    PLAYER["tireCnt"] = max(0, min(MAX_TIRE, PLAYER["tireCnt"] + n))',
    '    return PLAYER["tireCnt"]',
    '',
    '',
    'def _pick(req, *names):',
    '    for k in names:',
    '        v = req.get(k)',
    '        if isinstance(v, int) and v > 0:',
    '            return v',
    '    return 0',
    '',
    '',
    'def ep_selectcar(req):',
    '    no = _pick(req, "carNo")',
    '    if no in OWNED_CARS:',
    '        PLAYER["carNo"] = no',
    '        PLAYER["carSeq"] = _pick(req, "carSeq") or (no + 1)',
    '        PLAYER["carClass"] = CAR_CLASS.get(no, "C")',
    '        log("         *** 차 선택: %d (%s class)"',
    '            % (no, PLAYER["carClass"]))',
    '    return auto("/user/car/select")',
    '',
    '',
    '# 등급별 튜닝 비용. 현재 레벨(0~2)로 색인한다.',
    '# cardatabase 의 TurningCostDB 그대로다.',
    'TUNE_COST = {"C": [200, 400, 700], "B": [1000, 1400, 2000],',
    '             "A": [3000, 4500, 6500], "S": [9000, 12000, 18000],',
    '             "R": [0, 0, 0]}',
    'TUNE_KEY = {1: "carAccel", 2: "carSpeed", 3: "carFuleCost"}',
    'CLASS_UP = {"C": ("B", 5000), "B": ("A", 20000),',
    '            "A": ("S", 60000), "S": ("R", 30000)}',
    '',
    '',
    'def _carno(req):',
    '    """요청의 carSeq(=carNo+1) 나 carNo 에서 차 번호를 얻는다."""',
    '    no = _pick(req, "carNo")',
    '    if no in OWNED_CARS:',
    '        return no',
    '    seq = _pick(req, "carSeq")',
    '    if seq - 1 in OWNED_CARS:',
    '        return seq - 1',
    '    return PLAYER["carNo"]',
    '',
    '',
    'def ep_tunecar(req):',
    '    """튜닝. 레벨을 올리고 남은 골드를 정확히 돌려준다."""',
    '    no = _carno(req)',
    '    key = TUNE_KEY.get(_pick(req, "tuneType"), "carAccel")',
    '    cls = CAR_CLASS.get(no, "C")',
    '    lv = TUNE.get((no, key), 0)',
    '    if lv < 3:',
    '        cost = TUNE_COST.get(cls, TUNE_COST["C"])[lv]',
    '        if PLAYER["gold"] >= cost:',
    '            PLAYER["gold"] -= cost',
    '            lv += 1',
    '            TUNE[(no, key)] = lv',
    '            log("         *** 튜닝: %d번차 %s %d레벨 (골드 -%d)"',
    '                % (no, key, lv, cost))',
    '    b = auto("/user/car/tune")',
    '    b["remainGoldAmt"] = PLAYER["gold"]',
    '    b["missions"] = []',
    '    for k in ("carAccel", "carSpeed", "carFuleCost"):',
    '        if k in b:',
    '            b[k] = TUNE.get((no, k), 0)',
    '    return b',
    '',
    '',
    'def ep_upgradecar(req):',
    '    """등급 올리기. 올리면 튜닝 레벨은 0 으로 돌아간다."""',
    '    no = _carno(req)',
    '    cur = CAR_CLASS.get(no, "C")',
    '    nxt, cost = CLASS_UP.get(cur, (None, 0))',
    '    if nxt and PLAYER["gold"] >= cost:',
    '        PLAYER["gold"] -= cost',
    '        CAR_CLASS[no] = nxt',
    '        for k in ("carAccel", "carSpeed", "carFuleCost"):',
    '            TUNE.pop((no, k), None)',
    '        if no == PLAYER["carNo"]:',
    '            PLAYER["carClass"] = nxt',
    '        log("         *** 등급: %d번차 %s -> %s (골드 -%d)"',
    '            % (no, cur, nxt, cost))',
    '    b = auto("/user/car/upgrade")',
    '    b["remainGoldAmt"] = PLAYER["gold"]',
    '    b["missions"] = []',
    '    return b',
    '',
    '',
    'def _getcar(req, path):',
    '    """차 구매 · 해금. 골드값이 0 인 차는 트로피로 산다.',
    '',
    '    응답 모양이 경로마다 달라(BuyCar 는 remainGoldAmt, UnlockBuy 는',
    '    remainTrophyCnt) 그 경로의 스키마로 만들어야 한다. 없는 키를 읽으면',
    '    JSONObject.GetLong 이 널참조로 죽는다."""',
    '    no = _pick(req, "carNo")',
    '    if no not in CAR_CLASS:',
    '        no = _pick(req, "carSeq") - 1',
    '    gold, trophy = CAR_COST.get(no, (0, 0))',
    '    # 골드로 사는 길(/shop/car/buy)과 트로피로 여는 길(unlock*)이 따로 있다',
    '    by_gold = path.endswith("/buy")',
    '    if no in CAR_CLASS and no not in OWNED_CARS:',
    '        if by_gold and gold and PLAYER["gold"] >= gold:',
    '            PLAYER["gold"] -= gold',
    '            OWNED_CARS.add(no)',
    '        elif not by_gold and PLAYER["trophyCnt"] >= trophy:',
    '            PLAYER["trophyCnt"] -= trophy',
    '            OWNED_CARS.add(no)',
    '        elif PLAYER["gold"] >= gold and gold:',
    '            PLAYER["gold"] -= gold',
    '            OWNED_CARS.add(no)',
    '        if no in OWNED_CARS:',
    '            log("         *** 차 구매: %d번 (골드 %d / 트로피 %d, 보유 %d대)"',
    '                % (no, gold, trophy, len(OWNED_CARS)))',
    '    b = auto(path)',
    '    b["missions"] = []',
    '    for k in ("remainGoldAmt", "goldAmt", "gold"):',
    '        b[k] = PLAYER["gold"]',
    '    for k in ("remainTrophyCnt", "trophyCnt"):',
    '        b[k] = PLAYER["trophyCnt"]',
    '    b["carSeq"] = no + 1',
    '    b["carNo"] = no',
    '    b["carClass"] = CAR_CLASS.get(no, "C")',
    '    return b',
    '',
    '',
    'def ep_buycar2(req):',
    '    return _getcar(req, "/shop/car/buy")',
    '',
    '',
    'def ep_unlockcar(req):',
    '    return _getcar(req, "/shop/car/unlock")',
    '',
    '',
    'def ep_unlockbuycar(req):',
    '    return _getcar(req, "/shop/car/unlockbuy")',
    '',
    '',
    '# 수신함. 실제로 선물해 줄 친구가 없으니 타이어 한 통을 놔 둔다.',
    '#   presentType 001=타이어 002=트로피 003=골드',
    '#   recvDate 는 "yyyy-MM-dd HH:mm:ss" 여야 한다. 빈 문자열이면',
    '#   GiftUnit.SetDate 의 DateTime.ParseExact 가 죽어 프리팹에 구워진',
    '#   중국어 기본값("10天前")이 그대로 남는다.',
    'PRESENTS = [{"presentSeq": 1, "accountSeq": 0, "presentType": "001",',
    '             "presentQty": 5}]',
    '',
    '',
    'def ep_presentlist(req):',
    '    b = auto("/tire/present/list")',
    '    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")',
    '    b["presents"] = [dict(p, recvDate=now) for p in PRESENTS]',
    '    return b',
    '',
    '',
    'def ep_presentrecv(req):',
    '    got = 0',
    '    seq = _pick(req, "presentSeq")',
    '    for p in list(PRESENTS):',
    '        if seq and p["presentSeq"] != seq:',
    '            continue',
    '        got += p["presentQty"]',
    '        PRESENTS.remove(p)',
    '    PLAYER["tireCnt"] += got',
    '    if got:',
    '        log("         *** 선물 수령: 타이어 +%d (보유 %d)"',
    '            % (got, PLAYER["tireCnt"]))',
    '    b = auto("/tire/present/recv")',
    '    b["recvType"] = "001"',
    '    b["recvQty"] = got',
    '    b["tireCnt"] = PLAYER["tireCnt"]',
    '    return b',
    '',
    '',
    '# --- 주간순위 -------------------------------------------------------',
    '# CRSystem.SetDefaultRankData 는 userId 를 내 소셜 ID 와 견줘 "나"를 고른다.',
    '# 소셜 플랫폼이 없어 내 소셜 ID 도, 친구 닉네임도 없다.',
    '# rankfix.exe 로 넣은 마무리 블록이 userId 를 이름으로 쓰고,',
    '# "__me__" 표식이면 내 줄로 잡는다.',
    '# gameMode 001=주행 002=허들. carNo 와 ladderClassNo 는 1부터 센다.',
    'RIVALS = [',
    '    ("\\uc9c8\\uc8fc\\ubcf8\\ub2a5", 1200000, 9, "S"),',
    '    ("\\ub2c8\\ud2b8\\ub85c\\ubd80\\uc2a4\\ud130", 940000, 8, "A"),',
    '    ("\\ub3c4\\ub85c\\uc704\\uc758\\ub2ec\\ub9bc", 610000, 7, "A"),',
    '    ("\\ucd08\\ubcf4\\ub4dc\\ub77c\\uc774\\ubc84", 250000, 2, "B"),',
    '    ("\\uac70\\ubd81\\uc774\\ud0dd\\ubc30", 80000, 1, "C"),',
    ']',
    '',
    '',
    'def _rankrow(uid, seq, score, carno, carcls, mode):',
    '    return {"userId": uid, "gameMode": mode, "accountSeq": seq,',
    '            "score": int(score), "carNo": carno, "carClass": carcls,',
    '            "canPresent": False, "sentPresent": False,',
    '            "boastReject": False, "carX": 0, "carY": 0,',
    '            "matchRejectFlag": False, "grade": "", "isDormancy": False,',
    '            "ladderClassNo": 1}',
    '',
    '',
    'def _ranklist(mode_scores):',
    '    rows = []',
    '    for mode, my in mode_scores:',
    '        rows.append(_rankrow("__me__", 1, my, PLAYER["carNo"],',
    '                             CAR_CLASS.get(PLAYER["carNo"], "C"), mode))',
    '        for i, (nm, sc, cn, cl) in enumerate(RIVALS):',
    '            rows.append(_rankrow(nm, 100 + i, sc, cn, cl, mode))',
    '    return rows',
    '',
    '',
    'def ep_ranklist(req):',
    '    b = auto("/ranking/current/list")',
    '    b["friends"] = _ranklist([("001", PLAYER["bestScore"]),',
    '                              ("002", PLAYER["bestScoreHurdle"])])',
    '    return b',
    '',
    '',
    'def ep_prevranklist(req):',
    '    b = auto("/ranking/previous/list")',
    '    key = "friends" if "friends" in b else "ranks"',
    '    b[key] = _ranklist([("001", PLAYER["prevScore"])])',
    '    return b',
    '',
    '',
    '# --- 초대 -----------------------------------------------------------',
    '# 이미 초대한 사람 목록은 **늘 비워 둔다.**',
    '# 여기에 쌓아 두면 클라이언트가 그 사람들을 초대 대상에서 걸러 낸다.',
    '# 비워 두면 앱을 껐다 켤 때마다 이웃 5명을 다시 초대할 수 있고,',
    '# 횟수만 서버에 쌓여 30회·50회 보상까지 갈 수 있다.',
    'def ep_invitelist(req):',
    '    b = auto("/invitation/list")',
    '    b["invitations"] = []',
    '    return b',
    '',
    '',
    '# 초대 횟수 보상. eMission 값은 열거형 **순번**이다',
    '# (none=0, mission1=1 … mission19=19, mission32=20, mission37=21).',
    '#   30회 -> mission10 = CAT(미아우, carNo 11)',
    '#   50회 -> mission15 = Hummer(허미, carNo 13)',
    'INVITE_REWARD = {',
    '    1: ("tire", 5, 0), 5: ("gold", 4000, 0), 15: ("trophy", 20, 0),',
    '    30: ("car", 11, 10), 50: ("car", 13, 15),',
    '}',
    '',
    '',
    'def ep_invite(req):',
    '    # 초대 횟수는 계속 쌓이고, 문턱마다 보상을 준다',
    '    PLAYER["inviteCnt"] += 1',
    '    n = PLAYER["inviteCnt"]',
    '    missions = []',
    '    got = INVITE_REWARD.get(n)',
    '    if got:',
    '        kind, amount, mission = got',
    '        if kind == "tire":',
    '            add_tire(amount)',
    '        elif kind == "gold":',
    '            add_gold(amount)',
    '        elif kind == "trophy":',
    '            add_trophy(amount)',
    '        elif kind == "car":',
    '            OWNED_CARS.add(amount)',
    '        if mission:',
    '            missions.append(mission)',
    '        log("         *** 초대 %d회 보상: %s %d" % (n, kind, amount))',
    '    log("         *** 초대 %d회" % n)',
    '    b = auto("/invitation/invite")',
    '    b["inviteCnt"] = n',
    '    b["missions"] = missions',
    '    if got and got[0] == "car":',
    '        b["carNo"] = got[1]',
    '        b["carSeq"] = got[1] + 1',
    '    return b',
    '',
    '',
    '# --- 결제 -----------------------------------------------------------',
    '# 실물 결제 SDK 는 없다. 클라이언트는 shopfix.exe 로 결제 플랫폼을',
    '# BillingPlatform_Editor 로 바꿔 두어 곧바로 성공을 돌려준다.',
    '# 흐름은 그대로라 서버는 register -> confirm 두 번을 받고,',
    '# confirm 에서 트로피를 준다.',
    'BILLING_ITEMS = {',
    '    "chacha_CN_001": 10, "chacha_CN_002": 35, "chacha_CN_003": 60,',
    '    "chacha_CN_004": 130, "chacha_CN_005": 420, "chacha_CN_006": 750,',
    '    "chacha_CN_008": 60, "chacha_CN_009": 170,',
    '}',
    'PENDING = {}',
    '',
    '',
    'def ep_billregister(req):',
    '    item = req.get("marketItemId") or ""',
    '    # nonce 는 반드시 **숫자**여야 한다. 문자열로 주면 클라이언트가',
    '    # "nonce object is not System.Int64 type" 하고 0 을 되보낸다.',
    '    nonce = int(time.time() * 1000) % 100000000',
    '    PENDING[nonce] = item',
    '    b = auto("/shop/billing/raven/register")',
    '    b.update({"nonce": nonce, "resCode": "0000",',
    '              "transactionId": str(nonce),',
    '              "rate": 1, "applicationId": "cha", "applicationKey": "cha",',
    '              "privateKey": "cha", "notifyUrl": "", "applicationName": "cha",',
    '              "billRegistResult": {"resCode": "0000", "nonce": nonce}})',
    '    log("         *** 결제 등록: %s (nonce %d)" % (item, nonce))',
    '    return b',
    '',
    '',
    'def ep_billconfirm(req):',
    '    nonce = req.get("nonce")',
    '    item = PENDING.pop(nonce, None) or req.get("marketItemId") or ""',
    '    got = BILLING_ITEMS.get(item, 0)',
    '    if got:',
    '        add_trophy(got)',
    '        log("         *** 결제 완료: %s 트로피 +%d -> %d"',
    '            % (item, got, PLAYER["trophyCnt"]))',
    '    b = auto("/shop/billing/raven/confirm")',
    '    b["resCode"] = "0000"',
    '    b["trophyCnt"] = PLAYER["trophyCnt"]',
    '    b["remainTrophyCnt"] = PLAYER["trophyCnt"]',
    '    return b',
    '',
    '',
    '# --- 자동차 가챠 -----------------------------------------------------',
    '# 트로피를 내고 뽑으면 S~C 중 하나가 나온다. 마음에 안 들면 10 트로피로',
    '# 재도전, 창을 닫는 순간 그때 등급으로 확정. S 가 뜨면 더 못 돌린다.',
    '# 대상은 CarDataBase 에서 IsGotyaEvent 인 6대뿐이다.',
    'GACHA_CARS = {26: "Cyclone", 27: "Hurricane", 28: "Phoenix",',
    '              30: "Heavysuricar", 31: "Superemperor", 32: "Thunder"}',
    'GACHA_COST = 15',
    '# 화면에 뜨는 재도전 값과 맞춘다(_GetPremiumGotyaCarBuyRetryTrophyCost).',
    'GACHA_RETRY_COST = 15',
    '# 등급 확률. S 는 드물게.',
    'GACHA_ODDS = [("C", 45), ("B", 30), ("A", 20), ("S", 5)]',
    '',
    '',
    'def ep_gacha(req):',
    '    no = _pick(req, "carNo")',
    '    retry = bool(req.get("retry"))',
    '    cost = GACHA_RETRY_COST if retry else GACHA_COST',
    '    b = auto("/shop/car/gacha")',
    '    b["missions"] = []',
    '    if no not in GACHA_CARS or PLAYER["trophyCnt"] < cost:',
    '        b["remainTrophyCnt"] = PLAYER["trophyCnt"]',
    '        b["carSeq"] = no + 1',
    '        b["carClass"] = CAR_CLASS.get(no, "C")',
    '        return b',
    '    PLAYER["trophyCnt"] -= cost',
    '    roll = random.randint(1, sum(w for _c, w in GACHA_ODDS))',
    '    cls = "C"',
    '    for name, w in GACHA_ODDS:',
    '        roll -= w',
    '        if roll <= 0:',
    '            cls = name',
    '            break',
    '    CAR_CLASS[no] = cls',
    '    OWNED_CARS.add(no)',
    '    SHOP_CARS.discard(no)',
    '    bonus = random.choice([0, 0, 500, 1000, 2000])',
    '    if bonus:',
    '        add_gold(bonus)',
    '    log("         *** 가챠: %s -> %s 클래스 (트로피 -%d, 보너스 골드 %d)"',
    '        % (GACHA_CARS[no], cls, cost, bonus))',
    '    b["remainTrophyCnt"] = PLAYER["trophyCnt"]',
    '    b["carSeq"] = no + 1',
    '    b["carClass"] = cls',
    '    b["itemNo"] = 0',
    '    b["goldAmt"] = bonus',
    '    return b',
    '',
    '',
    '# --- 차량 되팔기(보상 판매) -------------------------------------------',
    '# 헌 차를 넘기고 새 차를 싸게 산다. 클라이언트는 우리가 준 표에서',
    '#   같은 등급 줄의 carClassValue + 각 항목이 (레벨+1) 인 줄의 값',
    '# 을 더해 할인폭을 만든다(TradeCarValueDB.GetDiscountTrophy).',
    '# 그래서 등급마다 레벨 1~4 짜리 줄을 넉 줄씩 준다.',
    'TRADE_CLASS_VALUE = {"C": 0, "B": 14, "A": 50, "S": 120, "R": 200}',
    'TRADE_LEVEL_VALUE = {1: 0, 2: 5, 3: 10, 4: 20}',
    '',
    '',
    'def ep_tradelist(req):',
    '    b = auto("/user/car/compensate")',
    '    rows = []',
    '    for cls, cv in TRADE_CLASS_VALUE.items():',
    '        for lv, lvv in sorted(TRADE_LEVEL_VALUE.items()):',
    '            rows.append({',
    '                "carClass": cls, "carClassTrophy": cv,',
    '                "carAccel": lv, "carAccelTrophy": lvv,',
    '                "carSpeed": lv, "carSpeedTrophy": lvv,',
    '                "carSkill": lv, "carSkillTrophy": lvv,',
    '                "carFuleCost": lv, "carFuleCostTrophy": lvv,',
    '            })',
    '    b["compensateCars"] = rows',
    '    return b',
    '',
    '',
    'def _trade_value(no):',
    '    """헌 차 한 대가 트로피로 얼마인가."""',
    '    v = TRADE_CLASS_VALUE.get(CAR_CLASS.get(no, "C"), 0)',
    '    for k in ("carAccel", "carSpeed", "carFuleCost"):',
    '        v += TRADE_LEVEL_VALUE.get(TUNE.get((no, k), 0) + 1, 0)',
    '    return v',
    '',
    '',
    'def ep_tradebuy(req):',
    '    """헌 차를 넘기고 새 차를 받는다."""',
    '    no = _pick(req, "carNo")',
    '    junk = _pick(req, "junkCarNo")',
    '    cls = req.get("compensateClass") or CAR_CLASS.get(no, "C")',
    '    b = auto("/shop/car/compensate")',
    '    b["missions"] = []',
    '    if no in CAR_CLASS and junk in OWNED_CARS and junk != no:',
    '        # 값은 **클라이언트 화면과 같은 셈법**으로 매긴다.',
    '        # 화면은 우리가 준 등급표(TRADE_CLASS_VALUE)로 정가를 잡고',
    '        # 헌 차 값을 뺀다. 차값(CAR_COST)으로 매기면 화면에 106 이',
    '        # 떠 놓고 46 만 깎여 어긋난다.',
    '        base = TRADE_CLASS_VALUE.get(cls, CAR_COST.get(no, (0, 0))[1])',
    '        price = max(0, base - _trade_value(junk))',
    '        if PLAYER["trophyCnt"] >= price:',
    '            PLAYER["trophyCnt"] -= price',
    '            OWNED_CARS.discard(junk)',
    '            SHOP_CARS.add(junk)',
    '            for k in ("carAccel", "carSpeed", "carFuleCost"):',
    '                TUNE.pop((junk, k), None)',
    '            OWNED_CARS.add(no)',
    '            SHOP_CARS.discard(no)',
    '            if cls in ("C", "B", "A", "S", "R"):',
    '                CAR_CLASS[no] = cls',
    '            log("         *** 되팔기: %d번 넘기고 %d번 %s 획득 (트로피 -%d)"',
    '                % (junk, no, cls, price))',
    '    b["remainTrophyCnt"] = PLAYER["trophyCnt"]',
    '    b["carSeq"] = no + 1',
    '    return b',
    '',
    '',
    'def ep_selectchar(req):',
    '    no = _pick(req, "characterNo")',
    '    if 1 <= no <= DRIVER_COUNT:',
    '        PLAYER["characterNo"] = no',
    '        log("         *** 드라이버 선택: %d" % no)',
    '    return auto("/user/character/select")',
    '',
    '',
    old,
    '    "/user/car/select": ep_selectcar,',
    '    "/user/character/select": ep_selectchar,',
    '    "/user/car/tune": ep_tunecar,',
    '    "/user/car/upgrade": ep_upgradecar,',
    '    "/shop/car/buy": ep_buycar2,',
    '    "/shop/car/unlock": ep_unlockcar,',
    '    "/shop/car/unlockbuy": ep_unlockbuycar,',
    '    "/tire/present/list": ep_presentlist,',
    '    "/tire/present/recv": ep_presentrecv,',
    '    "/tire/present/recvAll": ep_presentrecv,',
    '    "/ranking/current/list": ep_ranklist,',
    '    "/ranking/previous/list": ep_prevranklist,',
    '    "/invitation/list": ep_invitelist,',
    '    "/invitation/invite": ep_invite,',
    '    "/shop/billing/raven/register": ep_billregister,',
    '    "/shop/billing/raven/confirm": ep_billconfirm,',
    '    "/shop/car/gacha": ep_gacha,',
    '    "/user/car/compensate": ep_tradelist,',
    '    "/shop/car/compensate": ep_tradebuy,',
])
assert old in s, 'ROUTES 표를 못 찾았다'
s = s.replace(old, new, 1)

# 게임 시작 요청에도 고른 차가 실려 온다. 그때도 기억해 둔다.
old = 'def ep_gamestart(req):\n    Session.race_value += 1'
new = 'def ep_gamestart(req):\n    Session.race_value += 1\n' + '\n'.join([
    '    no = req.get("carNo")',
    '    if isinstance(no, int) and no in OWNED_CARS:',
    '        PLAYER["carNo"] = no',
    '        PLAYER["carClass"] = CAR_CLASS.get(no, "C")',
    '        seq = req.get("carSeq")',
    '        if isinstance(seq, int) and seq > 0:',
    '            PLAYER["carSeq"] = seq',
])
assert old in s, 'ep_gamestart 를 못 찾았다'
s = s.replace(old, new, 1)

# --- 6. 요청 본문 한 겹 벗기기 ---------------------------------------------
# 클라이언트는 {"gameStartReq": {...}} 처럼 한 겹 싸서 보낸다.
# 지금까지 핸들러들이 바깥 껍데기에서 carNo/trophyCnt 를 찾고 있어서
# 차 선택도, 골드 교환량도, 차 구매도 전부 못 읽고 있었다.
old = '            resp = fn(req) if fn else auto(path)'
new = '            resp = fn(unwrap(req)) if fn else auto(path)'
assert old in s, '핸들러 호출부를 못 찾았다'
s = s.replace(old, new, 1)

old = 'class H(socketserver.BaseRequestHandler):'
new = '\n'.join([
    'def unwrap(req):',
    '    """{"xxxReq": {...}} 한 겹을 벗겨 안쪽 dict 를 돌려준다."""',
    '    if isinstance(req, dict) and len(req) == 1:',
    '        v = list(req.values())[0]',
    '        if isinstance(v, dict):',
    '            return v',
    '    return req',
    '',
    '',
    old,
])
assert old in s
s = s.replace(old, new, 1)

# --- 지난주 순위 팝업 --------------------------------------------------------
# 로그인 응답의 newWeek 가 참일 때만 뜬다(주가 바뀐 그 한 번).
# 서버가 주를 기억하지 않으니 환경변수로 열어 둔다: CHA_NEWWEEK=1
old = '"takeTrophy": False, "newWeek": False,'
new = '"takeTrophy": False,\n' \
      '              "newWeek": os.environ.get("CHA_NEWWEEK") == "1",'
assert old in s, '로그인 응답의 newWeek 를 못 찾았다'
s = s.replace(old, new, 1)

# --- 7. 교환은 exchangeNo 로 고른다 ------------------------------------------
# 클라이언트는 트로피 수가 아니라 **자리 번호**를 보낸다.
#   GoldMain.OnBuyGold_1~6  -> 3, 4, 9, 10, 11, 12
#   ShopTire.OnBuyTire_1~6  -> 1, 2, 5, 6, 7, 8
# 트로피 수로 짐작하면 엉뚱한 줄이 걸려, 화면은 "골드 100000개 구매"라 하는데
# 실제로는 2500 만 들어오는 식으로 어긋난다.
old = '''def _amount(req, table):
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
    return table[0]'''
new = '''# 자리 번호 -> (트로피값, 받는 양)
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
    return table[0]'''
assert old in s, '_amount 를 못 찾았다'
s = s.replace(old, new, 1)

# --- 8. 상한 적용 · 교환표 바로잡기 -----------------------------------------
# 타이어는 게스트 제한과 무관하다(m_IsEnableGuestMode 는 꺼져 있다).
# 99 는 그냥 내가 정했던 값이라 게임 자체 상한(999)까지 올린다.
# 다만 **999 로 두면 안 된다.** InviteUnit.OnInvite 가
#   tireCount < maxAllowHaveTireCount(999)
# 일 때만 초대를 허용하고, 아니면 "보유 타이어가 최대여서…" 를 띄우고 만다.
# 900 으로 둔다. 서버는 타이어를 깎지 않으므로 앱을 껐다 켜면
# /user/info/get 이 늘 900 을 돌려줘 그 판에 쓴 만큼이 도로 채워진다.
old = '"nickName": "Racer", "gold": 999999, "trophyCnt": 9999, "tireCnt": 99,'
new = '"nickName": "Racer", "gold": 999999, "trophyCnt": 9999, "tireCnt": 900,'
assert old in s, '타이어 기본값 줄을 못 찾았다'
s = s.replace(old, new, 1)

s = s.replace('import socketserver, threading, datetime, json, sys, os, base64, secrets',
              'import socketserver, threading, datetime, json, sys, os, base64, secrets, time, random', 1)

# 클라이언트가 실제로 쓰는 교환표. GoldMain.OnBuyGold_N / ShopTire.OnBuyTire_N 에
# 박혀 있는 값 그대로다. 서버가 다르게 주면 표시와 지급이 어긋난다.
old = 'GOLD_EXCHANGE = [(1, 3000), (5, 18000), (10, 40000), (30, 130000), (50, 230000)]'
new = 'GOLD_EXCHANGE = [(5, 2500), (10, 6000), (20, 14000), (30, 24000),\n' \
      '                 (50, 45000), (100, 100000)]'
assert old in s, '골드 교환표를 못 찾았다'
s = s.replace(old, new, 1)

old = 'TIRE_EXCHANGE = [(1, 1), (5, 6), (10, 13), (30, 42), (50, 75)]'
new = 'TIRE_EXCHANGE = [(5, 5), (10, 12), (20, 30), (30, 50), (50, 90), (100, 200)]'
assert old in s, '타이어 교환표를 못 찾았다'
s = s.replace(old, new, 1)

# 늘어나는 곳은 전부 상한을 거치게 한다
for old, new in (
        ('        PLAYER["gold"] += gain', '        add_gold(gain)'),
        ('        PLAYER["tireCnt"] += gain', '        add_tire(gain)'),
        ('    PLAYER["gold"] += got', '    add_gold(got)'),
        ('    PLAYER["tireCnt"] += got', '    add_tire(got)'),
):
    assert old in s, '상한을 걸 자리를 못 찾았다: %s' % old.strip()
    s = s.replace(old, new, 1)

# --- 9. 상태를 파일 하나에 담는다 -------------------------------------------
# chastate.json 이 서버로 갈 데이터 전부다. 서버가 켜질 때 읽고, 값이 바뀌면
# 바로 쓴다. 런처(chalauncher.py)가 그 파일을 고치면 **다음 요청부터** 반영된다.
# 나중에 오라클로 옮기면 이 파일이 그대로 계정 하나의 저장 내용이 된다.
old = 'ROUTES = {'
new = '\n'.join([
    'import chastate as _S',
    '',
    'STATE = _S.load()',
    '_state_mtime = [0.0]',
    '_state_last = [""]',
    '',
    '',
    'def _state_apply():',
    '    """파일 -> 서버 안의 살아 있는 값들."""',
    '    st = STATE',
    '    p = st["player"]',
    '    PLAYER["nickName"] = p.get("nickName", "Racer")',
    '    PLAYER["gold"] = int(p.get("gold", 0))',
    '    PLAYER["trophyCnt"] = int(p.get("trophy", 0))',
    '    PLAYER["tireCnt"] = int(p.get("tire", 0))',
    '    PLAYER["carNo"] = _S.NAME_TO_NO.get(p.get("car", "AVEO"), 1)',
    '    PLAYER["carSeq"] = PLAYER["carNo"] + 1',
    '    PLAYER["characterNo"] = int(p.get("driver", 1))',
    '',
    '    r = st["records"]',
    '    for a, b in (("bestScore", "bestScore"),',
    '                 ("bestScoreHurdle", "bestScoreHurdle"),',
    '                 ("prevScore", "prevScore"),',
    '                 ("maxDistance", "maxDistance"),',
    '                 ("playCount", "playCount")):',
    '        PLAYER[b] = int(r.get(a, 0))',
    '    PLAYER["inviteCnt"] = int(st["invite"].get("count", 0))',
    '',
    '    # 등급은 시작 등급 위에 파일 값을 덮는다',
    '    for name, cls in st.get("carClass", {}).items():',
    '        no = _S.NAME_TO_NO.get(name)',
    '        if no in CAR_CLASS and cls in ("C", "B", "A", "S", "R"):',
    '            CAR_CLASS[no] = cls',
    '    PLAYER["carClass"] = CAR_CLASS.get(PLAYER["carNo"], "C")',
    '',
    '    OWNED_CARS.clear()',
    '    for name in st.get("carsOwned", []):',
    '        no = _S.NAME_TO_NO.get(name)',
    '        if no in CAR_CLASS:',
    '            OWNED_CARS.add(no)',
    '    SHOP_CARS.clear()',
    '    SHOP_CARS.update(set(CAR_CLASS) - OWNED_CARS)',
    '',
    '    TUNE.clear()',
    '    keymap = {"accel": "carAccel", "speed": "carSpeed", "oil": "carFuleCost"}',
    '    for name, t in st.get("carTune", {}).items():',
    '        no = _S.NAME_TO_NO.get(name)',
    '        if no is None:',
    '            continue',
    '        for k, v in (t or {}).items():',
    '            if k in keymap and int(v or 0):',
    '                TUNE[(no, keymap[k])] = max(0, min(3, int(v)))',
    '',
    '    DRIVERS_OWNED.clear()',
    '    DRIVERS_OWNED.update(int(d) for d in st.get("driversOwned", [])',
    '                         if 1 <= int(d) <= DRIVER_COUNT)',
    '    if not DRIVERS_OWNED:',
    '        DRIVERS_OWNED.add(1)',
    '',
    '    kind = {"tire": "001", "trophy": "002", "gold": "003"}',
    '    del PRESENTS[:]',
    '    for i, pr in enumerate(st.get("presents", [])):',
    '        PRESENTS.append({"presentSeq": i + 1, "accountSeq": 0,',
    '                         "presentType": kind.get(pr.get("type"), "001"),',
    '                         "presentQty": int(pr.get("count", 1)),',
    '                         "sender": pr.get("from", "")})',
    '',
    '',
    'def _state_gather():',
    '    """서버 안의 값 -> 파일 모양."""',
    '    st = STATE',
    '    st["player"].update({',
    '        "nickName": PLAYER["nickName"],',
    '        "gold": PLAYER["gold"], "trophy": PLAYER["trophyCnt"],',
    '        "tire": PLAYER["tireCnt"],',
    '        "car": _S.NO_TO_NAME.get(PLAYER["carNo"], "AVEO"),',
    '        "driver": PLAYER["characterNo"],',
    '    })',
    '    st["records"].update({',
    '        "bestScore": PLAYER["bestScore"],',
    '        "bestScoreHurdle": PLAYER["bestScoreHurdle"],',
    '        "prevScore": PLAYER["prevScore"],',
    '        "maxDistance": PLAYER["maxDistance"],',
    '        "playCount": PLAYER["playCount"],',
    '    })',
    '    st["invite"]["count"] = PLAYER["inviteCnt"]',
    '    st["carsOwned"] = [_S.NO_TO_NAME[n] for n in sorted(OWNED_CARS)',
    '                       if n in _S.NO_TO_NAME]',
    '    st["carClass"] = dict((_S.NO_TO_NAME[n], c) for n, c in CAR_CLASS.items()',
    '                          if n in _S.NO_TO_NAME',
    '                          and c != _S.START_CLASS.get(_S.NO_TO_NAME[n]))',
    '    back = {"carAccel": "accel", "carSpeed": "speed", "carFuleCost": "oil"}',
    '    tune = {}',
    '    for (no, k), v in TUNE.items():',
    '        nm = _S.NO_TO_NAME.get(no)',
    '        if nm and k in back:',
    '            tune.setdefault(nm, {})[back[k]] = v',
    '    st["carTune"] = tune',
    '    st["driversOwned"] = sorted(DRIVERS_OWNED)',
    '    label = {"001": "tire", "002": "trophy", "003": "gold"}',
    '    st["presents"] = [{"type": label.get(p["presentType"], "tire"),',
    '                       "count": p["presentQty"],',
    '                       "from": p.get("sender", "")} for p in PRESENTS]',
    '    return st',
    '',
    '',
    'def _state_pull():',
    '    """런처가 파일을 고쳤으면 다시 읽는다."""',
    '    try:',
    '        m = os.path.getmtime(_S.STATE_PATH)',
    '    except OSError:',
    '        return',
    '    if m <= _state_mtime[0]:',
    '        return',
    '    _state_mtime[0] = m',
    '    fresh = _S.load()',
    '    STATE.clear()',
    '    STATE.update(fresh)',
    '    _state_apply()',
    '    _state_last[0] = json.dumps(STATE, ensure_ascii=False, sort_keys=True)',
    '    log("         *** 상태 파일을 다시 읽었다")',
    '',
    '',
    'def _state_push():',
    '    """값이 바뀌었으면 파일에 남긴다."""',
    '    st = _S.clamp(_state_gather())',
    '    blob = json.dumps(st, ensure_ascii=False, sort_keys=True)',
    '    if blob == _state_last[0]:',
    '        return',
    '    _state_last[0] = blob',
    '    try:',
    '        _S.save(st)',
    '        _state_mtime[0] = os.path.getmtime(_S.STATE_PATH)',
    '    except OSError as e:',
    '        log("  [상태 저장 실패] %r" % e)',
    '',
    '',
    'def ep_notice(req):',
    '    """공지사항. 내용은 상태 파일에서 온다."""',
    '    b = auto("/service/notice/get")',
    '    n = STATE.get("notice", {})',
    '    for k in ("notice", "noticeMessage", "message", "content"):',
    '        b[k] = n.get("body", "")',
    '    for k in ("noticeTitle", "title"):',
    '        b[k] = n.get("title", "")',
    '    for k in ("noticeUrl", "url"):',
    '        b[k] = n.get("url", "")',
    '    return b',
    '',
    '',
    old,
])
assert old in s, 'ROUTES 표를 못 찾았다'
s = s.replace(old, new, 1)

# 드라이버 목록은 파일이 정한 만큼만 준다(빼면 캐릭터 상점에서 사야 한다)
old = '''        for no in range(int(__import__('os').environ.get('CHA_DRV','12'))):'''
new = '''        for no in sorted(DRIVERS_OWNED):
            no -= 1'''
assert old in s, '드라이버 목록 반복문을 못 찾았다'
s = s.replace(old, new, 1)

old = 'DRIVER_COUNT = 12'
new = 'DRIVER_COUNT = 12\n\n# 보유 드라이버(1~12). 상태 파일이 정한다.\nDRIVERS_OWNED = set(range(1, 13))'
assert old in s
s = s.replace(old, new, 1)

# 이름 바꾸기를 저장한다.
# 클라이언트는 소셜 계정 이름을 그대로 보낸다. 게임 안에 이름을 바꾸는
# 화면은 없지만, 무엇이 오든 세이브에 남아야 다음에 켰을 때 유지된다.
old = 'def ep_notice(req):'
new = """def ep_updateuserinfo(req):
    \"\"\"이름 바꾸기. 빈 이름이면 지금 이름을 지킨다.\"\"\"
    nm = (req or {}).get("nickName")
    if isinstance(nm, str) and nm.strip():
        nm = nm.strip()[:16]
        if nm != PLAYER["nickName"]:
            log("         *** 이름 바꿈: %s -> %s" % (PLAYER["nickName"], nm))
        PLAYER["nickName"] = nm
    b = auto("/user/info/update")
    b["nickName"] = PLAYER["nickName"]
    return b


""" + old
assert old in s, 'ep_notice 를 못 찾았다'
s = s.replace(old, new, 1)

# 아이템과 캐릭터 상점을 붙인다.
#
# 아이템 값은 **클라이언트에 박혀 있다**(Generic_ShopMain/eItemCost).
# 서버가 다른 값을 매기면 화면과 어긋나므로 그대로 옮겨 쓴다.
# 캐릭터 값은 어디에도 없어서 우리가 정한다(아래 주석 참조).
old = 'def ep_notice(req):'
new = """# CRSystem/eItemCode 그대로. 8~12 는 공구상자 안쪽 코드라 상점에 안 나온다.
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
    \"\"\"아이템 한 개 구매. 값은 클라이언트 표와 같다.\"\"\"
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
    \"\"\"캐릭터 구매. 트로피가 모자라면 골드로 받는다.

    응답 클래스에 골드 칸이 없어서 화면의 골드는 다음 새로고침 때 맞는다.\"\"\"
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


""" + old
assert old in s, 'ep_notice 를 못 찾았다'
s = s.replace(old, new, 1)

# 공지 경로와 상태 훅을 건다
old = '    "/shop/billing/raven/confirm": ep_billconfirm,'
new = old + '\n    "/service/notice/get": ep_notice,'\
          + '\n    "/shop/item/list": ep_itemlist,'\
          + '\n    "/shop/item/buy": ep_buyitem,'\
          + '\n    "/play/item/use": ep_useitem,'\
          + '\n    "/shop/character/buy": ep_buycharacter,'\
          + '\n    "/user/info/update": ep_updateuserinfo,'
assert old in s
s = s.replace(old, new, 1)

# 아이템 개수를 상태 파일과 잇는다
old = "    DRIVERS_OWNED.clear()"
new = """    ITEMS.clear()
    _codes = dict((v, k) for k, v in ITEM_NAME.items())
    for _n, _v in (st.get("items") or {}).items():
        if _n in _codes:
            ITEMS[_codes[_n]] = max(0, min(ITEM_MAX, int(_v or 0)))

""" + old
assert old in s
s = s.replace(old, new, 1)

old = '    st["driversOwned"] = sorted(DRIVERS_OWNED)'
new = ('    st["items"] = dict((ITEM_NAME[c], int(ITEMS.get(c, 0)))\n'
       '                       for c in ITEM_CODES)\n') + old
assert old in s
s = s.replace(old, new, 1)

old = '            fn = ROUTES.get(path)\n            resp = fn(unwrap(req)) if fn else auto(path)'
new = '            _state_pull()\n' + old
assert old in s, '핸들러 호출부를 못 찾았다'
s = s.replace(old, new, 1)

old = '            log("         RES: %s" % out[:260])'
new = old + '\n            _state_push()'
assert old in s
s = s.replace(old, new, 1)

# 서버가 켜질 때 파일 내용을 반영한다
old = 'class H(socketserver.BaseRequestHandler):'
new = '_state_apply()\n_state_mtime[0] = os.path.getmtime(_S.STATE_PATH) \\\n    if os.path.exists(_S.STATE_PATH) else 0.0\n_state_last[0] = json.dumps(STATE, ensure_ascii=False, sort_keys=True)\n\n\n' + old
assert old in s
s = s.replace(old, new, 1)

io.open(p, 'w', encoding='utf-8').write(s)
ast.parse(s)
print('carfix: 차 %d대 / 드라이버 1~12 / info 중첩 (구문 OK)' % len(CAR_CLASS))
