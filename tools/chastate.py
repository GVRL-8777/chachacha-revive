# -*- coding: utf-8 -*-
"""서버로 갈 데이터를 **파일 하나**에 담는다.

지금은 사설 서버가 이 파일을 읽어 쓰고, 나중에 오라클로 옮기면 그때는
이 파일이 그대로 계정 하나의 저장 내용이 된다. 그래서 형식은
"게임이 쓰는 말"이 아니라 **사람이 읽고 고칠 수 있는 말**로 적는다.

  · 자동차는 번호가 아니라 이름으로 적는다 (AVEO, PRIUS …)
  · 아이템도 코드가 아니라 이름으로 적는다 (BestOil, Nos …)
  · 없는 항목은 기본값으로 채워 주므로 파일을 손으로 깎아 써도 된다

  from chastate import load, save
  st = load()
  st["player"]["gold"] = 1234
  save(st)
"""
import copy
import io
import json
import os

CODE = os.path.dirname(os.path.abspath(__file__))
# 코드는 tools/ 안이지만 **상태 파일은 작업 폴더(그 위)** 에 있다.
ROOT = os.path.dirname(CODE)
STATE_PATH = os.path.join(ROOT, 'chastate.json')

# 서버 carNo(= CarDataBase 의 CarIndex + 1) -> 이름 · 시작 등급
CARS = [
    (1, "AVEO", "C"), (2, "PRIUS", "B"), (3, "Challenger", "B"),
    (4, "Evoque", "B"), (5, "CTS", "B"), (6, "Boxster", "B"),
    (7, "GTR", "A"), (8, "Mustang", "A"), (9, "McLaren", "A"),
    (10, "SSANENG", "C"), (11, "CAT", "B"), (12, "block", "B"),
    (13, "Hummer", "A"), (14, "Mini", "B"), (15, "Falcon", "A"),
    (16, "Choper", "A"), (17, "Ne88", "A"), (18, "Poli", "A"),
    (19, "Roy", "A"), (20, "Amber", "A"), (21, "Lamborghini", "S"),
    (22, "helly", "A"), (23, "C7", "S"), (24, "Taegeuk", "B"),
    (25, "Astonmartin", "S"), (26, "Cyclone", "C"), (27, "Hurricane", "C"),
    (28, "Phoenix", "C"), (29, "Hardroad", "B"), (30, "Heavysuricar", "C"),
    (31, "Superemperor", "C"), (32, "Thunder", "C"), (33, "Unicorn", "S"),
    (34, "Meteor", "A"), (35, "Archangel", "S"), (36, "W3", "S"),
    (37, "Blitz", "S"), (38, "Troy", "C"),
]
# newcar.py 로 새로 넣은 차들. 파일이 있으면 목록에 붙는다.
def _load_newcars():
    import io as _io
    import json as _json
    p = os.path.join(ROOT, 'newcars.json')
    if not os.path.exists(p):
        return []
    try:
        return _json.load(_io.open(p, encoding='utf-8'))
    except Exception:
        return []


NEW_CARS = _load_newcars()
for _c in NEW_CARS:
    if not any(x[0] == _c['carNo'] for x in CARS):
        CARS.append((_c['carNo'], _c['name'], _c['class']))
CARS.sort(key=lambda x: x[0])

NAME_TO_NO = dict((n, i) for i, n, _c in CARS)
NO_TO_NAME = dict((i, n) for i, n, _c in CARS)
START_CLASS = dict((n, c) for _i, n, c in CARS)

# 드라이버는 1~12. 이름은 게임 안 표기를 그대로 옮긴 것이다.
# 이름은 게임 텍스트표의 Char1~Char8 그대로다. 9~12 는 슬롯을 늘리며
# 붙인 자리라 원작에 이름이 없다(원작은 8명까지).
DRIVERS = [
    (1, "도 강현"), (2, "Sarah Cha"), (3, "빈 경유"), (4, "나 연비"),
    (5, "김준현"), (6, "갸루상"), (7, "앵그리성호"), (8, "정신이"),
    (9, "나정비"), (10, "안별이"), (11, "쌈바여인"), (12, "한이 가희"),
]

# eItemCode 순서 그대로. 값은 보유 개수.
ITEMS = ["BestOil", "Nos", "FrontSensor", "ToolBox",
         "OneShot", "Emergency", "Turbo"]
ITEM_LABEL = {
    "BestOil": "고급휘발유", "Nos": "부스터", "FrontSensor": "전방감지기",
    "ToolBox": "강화공구상자", "OneShot": "물소원샷",
    "Emergency": "비상연료", "Turbo": "터보",
}

MAX_GOLD = 999999999
MAX_TROPHY = 999999999
MAX_TIRE = 998          # 999 면 클라이언트가 초대를 막는다


