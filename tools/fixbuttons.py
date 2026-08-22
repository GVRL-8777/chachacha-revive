# -*- coding: utf-8 -*-
"""복제 카드의 버튼 배선을 고친다.

두 가지가 망가져 있었다.
 1) `UIButtonMessage.functionName` 이 전부 원본 그대로 "OnChoiceDriver_7" 이라
    9~12번 카드를 눌러도 8번 드라이버가 선택됐다(=선택이 안 되는 것처럼 보임).
    카드마다 _8 ~ _11 로 바꾼다(DLL 쪽에 해당 메서드를 새로 만들어 뒀다).
 2) `UICheckbox.functionName`("OnActivate")의 **길이 필드가 647 로 덮여** 있었다.
    `clonecard.py` 가 pathID 10(원본 버튼 GameObject) -> 647(복제본)로 바꾸면서
    길이값 10 까지 같이 갈아엎은 것이다. 문자열 본문은 남아 있으니 길이만 되돌린다.

레이아웃(실측):
  UIButtonMessage(60B): @24 target PPtr, @32 functionName(길이+문자열)
  UICheckbox(88B)     : @68 functionName 길이, @72 문자열
"""
import io, struct, sys
from collections import defaultdict
from sfparse import parse
from sfwrite import ALIGN
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

SRC, OUT = sys.argv[1], sys.argv[2]
CN_SA0 = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data/sharedassets0.assets'
JOBS = {'8_Driver_Jeongbi': 8, '9_Driver_Byul': 9,
        '10_Driver_Samba': 10, '11_Driver_Handol': 11}
BM_NAME_OFF = 32
CB_NAME_OFF = 68
CB_FUNC = b'OnActivate'


def main():
    meta = parse(SRC)
    raw = io.open(SRC, 'rb').read()
    sf = SerializedFile(EndianBinaryReader(raw), None)
    names = {}
    s0 = SerializedFile(EndianBinaryReader(io.open(CN_SA0, 'rb').read()), None)
    for pid, o in s0.objects.items():
        if o.type.name != 'MonoScript':
            continue
        d = o.get_raw_data()
        n = struct.unpack_from('<i', d, 0)[0]
        if 0 < n < 200:
            try:
                names[pid] = d[4:4 + n].decode('utf-8')
            except UnicodeDecodeError:
                pass

    gname, tr, comps = {}, {}, defaultdict(list)
    for p, o in sf.objects.items():
        if o.type.name == 'GameObject':
            t = o.read_typetree()
            gname[p] = t['m_Name']
            for c in t['m_Component']:
                v = c[1] if isinstance(c, (list, tuple)) and len(c) == 2 else None
                if isinstance(v, dict) and v.get('m_PathID'):
                    comps[p].append(v['m_PathID'])
        elif o.type.name == 'Transform':
            tr[p] = o.read_typetree()
    go_of = {p: t['m_GameObject']['m_PathID'] for p, t in tr.items()}
    t_of = {g: p for p, g in go_of.items()}

    def sub(card):
        root = [p for p, n in gname.items() if n == card][0]
        out = []

        def w(tp):
            out.append(go_of[tp])
            for c in tr[tp].get('m_Children', []):
                w(c['m_PathID'])
        w(t_of[root])
        return out

    patched = {}
    for card, idx in JOBS.items():
        for g in sub(card):
            for c in comps.get(g, []):
                o = sf.objects[c]
                if o.type.name != 'MonoBehaviour':
                    continue
                d = bytearray(o.get_raw_data())
                sn = names.get(struct.unpack_from('<i', d, 16)[0])
                if sn == 'UIButtonMessage':
                    ln = struct.unpack_from('<i', d, BM_NAME_OFF)[0]
                    old = d[BM_NAME_OFF + 4:BM_NAME_OFF + 4 + ln].decode('ascii', 'replace')
                    nb = ('OnChoiceDriver_%d' % idx).encode()
                    field = struct.pack('<i', len(nb)) + nb
                    while len(field) % 4:
                        field += b'\x00'
                    tail = bytes(d[BM_NAME_OFF + 4 + ((ln + 3) & ~3):])
                    patched[c] = bytes(d[:BM_NAME_OFF]) + field + tail
                    print("  %-20s 버튼 %s -> %s" % (card, old, nb.decode()))
                elif sn == 'UICheckbox':
                    ln = struct.unpack_from('<i', d, CB_NAME_OFF)[0]
                    body = bytes(d[CB_NAME_OFF + 4:CB_NAME_OFF + 4 + len(CB_FUNC)])
                    if ln == len(CB_FUNC):
                        continue
                    if body != CB_FUNC:
                        print("  [경고] %s 체크박스 문자열이 예상과 다름: %r" % (card, body))
                        continue
                    struct.pack_into('<i', d, CB_NAME_OFF, len(CB_FUNC))
                    patched[c] = bytes(d)
                    print("  %-20s 체크박스 함수이름 길이 %d -> %d 복구"
                          % (card, ln, len(CB_FUNC)))

    objs = sorted(meta['objects'], key=lambda x: x['start'])
    data = bytearray()
    newobjs = []
    for ob in objs:
        while len(data) % 8:
            data.append(0)
        st = len(data)
        b = patched.get(ob['path_id']) or \
            raw[meta['data_offset'] + ob['start']: meta['data_offset'] + ob['start'] + ob['size']]
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
    data_offset = max(meta['data_offset'], ALIGN(20 + len(m) + 64))
    head = struct.pack('>IIII', len(m), data_offset + len(data), 9, data_offset)
    head += bytes([1 if meta['endian'] == '>' else 0, 0, 0, 0])
    ob2 = bytearray(head + m)
    while len(ob2) < data_offset:
        ob2 += b'\x00'
    ob2 += data
    io.open(OUT, 'wb').write(bytes(ob2))
    print("출력: %s (%d B) / 컴포넌트 %d개 수정" % (OUT, len(ob2), len(patched)))


if __name__ == '__main__':
    main()
