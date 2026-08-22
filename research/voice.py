# -*- coding: utf-8 -*-
"""카카오판에서 helly 음성 클립을 찾아 재생 가능한 파일로 뽑는다.

유니티 4 의 AudioClip 은 내부 포맷이 여러 가지라(MP3/Ogg/WAV/FSB) 우선 UnityPy 의
디코더를 쓰고, 실패하면 원본 바이트를 헤더로 판별해 그대로 저장한다.
"""
from _here import ROOT
import os, sys, io, UnityPy

SRC = 'survey/racechachachaforkakao/assets/bin/Data'
OUT = ROOT
WANT = sys.argv[1].lower() if len(sys.argv) > 1 else 'helly_vox'
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else 3

os.makedirs(OUT, exist_ok=True)
found = 0

def sniff(b):
    if b[:4] == b'RIFF':
        return '.wav'
    if b[:4] == b'OggS':
        return '.ogg'
    if b[:3] == b'ID3' or b[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'):
        return '.mp3'
    if b[:4] == b'FSB3' or b[:4] == b'FSB4' or b[:4] == b'FSB5':
        return '.fsb'
    return '.bin'

for f in sorted(os.listdir(SRC)):
    p = os.path.join(SRC, f)
    if not os.path.isfile(p):
        continue
    try:
        env = UnityPy.load(p)
    except Exception:
        continue
    for r in env.objects:
        if r.type.name != 'AudioClip':
            continue
        try:
            c = r.read()
        except Exception:
            continue
        nm = (c.m_Name or '')
        if WANT not in nm.lower():
            continue
        print("발견: %-32s (파일 %s)" % (nm, f[:16]))
        saved = False
        # 1) UnityPy 디코더 (FSB 등을 wav 로 풀어 준다)
        try:
            for sname, sdata in (c.samples or {}).items():
                out = os.path.join(OUT, "%s.wav" % nm)
                io.open(out, 'wb').write(sdata)
                print("   -> %s (%d KB, UnityPy 디코드)" % (out, len(sdata) // 1024))
                saved = True
                break
        except Exception as e:
            print("   UnityPy 디코드 실패: %s" % type(e).__name__)
        # 2) 원본 바이트 그대로
        if not saved:
            raw = None
            for attr in ('m_AudioData', 'm_Resource'):
                v = getattr(c, attr, None)
                if isinstance(v, (bytes, bytearray)) and len(v) > 64:
                    raw = bytes(v)
                    break
                if v is not None and hasattr(v, 'get_data'):
                    try:
                        raw = v.get_data()
                    except Exception:
                        pass
                    if raw:
                        break
            if raw:
                ext = sniff(raw)
                out = os.path.join(OUT, nm + ext)
                io.open(out, 'wb').write(raw)
                print("   -> %s (%d KB, 원본 %s)" % (out, len(raw) // 1024, ext))
                saved = True
            else:
                print("   오디오 바이트를 찾지 못함. 속성:",
                      [a for a in dir(c) if 'udio' in a or 'esource' in a][:6])
        if saved:
            found += 1
        if found >= LIMIT:
            print("총 %d개 추출" % found)
            sys.exit(0)

print("총 %d개 추출" % found)
