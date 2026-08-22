# -*- coding: utf-8 -*-
"""한글화로 넘치는 UILabel 에 줄바꿈 폭(mMaxLineWidth)을 자동으로 넣는다.

배경: 중국판 UI 는 중국어 길이에 맞춰 잡혀 있어, 한국어로 바꾸면 문자열이 평균 두 배
넓어지면서 버튼·상자를 뚫고 나간다. 원문은 그대로 두라는 요구라 라벨 쪽을 고친다.

각 라벨이 쓸 수 있는 폭은 이렇게 구한다.
  1) 조상 GameObject 에 붙은 위젯(UISprite 계열)의 가로 스케일 = 상자 폭
  2) 라벨이 상자 중심에서 밀려 있는 만큼 뺀다
  3) 여백 8% 를 남긴다

mMaxLineWidth 는 화면 로컬 단위와 같은 축척으로 관측된다
(드라이버 설명 라벨 165 / 카드 폭 329 / 초상화 118 -> 남는 폭과 맞아떨어진다).
UILabel 꼬리(텍스트 뒤 64바이트)의 오프셋 0 이며, 크기가 안 변하므로 제자리 수정한다.
"""
import io
import os
import glob
import struct
import sys
from collections import defaultdict

from sfparse import parse
from sfwrite import ALIGN
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile
from scanwidth import Meter, load

CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
OVERLAY = 'overlay'
TEXT_OFF = 72
WIDGETS = ('UISprite', 'UISlicedSprite', 'UITiledSprite', 'UIFilledSprite')
MARGIN = 0.92
APPLY = '--apply' in sys.argv


def script_names():
    p = os.path.join(CN, 'sharedassets0.assets')
    sf = SerializedFile(EndianBinaryReader(io.open(p, 'rb').read()), None)
    out = {}
    for pid, o in sf.objects.items():
        if o.type.name != 'MonoScript':
            continue
        d = o.get_raw_data()
        n = struct.unpack_from('<i', d, 0)[0]
        if 0 < n < 200:
            try:
                out[pid] = d[4:4 + n].decode('utf-8')
            except UnicodeDecodeError:
                pass
    return out


