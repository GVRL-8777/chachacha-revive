# -*- coding: utf-8 -*-
"""APK 를 푼 폴더에서 `tb_systemtext` 를 텍스트로 꺼낸다.

한국어화의 첫 단계다. LINE GoGoGo 1.0.3 의 문자열표가 **한국어 원본**이고,
`mkkorean.py` 가 그것을 중국판 자산에 써 넣는다.

  python dump_systemtext.py survey/line line_tb_systemtext.txt

표는 `키 = 값` 이 줄마다 늘어선 모양이고 줄 끝이 **CRLF** 다. 그 모양을
그대로 지켜야 게임이 읽는다 — `ByteReader::ReadDictionary` 가 `=` 로 가르고
양쪽을 `Trim()` 한다.
"""
import io
import os
import sys

import UnityPy

NAME = 'tb_systemtext'


def find(root, want=NAME):
    """푼 폴더를 훑어 그 이름의 TextAsset 을 찾는다. (파일, 이름, 내용)."""
    data = os.path.join(root, 'assets', 'bin', 'Data')
    if not os.path.isdir(data):
        data = root
    for fn in sorted(os.listdir(data)):
        p = os.path.join(data, fn)
        if os.path.isdir(p):
            continue
        try:
            env = UnityPy.load(p)
        except Exception:
            continue
        for o in env.objects:
            if o.type.name != 'TextAsset':
                continue
            try:
                d = o.read()
            except Exception:
                continue
            nm = getattr(d, 'm_Name', None) or getattr(d, 'name', None)
            if not nm or want.lower() not in str(nm).lower():
                continue
            body = getattr(d, 'm_Script', None)
            if body is None:
                body = getattr(d, 'script', None)
            if body is None:
                continue
            if isinstance(body, (bytes, bytearray)):
                body = bytes(body).decode('utf-8', 'replace')
            return p, str(nm), body
    return None, None, None


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else 'survey/line'
    out = sys.argv[2] if len(sys.argv) > 2 else 'line_tb_systemtext.txt'
    p, nm, body = find(root)
    if body is None:
        raise SystemExit('%s 안에서 %s 를 못 찾았습니다' % (root, NAME))
    # 읽어 온 그대로 쓴다. 줄 끝을 건드리면 표가 깨진다.
    io.open(out, 'w', encoding='utf-8', newline='').write(body)
    lines = body.count('\n') + 1
    print('%s (%s) -> %s' % (nm, os.path.basename(p), out))
    print('  %d줄 · %d바이트' % (lines, len(body.encode('utf-8'))))
    head = [l for l in body.split('\n') if '=' in l][:2]
    for h in head:
        print('  예: %s' % h.strip()[:70])


if __name__ == '__main__':
    main()
