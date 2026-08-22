# -*- coding: utf-8 -*-
"""fitlabels 가 이미 손댄 라벨을 찾아 상태 파일(fit_state.json)을 되살린다.

상태 파일 없이 기준값만 바꿔 다시 돌리면, 이미 줄바꿈 폭이 들어간 라벨을
'원래부터 그랬던 것'으로 오인해 건너뛴다. 그래서 중국판 원본과 대조해
  · UILabel 꼬리 오프셋 0(mMaxLineWidth) 이 원본과 다르고
  · 원본 값이 0 이었던
라벨을 골라, 원본의 (줄바꿈 폭, 글자 크기)를 상태로 기록한다.
"""
import io
import os
import glob
import json
import struct
from collections import defaultdict

from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile

CN = 'survey/5577.com.cjenm.chachachacn/assets/bin/Data'
OVERLAY = 'overlay'
STATE = 'fit_state.json'
TEXT_OFF = 72


def script_names():
    sf = SerializedFile(EndianBinaryReader(
        io.open(os.path.join(CN, 'sharedassets0.assets'), 'rb').read()), None)
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


def labels(path, names):
    """{라벨pathID: (줄바꿈폭, 그 라벨 GameObject 의 스케일)}"""
    try:
        sf = SerializedFile(EndianBinaryReader(io.open(path, 'rb').read()), None)
    except Exception:
        return {}
    scale = {}
    for q, o in sf.objects.items():
        if o.type.name != 'Transform':
            continue
        try:
            t = o.read_typetree()
            scale[t['m_GameObject']['m_PathID']] = abs(float(t['m_LocalScale']['x']))
        except Exception:
            pass
    out = {}
    for q, o in sf.objects.items():
        if o.type.name != 'MonoBehaviour':
            continue
        d = o.get_raw_data()
        if len(d) < 80:
            continue
        if names.get(struct.unpack_from('<i', d, 16)[0]) != 'UILabel':
            continue
        n = struct.unpack_from('<i', d, TEXT_OFF)[0]
        if not (0 <= n < 4000):
            continue
        t = TEXT_OFF + 4 + ((n + 3) // 4) * 4
        if t + 64 > len(d):
            continue
        g = struct.unpack_from('<i', d, 4)[0]
        out[q] = (struct.unpack_from('<i', d, t)[0], scale.get(g, 0.0))
    return out


def main():
    names = script_names()
    state = {}
    files = 0
    for p in sorted(glob.glob(os.path.join(OVERLAY, '*'))):
        name = os.path.basename(p)
        orig = os.path.join(CN, name)
        if not os.path.exists(orig):
            continue
        a = labels(p, names)
        if not a:
            continue
        b = labels(orig, names)
        hit = 0
        for pid, (wrap, sc) in a.items():
            ow, osc = b.get(pid, (None, None))
            if ow is None:
                continue
            if wrap != ow and ow == 0:
                state['%s:%d' % (name, pid)] = {'w': ow, 's': osc}
                hit += 1
            elif abs(sc - osc) > 0.01:
                state['%s:%d' % (name, pid)] = {'w': ow, 's': osc}
                hit += 1
        if hit:
            files += 1
            print("  %-36s 되살린 라벨 %d개" % (name[:36], hit))
    io.open(STATE, 'w', encoding='utf-8').write(json.dumps(state, ensure_ascii=False))
    print("상태 %d개 기록 (자산 %d개) -> %s" % (len(state), files, STATE))


if __name__ == '__main__':
    main()
