# -*- coding: utf-8 -*-
"""트리 안의 AudioClip 을 훑어 이름·길이·크기를 뽑는다."""
import io, json, os, sys
import chaassets as A

def scan(tree):
    d = os.path.join(tree, A.DATA)
    files = [f for f in sorted(os.listdir(d))
             if os.path.isfile(os.path.join(d, f)) and '.split' not in f]
    out = []
    for i, fn in enumerate(files):
        if i % 200 == 0:
            sys.stderr.write('\r  %d/%d' % (i, len(files)))
        try:
            sf = A._sf(os.path.join(d, fn))
        except Exception:
            continue
        for pid, o in sf.objects.items():
            if o.type.name != 'AudioClip':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            out.append({'file': fn, 'pid': pid, 'name': t.get('m_Name'),
                        'len': round(float(t.get('m_Length') or 0), 3),
                        'size': int(t.get('m_Size') or 0),
                        'fmt': t.get('m_Type'),
                        'freq': t.get('m_Frequency')})
    sys.stderr.write('\n')
    return out

if __name__ == '__main__':
    tree = sys.argv[1]
    res = scan(tree)
    io.open(sys.argv[2], 'w', encoding='utf-8').write(
        json.dumps(res, ensure_ascii=False, indent=1))
    print('%s: AudioClip %d개' % (tree, len(res)))