def default():
    """아무것도 없을 때의 시작 상태."""
    return {
        "version": 1,
        "preset": "",       # 어느 빌드의 세이브인가

        "player": {
            "nickName": "Racer",
            "gold": 999999,
            "trophy": 9999,
            "tire": 900,
            "car": "AVEO",              # 지금 타는 차 (이름)
            "driver": 1,                # 지금 고른 드라이버 (1~12)
        },

        "records": {
            "bestScore": 0,             # 주행 모드 최고 점수
            "bestScoreHurdle": 0,       # 장애물 모드 최고 점수
            "prevScore": 0,             # 지난주 기록
            "maxDistance": 0,
            "playCount": 0,
        },

        # 보유 자동차. 여기서 빼면 자동차 샵에 매물로 뜬다.
        "carsOwned": [n for _i, n, _c in CARS
                      if n not in ("Lamborghini", "C7", "Astonmartin",
                                   "Unicorn", "Meteor")],
        # 등급을 올렸으면 여기에 적는다. 없으면 시작 등급.
        "carClass": {},
        # 튜닝 단계 0~3. {"AVEO": {"accel": 2, "speed": 0, "oil": 1}}
        "carTune": {},

        "driversOwned": [d for d, _n in DRIVERS],

        # --- 아직 서버를 안 붙인 것들. 값은 미리 여기에 담아 둔다 ---
        "items": dict((k, 0) for k in ITEMS),
        "skills": [],                   # [{"skill": 13, "car": "AVEO",
                                        #   "level": 1, "equipped": true}]

        "invite": {
            "count": 0,                 # 누적 초대 횟수 (30·50회 보상)
            "sent": [],                 # 이미 초대한 상대
        },

        "dormancy": {
            "days": 0,                  # 며칠 쉬었는가
            "rewardTaken": False,
        },

        "presents": [                   # 수신함
            {"type": "tire", "count": 5, "from": "지나가는 행인"},
        ],

        "notice": {
            "title": "공지사항",
            "body": "",
            "url": "",
        },

        "flags": {
            "newWeek": False,           # 켜면 지난주 순위 팝업이 뜬다
        },
    }


# --- 프리셋 -----------------------------------------------------------
# 빌드마다 다른 시작 상태를 담습니다. `preset` 값이 빌드와 다르면 로컬 APK 가
# 기기에 있던 세이브를 버리고 이 상태로 새로 시작합니다(다른 프리셋을 덮어
# 깔았을 때 앞의 진행이 남아 있으면 곤란하므로).
def preset_rich(name='malchiki-mazhory'):
    """부잣집 도련님 — 다 가진 상태로 시작합니다."""
    st = default()
    st['preset'] = name
    st['player'].update({'nickName': '도련님', 'gold': MAX_GOLD,
                         'trophy': MAX_TROPHY, 'tire': MAX_TIRE})
    st['carsOwned'] = [n for _i, n, _c in CARS]
    st['driversOwned'] = [d for d, _n in DRIVERS]
    # 강화공구상자만 99가 안 됩니다 — 클라이언트가 Mathf.Clamp(값, 0, 1) 로
    # 0/1 만 인정합니다(한 번에 한 개만 드는 물건입니다).
    st['items'] = dict((k, 1 if k == 'ToolBox' else 99) for k in ITEMS)
    return st


def preset_scratch(name='bespontovnyj-pirozhok'):
    """다시 처음부터 — 아베오 한 대와 기본 드라이버만."""
    st = default()
    st['preset'] = name
    st['player'].update({'nickName': 'Racer', 'gold': 50000,
                         'trophy': 10, 'tire': 900})
    st['carsOwned'] = ['AVEO']
    st['carClass'] = {}
    st['carTune'] = {}
    st['driversOwned'] = [1]
    st['items'] = dict((k, 0) for k in ITEMS)
    st['presents'] = []
    return st


# 프리셋은 이제 **세이브 파일의 밑그림**입니다. APK 종류가 아닙니다.
PRESETS = {
    'bespontovnyj-pirozhok': preset_scratch,
    'malchiki-mazhory': preset_rich,
}
# 화면에 보일 이름. 판 이름(rag · rich 따위)은 걷어내고 번호로만 부릅니다.
PRESET_LABEL = {
    'bespontovnyj-pirozhok': '프리셋 01 · 처음부터',
    'malchiki-mazhory': '프리셋 02 · 전부 해금',
}


def preset(name):
    if name not in PRESETS:
        raise SystemExit('그런 프리셋이 없습니다: %s (있는 것: %s)'
                         % (name, ' · '.join(sorted(PRESETS))))
    return PRESETS[name](name)


def _merge(base, over):
    """기본값 위에 파일 내용을 덮는다. 없는 키는 기본값이 남는다."""
    out = copy.deepcopy(base)
    if not isinstance(over, dict):
        return out
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path=STATE_PATH):
    if not os.path.exists(path):
        st = default()
        save(st, path)
        return st
    try:
        with io.open(path, encoding='utf-8') as f:
            raw = json.load(f)
    except Exception:
        return default()
    return _merge(default(), raw)


def save(state, path=STATE_PATH):
    """같은 폴더에 임시로 쓰고 갈아치운다(쓰다 만 파일이 남지 않게)."""
    tmp = path + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write('\n')
    if os.path.exists(path):
        os.remove(path)
    os.rename(tmp, path)


def clamp(state):
    """상한을 넘겼으면 도로 맞춘다."""
    p = state["player"]
    p["gold"] = max(0, min(MAX_GOLD, int(p.get("gold", 0))))
    p["trophy"] = max(0, min(MAX_TROPHY, int(p.get("trophy", 0))))
    p["tire"] = max(0, min(MAX_TIRE, int(p.get("tire", 0))))
    return state


if __name__ == '__main__':
    st = load()
    clamp(st)
    save(st)
    print('%s\n  보유 차 %d대 / 드라이버 %d명 / 골드 %d / 트로피 %d / 타이어 %d'
          % (STATE_PATH, len(st["carsOwned"]), len(st["driversOwned"]),
             st["player"]["gold"], st["player"]["trophy"], st["player"]["tire"]))
