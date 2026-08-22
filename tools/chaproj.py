# -*- coding: utf-8 -*-
"""프로젝트 파일 — 지금까지 만든 것을 한 덩이로 묶습니다.

한 프로젝트에 담기는 것

  · 세이브     그 시점의 세이브 한 벌 (통째로)
  · 내역       그 세이브를 만들기까지 무엇을 고쳤는지 (chalog 에서 떠 옵니다)
  · 새 차      런처로 넣은 차 목록 (newcars.json)
  · 빌드 설정  어떤 프리셋으로 구웠는지

**작업 트리(x77)는 담지 않습니다.** 1GB 가 넘고, 텍스처를 덮어쓴 것 같은
일은 되돌릴 수 없기 때문입니다. 대신 *무엇을 했는지*를 남겨서, 다른 트리
에서 같은 순서로 다시 밟을 수 있게 합니다.

  chaproj.save('내 판') · load('내 판') · items() · remove('내 판')
"""
import io
import json
import os
import time

CODE = os.path.dirname(os.path.abspath(__file__))
# 도구는 tools/ 안에 있고, 작업 트리(x77 · saves · lang …)는 그 위에 있다.
HERE = os.path.dirname(CODE)
DIR = os.path.join(HERE, 'projects')


def _path(name):
    safe = ''.join(c for c in name if c not in '\\/:*?"<>|').strip()
    if not safe:
        raise ValueError('쓸 수 없는 이름입니다')
    return os.path.join(DIR, safe + '.json')


def items():
    """프로젝트 목록. 최근 것이 먼저."""
    os.makedirs(DIR, exist_ok=True)
    out = []
    for f in os.listdir(DIR):
        if not f.endswith('.json'):
            continue
        p = os.path.join(DIR, f)
        try:
            d = json.load(io.open(p, encoding='utf-8'))
        except Exception:
            continue
        out.append({'name': f[:-5], 'saved': d.get('saved', ''),
                    'note': d.get('note', ''),
                    'preset': d.get('preset', ''),
                    'changes': len(d.get('changes') or []),
                    'cars': len(d.get('newcars') or []),
                    'bytes': os.path.getsize(p)})
    return sorted(out, key=lambda x: x['saved'], reverse=True)


def _newcars():
    p = os.path.join(HERE, 'newcars.json')
    if not os.path.exists(p):
        return []
    try:
        return json.load(io.open(p, encoding='utf-8'))
    except Exception:
        return []


def save(name, save_data, preset='', note='', mark=''):
    """지금 상태를 프로젝트로 묶습니다. `mark` 뒤의 내역만 담습니다."""
    import chalog
    os.makedirs(DIR, exist_ok=True)
    d = {'name': name, 'saved': time.strftime('%Y-%m-%d %H:%M:%S'),
         'note': note, 'preset': preset, 'save': save_data,
         'newcars': _newcars(),
         'changes': chalog.since(mark) if mark else chalog.read(2000)}
    io.open(_path(name), 'w', encoding='utf-8').write(
        json.dumps(d, ensure_ascii=False, indent=2))
    chalog.add('project', '프로젝트를 저장했습니다: %s' % name,
               {'내역': len(d['changes']), '새 차': len(d['newcars'])})
    return d


def load(name):
    p = _path(name)
    if not os.path.exists(p):
        raise KeyError('그런 프로젝트가 없습니다: %s' % name)
    return json.load(io.open(p, encoding='utf-8'))


def remove(name):
    import chalog
    p = _path(name)
    if os.path.exists(p):
        os.remove(p)
        chalog.add('project', '프로젝트를 지웠습니다: %s' % name)
        return True
    return False


def rename(name, to):
    import chalog
    src, dst = _path(name), _path(to)
    if not os.path.exists(src):
        raise KeyError('그런 프로젝트가 없습니다: %s' % name)
    if os.path.exists(dst):
        raise ValueError('같은 이름이 이미 있습니다: %s' % to)
    d = json.load(io.open(src, encoding='utf-8'))
    d['name'] = to
    io.open(dst, 'w', encoding='utf-8').write(
        json.dumps(d, ensure_ascii=False, indent=2))
    os.remove(src)
    chalog.add('project', '프로젝트 이름을 바꿨습니다: %s -> %s' % (name, to))
    return True
