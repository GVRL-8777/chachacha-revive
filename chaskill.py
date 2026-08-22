# -*- coding: utf-8 -*-
"""스킬 표 — `DataBase/SkillDataBase` 를 읽습니다.

스킬은 **차마다 따로** 붙습니다. 한 차에 원본(Origin) 슬롯 셋과 추가
(Addtion) 슬롯이 있고, 레벨은 1~3 입니다.

실측한 것

  · 표에 든 스킬은 **열셋**입니다(`skill001`~`skill013`).
    글 표에는 `skill014` · `skill015` 도 있지만 표에 없어 게임이 안 씁니다.
  · 1~3 번은 Origin 슬롯이고 값이 0 입니다(차를 R 로 올리면 딸려 옵니다).
  · 4~13 번은 Addtion 슬롯이고 골드 10,000 또는 트로피 50 입니다.
  · 올리는 값은 전부 15,000 -> 20,000 골드입니다.

응답 모양도 실측입니다(`NetRecive.CarSkillList` 의 필드).

    /skill/get/list  -> {"skillList": [{skillNo, carNo, skillLevel,
                                        equipFlag, skillType}]}
    /skill/buy       -> {remainGoldAmount, remainTrophyCount}
    /skill/equip     -> {}
    /skill/upgrade   -> {skillLevel}

**골드 칸 이름이 다릅니다.** 차·아이템 쪽은 `remainGoldAmt` 인데 스킬은
`remainGoldAmount` 입니다. 헷갈리면 화면 숫자가 안 바뀝니다.
"""
import io
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join('assets', 'bin', 'Data')
ASSET = 'd3799560ce23f7a4eaae7a90466f157e'      # DataBase/SkillDataBase
SLOT_CODE = {'Origin': '001', 'Addtion': '002'}

_CACHE = [None]


def _read(tree):
    from sfparse import parse
    p = os.path.join(tree, DATA, ASSET)
    raw = io.open(p, 'rb').read()
    meta = parse(p)
    rec = [o for o in meta['objects'] if o['path_id'] == 1][0]
    st = meta['data_offset'] + rec['start']
    b = raw[st:st + rec['size']]
    n = struct.unpack_from('<i', b, 0)[0]
    off = 4 + n
    off += (-off) % 4
    tlen = struct.unpack_from('<i', b, off)[0]
    return json.loads(b[off + 4:off + 4 + tlen].decode('utf-8'))


def table(tree='x77'):
    """[{no, code, slot, slotCode, max, costType, cost, upgrade}] 번호순."""
    if _CACHE[0] is not None:
        return _CACHE[0]
    try:
        d = _read(tree)
    except Exception:
        _CACHE[0] = []
        return []
    arr = (d.get('SkillDataBase') or d).get('SkillDataArray') or []
    out = []
    for s in arr:
        bc = s.get('BuyCost') or {}
        out.append({
            'no': s['Index'], 'code': s.get('NameCode') or '',
            'slot': s.get('SlotType') or '',
            'slotCode': SLOT_CODE.get(s.get('SlotType') or '', '002'),
            'max': s.get('MaxLevel') or 3,
            'costType': bc.get('CostType') or 'Gold',
            'cost': bc.get('Cost') or 0,
            'upgrade': s.get('UpgradeCost') or [],
        })
    out.sort(key=lambda x: x['no'])
    _CACHE[0] = out
    return out


def names(tree='x77'):
    """`skill001` -> `충격감소`. 글 표의 `_NoneLv` 쪽이 레벨 없는 이름입니다."""
    out = {}
    try:
        import chadrv
        _p, _raw, text, _t, _l = chadrv._systext(tree)
    except Exception:
        return out
    for ln in text.splitlines():
        if '=' not in ln:
            continue
        k, v = ln.split('=', 1)
        k = k.strip()
        if k.startswith('skill') and k.endswith('_NoneLv'):
            out[k[:-7]] = v.strip()
    return out


def meta(tree='x77'):
    """화면이 쓰는 표 — 이름까지 붙여서."""
    nm = names(tree)
    out = []
    for s in table(tree):
        r = dict(s)
        r['name'] = nm.get(s['code']) or s['code']
        out.append(r)
    return out


# ------------------------------------------------------------------ 세이브
def normalize(rows, tree='x77'):
    """세이브의 `skills` 를 다듬습니다. 모르는 번호와 넘친 레벨을 걷어냅니다."""
    tb = dict((s['no'], s) for s in table(tree))
    out, seen = [], set()
    for r in rows or []:
        try:
            car = int(r.get('car') or r.get('carNo') or 0)
            no = int(r.get('no') or r.get('skillNo') or 0)
        except Exception:
            continue
        if no not in tb or car <= 0 or (car, no) in seen:
            continue
        seen.add((car, no))
        lv = int(r.get('lv') or r.get('skillLevel') or 1)
        lv = max(1, min(tb[no]['max'], lv))
        out.append({'car': car, 'no': no, 'lv': lv,
                    'eq': bool(r.get('eq') or r.get('equip'))})
    return sorted(out, key=lambda x: (x['car'], x['no']))


def as_list(rows, car=None, tree='x77'):
    """클라이언트가 읽는 모양으로. `car` 를 주면 그 차 것만."""
    tb = dict((s['no'], s) for s in table(tree))
    out = []
    for r in normalize(rows, tree):
        if car and r['car'] != car:
            continue
        out.append({'skillNo': r['no'], 'carNo': r['car'],
                    'skillLevel': r['lv'],
                    'equipFlag': 'Y' if r['eq'] else 'N',
                    'skillType': tb[r['no']]['slotCode']})
    return out
