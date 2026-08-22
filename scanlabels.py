# -*- coding: utf-8 -*-
"""중국판 전 자산에서 UILabel/UILocalize 를 훑어 '문구가 어디에 쓰이는지' 표를 만든다.

각 라벨마다 다음을 뽑는다.
  · UILocalize 키 (없으면 프리팹에 박힌 원문)
  · Transform 스케일 = NGUI 2.x 에서 사실상 글자 크기
  · mMaxLineWidth (꼬리 오프셋 0) : 0 이면 **줄바꿈 없음 -> 가로로 무한정 늘어난다**

실측한 UILabel 레이아웃:
  @0  m_GameObject PPtr / @8 m_Enabled / @12 m_Script PPtr / @20 m_Name(len 0)
  @24 mMat PPtr / @40 mColor(4f) / @56 mPivot / @60 mDepth
  @64 mFont PPtr / @72 mText(len+bytes, 4정렬)
  이후 64바이트 꼬리: [0]=mMaxLineWidth [4]=mEncoding [20]=mEffectStyle
                      [24..39]=mEffectColor [44,48]=mEffectDistance
UILocalize 는 36바이트, @24 에 키 문자열.
"""
import io
import os
import glob
import json
import struct
import sys
from collections import defaultdict

from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
SA0 = os.path.join(CN, 'sharedassets0.assets')
TEXT_OFF = 72
LOC_KEY_OFF = 24


def script_names():
    sf = SerializedFile(EndianBinaryReader(io.open(SA0, 'rb').read()), None)
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


def scan(path, names):
    try:
        sf = SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)
    except Exception:
        return []
    gname, comps, scale = {}, defaultdict(list), {}
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
                t = o.read_typetree()
                scale[t['m_GameObject']['m_PathID']] = t['m_LocalScale']
        except Exception:
            continue

    rows = []
    for g, cl in comps.items():
        key, label = None, None
        for c in cl:
            o = sf.objects.get(c)
            if o is None or o.type.name != 'MonoBehaviour':
                continue
            d = o.get_raw_data()
            if len(d) < 20:
                continue
            sn = names.get(struct.unpack_from('<i', d, 16)[0])
            if sn == 'UILocalize':
                n = struct.unpack_from('<i', d, LOC_KEY_OFF)[0]
                if 0 < n < 80 and LOC_KEY_OFF + 4 + n <= len(d):
                    try:
                        key = d[LOC_KEY_OFF + 4:LOC_KEY_OFF + 4 + n].decode('utf-8')
                    except UnicodeDecodeError:
                        pass
            elif sn == 'UILabel':
                label = d
        if label is None:
            continue
        n = struct.unpack_from('<i', label, TEXT_OFF)[0]
        if not (0 <= n < 4000) or TEXT_OFF + 4 + n > len(label):
            continue
        try:
            txt = label[TEXT_OFF + 4:TEXT_OFF + 4 + n].decode('utf-8')
        except UnicodeDecodeError:
            txt = ''
        tail = TEXT_OFF + 4 + ((n + 3) // 4) * 4
        wrap = struct.unpack_from('<i', label, tail)[0] if tail + 4 <= len(label) else -1
        s = scale.get(g, {})
        rows.append({'file': os.path.basename(path), 'go': gname.get(g, '?'),
                     'key': key, 'text': txt, 'wrap': wrap,
                     'size': round(float(s.get('y', 0)), 1)})
    return rows


def main():
    names = script_names()
    files = [p for p in glob.glob(os.path.join(CN, '*'))
             if not os.path.isdir(p) and not p.endswith('.resS') and '.split' not in p]
    allrows = []
    for p in files:
        allrows += scan(p, names)
    io.open('labels.json', 'w', encoding='utf-8').write(
        json.dumps(allrows, ensure_ascii=False, indent=0))
    keyed = [r for r in allrows if r['key']]
    baked = [r for r in allrows if not r['key'] and r['text'].strip()]
    nowrap = [r for r in keyed if r['wrap'] == 0]
    print("자산 %d개 훑음" % len(files))
    print("UILabel 총 %d개" % len(allrows))
    print("  · UILocalize 키 있음 : %d개 (고유 키 %d개)"
          % (len(keyed), len(set(r['key'] for r in keyed))))
    print("  · 줄바꿈 없음(wrap=0): %d개  <- 가로로 넘칠 수 있는 라벨" % len(nowrap))
    print("  · 키 없이 원문 박힘   : %d개" % len(baked))
    han = [r for r in baked if any('\u4e00' <= c <= '\u9fff' for c in r['text'])]
    print("     그중 중국어 포함   : %d개  <- 번역이 안 되는 라벨" % len(han))
    print("\n표 저장 -> labels.json")


if __name__ == '__main__':
    main()
