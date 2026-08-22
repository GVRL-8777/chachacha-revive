# -*- coding: utf-8 -*-
"""바꾼 내역을 적어 둡니다.

런처로 무엇을 고쳤는지는 **작업 트리만 봐서는 알 수 없습니다.** 텍스처를
덮어쓰면 그냥 덮어써지고, 차 값을 고쳐도 JSON 안 숫자만 바뀝니다. 그래서
고칠 때마다 여기 한 줄씩 남깁니다.

한 줄이 JSON 한 덩이인 `.jsonl` 입니다. 덧붙이기만 하므로 런처가 여러 개
떠 있어도 서로 밟지 않고, 사람이 열어 봐도 읽힙니다.

  kind   save · asset · build · device · project · system
  text   사람이 읽을 한 줄
  detail 있으면 딸린 값(파일 이름 · 개수 같은 것)
"""
import io
import json
import os
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOGFILE = os.path.join(HERE, 'chalog.jsonl')
_LOCK = threading.Lock()
MAX_LINES = 4000


def add(kind, text, detail=None):
    """한 줄 적습니다. 실패해도 하던 일을 막지 않습니다."""
    row = {'t': time.strftime('%Y-%m-%d %H:%M:%S'), 'kind': kind,
           'text': text}
    if detail:
        row['detail'] = detail
    try:
        with _LOCK:
            with io.open(LOGFILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
    except Exception:
        pass
    return row


def read(limit=500, kind=None, find=None):
    """뒤에서부터 limit 줄. 갈래와 글자로 거를 수 있습니다."""
    if not os.path.exists(LOGFILE):
        return []
    out = []
    try:
        with io.open(LOGFILE, encoding='utf-8') as f:
            lines = f.readlines()[-MAX_LINES:]
    except Exception:
        return []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            row = json.loads(ln)
        except Exception:
            continue
        if kind and row.get('kind') != kind:
            continue
        if find and find not in json.dumps(row, ensure_ascii=False):
            continue
        out.append(row)
    return out[-limit:]


def since(mark):
    """`mark`(시각 문자열) 뒤에 적힌 것만. 프로젝트에 담을 때 씁니다."""
    return [r for r in read(MAX_LINES) if not mark or r.get('t', '') > mark]


def clear():
    try:
        if os.path.exists(LOGFILE):
            os.remove(LOGFILE)
    except Exception:
        return False
    add('system', '기록을 비웠습니다')
    return True


def as_text(rows):
    return '\n'.join(
        '%s  [%s] %s%s' % (r.get('t', ''), r.get('kind', ''), r.get('text', ''),
                           ('  ' + json.dumps(r['detail'], ensure_ascii=False))
                           if r.get('detail') else '')
        for r in rows)


def export(path=None):
    """사람이 읽을 텍스트로 내보냅니다."""
    path = path or os.path.join(HERE, 'export', 'chalog.txt')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, 'w', encoding='utf-8').write(as_text(read(MAX_LINES)) + '\n')
    return path
