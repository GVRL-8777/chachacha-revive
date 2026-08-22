# -*- coding: utf-8 -*-
"""분할(.splitN) 자산과 level* 까지 붙여서 AudioClip 을 훑습니다."""
import io, json, os, sys
import chaassets as A
from UnityPy.streams import EndianBinaryReader
from UnityPy.files.SerializedFile import SerializedFile


def joined(d, base):
    parts = sorted([f for f in os.listdir(d) if f.startswith(base + '.split')],
                   key=lambda x: int(x.rsplit('split', 1)[1]))
    blob = b''.join(io.open(os.path.join(d, p), 'rb').read() for p in parts)
    return blob


def scan(tree):
    d = os.path.join(tree, A.DATA)
    out = []
    names = set(f.split('.split')[0] for f in os.listdir(d) if '.split' in f)
    targets = [(n, joined(d, n)) for n in sorted(names)]
    for f in ('mainData', 'level0', 'level1', 'level2', 'level3'):
        p = os.path.join(d, f)
        if os.path.exists(p):
            targets.append((f, io.open(p, 'rb').read()))
    for name, blob in targets:
        try:
            sf = SerializedFile(EndianBinaryReader(blob), None)
        except Exception as e:
            print('  %s 못 읽음: %s' % (name, e))
            continue
        n = 0
        for pid, o in sf.objects.items():
            if o.type.name != 'AudioClip':
                continue
            try:
                t = o.read_typetree()
            except Exception:
                continue
            out.append({'file': name, 'pid': pid, 'name': t.get('m_Name'),
                        'bytes': len(t.get('m_AudioData') or b'')})
            n += 1
        print('  %-24s 오브젝트 %5d개 · AudioClip %d개' % (name, len(sf.objects), n))
    return out


if __name__ == '__main__':
    res = scan(sys.argv[1] if len(sys.argv) > 1 else 'x77')
    io.open(sys.argv[2] if len(sys.argv) > 2 else 'audio_split.json',
            'w', encoding='utf-8').write(json.dumps(res, ensure_ascii=False, indent=1))
    print('AudioClip %d개' % len(res))
    for a in sorted(res, key=lambda x: x['name'] or ''):
        print('   %-28s %8d B  (%s)' % (a['name'], a['bytes'], a['file']))
