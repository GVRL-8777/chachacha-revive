# -*- coding: utf-8 -*-
"""복제 카드를 원본 카드(7번)와 4바이트 단위로 대조해 손상을 찾아낸다.

`clonecard.py` 는 바이트 수준으로 pathID 를 치환했는데, 그 값이 **문자열 길이나
PPtr 의 fileID 자리에 우연히 같은 숫자로 들어 있으면 함께 덮어써 버린다.**
(이미 UILocalize 키 길이, UISprite 아틀라스 fileID, UICheckbox 함수이름 길이가 당했다)

분류:
  remap  = 원본 pathID -> 대응 복제본 pathID (정상적인 참조 갱신)
  의도    = 우리가 일부러 바꾼 값(스프라이트 이름/로컬라이즈 키/버튼 함수명 영역)
  손상    = 그 외 전부
"""
import io, struct, sys
from collections import defaultdict
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

SRC = sys.argv[1] if len(sys.argv) > 1 else 'overlay/51161fc3df9f94087a76edf2817d987a'
CN_SA0 = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data/sharedassets0.assets'
ORIG_CARD = '7_Driver_Mental'
CLONES = ['8_Driver_Jeongbi', '9_Driver_Byul', '10_Driver_Samba', '11_Driver_Handol']
# 일부러 다르게 만든 컴포넌트(문자열이 통째로 바뀜)
INTENDED = {'UILocalize', 'UISprite'}


def load():
    sf = SerializedFile(EndianBinaryReader(io.open(SRC, 'rb').read()), None)
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
    return sf, names


def main():
    sf, names = load()
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

    def walk(card):
        root = [p for p, n in gname.items() if n == card][0]
        out = []

        def w(tp):
            out.append(go_of[tp])
            for c in tr[tp].get('m_Children', []):
                w(c['m_PathID'])
        w(t_of[root])
        return out

    base = walk(ORIG_CARD)
    for card in CLONES:
        cl = walk(card)
        # 오브젝트/컴포넌트 대응표 (복제 순서가 같다)
        m = {}
        for a, b in zip(base, cl):
            m[a] = b
            for x, y in zip(comps.get(a, []), comps.get(b, [])):
                m[x] = y
        print("=== %s ===" % card)
        bad = 0
        for a, b in zip(base, cl):
            for x, y in zip(comps.get(a, []), comps.get(b, [])):
                oa, ob = sf.objects[x], sf.objects[y]
                if oa.type.name != 'MonoBehaviour':
                    continue
                da, db = oa.get_raw_data(), ob.get_raw_data()
                sn = names.get(struct.unpack_from('<i', da, 16)[0])
                if sn in INTENDED:
                    continue
                for off in range(0, min(len(da), len(db)) - 3, 4):
                    va = struct.unpack_from('<i', da, off)[0]
                    vb = struct.unpack_from('<i', db, off)[0]
                    if va == vb:
                        continue
                    if m.get(va) == vb:
                        continue        # 정상 remap
                    print("   손상 %-18s %-16s @%-3d  %d -> %d"
                          % (gname[a], sn, off, va, vb))
                    bad += 1
        print("   손상 %d건\n" % bad)


if __name__ == '__main__':
    main()
