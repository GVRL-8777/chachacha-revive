# -*- coding: utf-8 -*-
"""직렬화 파일 안의 오브젝트 하나를 **길이가 달라져도** 갈아 끼운다.

같은 길이로 덮어쓰는 것은 여러 도구가 이미 한다. 이쪽은 길이가 늘거나 줄어도
되게 한다. 방법은 단순하다 — 데이터 구역을 다시 깔고, 오브젝트 표의
start/size 와 머리의 file_size 를 고친다. 오브젝트가 파일 안에서 어떤 순서로
놓이든 표만 맞으면 되므로 바꾼 것을 맨 뒤로 보낸다.

주의할 것 두 가지.

  · **머리는 큰끝, 메타데이터는 파일이 정한 순서**다. 섞으면 파일이 깨진다.
  · 오브젝트는 8바이트에 맞춰 놓는다.

    from sfedit import replace_object
    replace_object('.../어떤파일', path_id=1, blob=새바이트)
"""
import io
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ALIGN = 8


def replace_object(path, path_id, blob, backup_suffix=None):
    """path 안의 오브젝트 `path_id` 의 데이터를 `blob` 으로 바꾼다."""
    from sfparse import parse

    if backup_suffix:
        bak = path + backup_suffix
        if not os.path.exists(bak):
            shutil.copy2(path, bak)

    meta = parse(path)
    raw = bytearray(io.open(path, 'rb').read())
    doff = meta['data_offset']
    tbl = meta['obj_table_at']
    ent = meta['obj_entry_size']
    if not any(x['path_id'] == path_id for x in meta['objects']):
        raise SystemExit('%s 안에 pathID=%s 가 없습니다' % (path, path_id))

    chunks = []
    pos = 0
    layout = {}
    for x in meta['objects']:
        if x['path_id'] == path_id:
            continue
        data = bytes(raw[doff + x['start']:doff + x['start'] + x['size']])
        layout[x['path_id']] = (pos, len(data))
        chunks.append(data)
        pos += len(data)
        pad = (-pos) % ALIGN
        chunks.append(b'\0' * pad)
        pos += pad
    layout[path_id] = (pos, len(blob))
    chunks.append(bytes(blob))
    pos += len(blob)

    out = bytearray(raw[:doff]) + b''.join(chunks)

    e = meta['endian']
    for i, x in enumerate(meta['objects']):
        st, sz = layout[x['path_id']]
        at = tbl + i * ent
        struct.pack_into(e + 'I', out, at + 4, st)
        struct.pack_into(e + 'I', out, at + 8, sz)
    struct.pack_into('>I', out, 4, len(out))

    io.open(path, 'wb').write(bytes(out))
    old = [x['size'] for x in meta['objects'] if x['path_id'] == path_id][0]
    return old, len(blob), meta['file_size'], len(out)


def restore(path, backup_suffix):
    bak = path + backup_suffix
    if not os.path.exists(bak):
        return False
    shutil.copy2(bak, path)
    return True