def process(path, names, cn, kr, meter, report):
    try:
        sf = SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)
    except Exception:
        return None
    gname, comps, tr = {}, defaultdict(list), {}
    for q, o in sf.objects.items():
        try:
            if o.type.name == 'GameObject':
                t = o.read_typetree()
                gname[q] = t['m_Name']
                for c in t['m_Component']:
                    v = c[1] if isinstance(c, (list, tuple)) and len(c) == 2 else None
                    if isinstance(v, dict) and v.get('m_PathID'):
                        comps[q].append(v['m_PathID'])
            elif o.type.name == 'Transform':
                tr[q] = o.read_typetree()
        except Exception:
            continue
    if not tr:
        return None

    go_of = {q: t['m_GameObject']['m_PathID'] for q, t in tr.items()}
    t_of = {g: q for q, g in go_of.items()}
    parent = {}
    for q, t in tr.items():
        for c in t.get('m_Children', []):
            parent[c['m_PathID']] = q

    def widget_w(g):
        for c in comps.get(g, []):
            o = sf.objects.get(c)
            if o is None or o.type.name != 'MonoBehaviour':
                continue
            d = o.get_raw_data()
            if len(d) < 20:
                continue
            if names.get(struct.unpack_from('<i', d, 16)[0]) in WIDGETS:
                t = tr.get(t_of.get(g))
                if t:
                    return abs(float(t['m_LocalScale']['x']))
        return None

    def box_for(g):
        """라벨을 감싸는 상자 폭과, 상자 중심에서 라벨이 밀린 거리.

        NGUI 에서는 배경 스프라이트가 부모가 아니라 **형제**인 경우가 많다
        (Button > [Background(UISlicedSprite), Label(UILabel)]).
        그래서 조상을 거슬러 올라가며 그 조상 자신과 **직계 자식들**을 함께 살핀다.
        """
        node = t_of.get(g)
        off, hops = 0.0, 0
        while node is not None and hops < 6:
            gg = go_of[node]
            cands = []
            if gg != g:
                w = widget_w(gg)
                if w:
                    cands.append(w)
            for ch in tr[node].get('m_Children', []):
                cg = go_of.get(ch['m_PathID'])
                if cg is None or cg == g:
                    continue
                w = widget_w(cg)
                if w:
                    cands.append(w)
            cands = [w for w in cands if w > 20]
            if cands:
                return max(cands), abs(off)
            off += float(tr[node]['m_LocalPosition']['x'])
            node = parent.get(node)
            hops += 1
        return None, 0.0

    patched = {}
    for g, cl in comps.items():
        key, lab_pid = None, None
        for c in cl:
            o = sf.objects.get(c)
            if o is None or o.type.name != 'MonoBehaviour':
                continue
            d = o.get_raw_data()
            if len(d) < 20:
                continue
            sn = names.get(struct.unpack_from('<i', d, 16)[0])
            if sn == 'UILocalize':
                n = struct.unpack_from('<i', d, 24)[0]
                if 0 < n < 80:
                    try:
                        key = d[28:28 + n].decode('utf-8')
                    except UnicodeDecodeError:
                        pass
            elif sn == 'UILabel':
                lab_pid = c
        if lab_pid is None or not key or key not in cn or key not in kr:
            continue
        if cn[key] == kr[key]:
            continue
        d = bytearray(sf.objects[lab_pid].get_raw_data())
        n = struct.unpack_from('<i', d, TEXT_OFF)[0]
        t = TEXT_OFF + 4 + ((n + 3) // 4) * 4
        if t + 64 > len(d):
            continue

        # --- 지난번에 이 도구가 손댄 라벨이면 **원래 값으로 되돌린 뒤** 다시 판단한다.
        # 이렇게 해야 기준값을 바꿔가며 몇 번이고 다시 돌려도 결과가 누적되지 않는다.
        base = os.path.basename(path)
        sk = '%s:%d' % (base, lab_pid)
        st = state.get(sk)
        size = abs(float(tr[t_of[g]]['m_LocalScale']['x'])) or 1.0
        if st:
            struct.pack_into('<i', d, t, int(st['w']))
            size = float(st['s'])
            scales[t_of[g]] = None          # 일단 원래 스케일로 되돌린다는 표시
        elif struct.unpack_from('<i', d, t)[0] != 0:
            continue                        # 원래부터 줄바꿈 폭이 있던 라벨은 그대로 둔다

        wc, wk = meter.width(cn[key]), meter.width(kr[key])
        if wc <= 0 or wk <= wc * SLACK:
            if st:
                patched[lab_pid] = bytes(d)   # 되돌린 상태를 반영
                newstate.pop(sk, None)
            continue          # 설계 여유 안에 들어가면 건드리지 않는다
        orig_size = size

        # 기준선: **중국어가 차지하던 폭**. 중국판 UI 는 그 폭에 맞춰 설계됐으므로
        # 거기에 설계 여유(SLACK)를 얹은 값이 안전한 한계선이다.
        # 계층에서 상자를 찾을 수 있으면 그보다 넓어지지 않게 한 번 더 조인다.
        # 계층에서 실제 상자를 찾으면 그것을 믿는다. 짧은 라벨일수록 설계 여유가 커서
        # 중국어 폭만 보고 조이면 멀쩡하던 버튼까지 두 줄로 쪼개진다("준비하기").
        # 상자를 못 찾을 때만 중국어가 쓰던 폭을 기준선으로 삼는다.
        box, off = box_for(g)
        usable = (box - off * 2) * MARGIN if box is not None else 0.0
        if usable > MIN_EM * size:
            allow_em = usable / size
        else:
            allow_em = wc * SLACK

        need = wk * size
        if need <= allow_em * size:
            continue

        if allow_em >= MIN_EM:
            # 상자가 넉넉하다 -> 줄바꿈으로 접는다
            struct.pack_into('<i', d, t, int(round(allow_em * size)))
            patched[lab_pid] = bytes(d)
            report['fixed'].append((os.path.basename(path), gname.get(g, '?'), key,
                                    '줄바꿈', int(round(allow_em * size)), int(round(need))))
        else:
            # 중국어가 두세 글자였던 짧은 버튼 라벨.
            # 이런 곳은 접으면 글자가 세로로 쌓여 더 나빠지므로 **글자 크기를 줄인다.**
            # 두 줄까지 허용해 축소율이 과하지 않게 한다.
            factor = max(MIN_SHRINK, (allow_em * LINES) / wk)
            if factor >= 0.995:
                continue
            newsize = size * factor
            tp = t_of[g]
            report['shrink'].append((os.path.basename(path), gname.get(g, '?'), key,
                                     round(size, 1), round(newsize, 1), int(round(need))))
            scales[tp] = newsize / size
            struct.pack_into('<i', d, t, int(round(allow_em * size)))
            patched[lab_pid] = bytes(d)
    return patched if patched else None


def rebuild(path, patched, out):
    meta = parse(path)
    raw = io.open(path, 'rb').read()
    off = meta['data_offset']
    data = bytearray()
    newobjs = []
    for ob in sorted(meta['objects'], key=lambda x: x['start']):
        while len(data) % 8:
            data.append(0)
        st = len(data)
        b = patched.get(ob['path_id']) or raw[off + ob['start']: off + ob['start'] + ob['size']]
        data += b
        newobjs.append(dict(ob, start=st, size=len(b)))
    m = meta['unity'].encode('utf-8') + b'\x00'
    m += struct.pack('<i', meta['platform'])
    m += struct.pack('<i', 0)
    m += struct.pack('<i', meta['big_id'])
    m += struct.pack('<i', len(newobjs))
    for ob in sorted(newobjs, key=lambda x: x['path_id']):
        m += struct.pack('<iIIiHh', ob['path_id'], ob['start'], ob['size'],
                         ob['type_id'], ob['class_id'], ob['destroyed'])
    m += struct.pack('<i', len(meta['externals']))
    for nm in meta['externals']:
        m += b'\x00' + b'\x00' * 16 + struct.pack('<i', 0) + nm.encode('utf-8') + b'\x00'
    m += b'\x00'
    do = max(meta['data_offset'], ALIGN(20 + len(m) + 64))
    head = struct.pack('>IIII', len(m), do + len(data), 9, do)
    head += bytes([1 if meta['endian'] == '>' else 0, 0, 0, 0])
    ob2 = bytearray(head + m)
    while len(ob2) < do:
        ob2 += b'\x00'
    ob2 += data
    io.open(out, 'wb').write(bytes(ob2))


def main():
    names = script_names()
    cn, _ = load('st_cn.txt')
    kr, _ = load('st_merged_kr.txt')
    meter = Meter('C:/Windows/Fonts/malgunbd.ttf')
    report = {'fixed': [], 'nobox': []}
    files = [p for p in glob.glob(os.path.join(CN, '*'))
             if not os.path.isdir(p) and not p.endswith('.resS') and '.split' not in p]
    touched = 0
    for p in files:
        name = os.path.basename(p)
        src = os.path.join(OVERLAY, name)
        base = src if os.path.exists(src) else p
        patched = process(base, names, cn, kr, meter, report)
        if not patched:
            continue
        if APPLY:
            rebuild(base, patched, os.path.join(OVERLAY, name))
        touched += 1

    print("줄바꿈 폭을 넣을 라벨 %d개 (자산 %d개)" % (len(report['fixed']), touched))
    print("상자를 못 찾아 건너뛴 라벨 %d개" % len(report['nobox']))
    print()
    hdr = ('자산', '오브젝트', '키', '상자', '허용', '필요')
    print("%-28s %-24s %-22s %6s %6s %6s" % hdr)
    for row in sorted(report['fixed'], key=lambda x: -x[5])[:25]:
        f, g, k, box, avail, need = row
        print("%-28s %-24s %-22s %6s %6s %6s" % (f[:28], g[:24], k[:22], box, avail, need))

    body = '=== 줄바꿈으로 접음 ===\n'
    body += '\n'.join('%s\t%s\t%s\t%s\t폭 %s\t필요 %s' % r for r in report['fixed'])
    body += '\n\n=== 글자 크기를 줄임 ===\n'
    body += '\n'.join('%s\t%s\t%s\t%s -> %s\t필요 %s' % r for r in report['shrink'])
    body += '\n\n=== 상자 못 찾음 ===\n'
    body += '\n'.join('%s\t%s\t%s' % r for r in report['nobox'])
    io.open('fit_report.txt', 'wb').write(body.encode('utf-8'))
    tail = '' if APPLY else '   (미적용: --apply 를 붙이면 실제로 씀)'
    print("\n전체 -> fit_report.txt" + tail)


if __name__ == '__main__':
    main()
