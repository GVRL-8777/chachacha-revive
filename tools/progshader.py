# -*- coding: utf-8 -*-
"""고정기능 셰이더를 **프로그램 셰이더**로 갈아 끼운다.

왜 필요한가. 이 게임의 차와 맵은 `Mobile-Lightmap-Unlit` 으로 그려지는데,
그 셰이더는 셰이더 프로그램이 없는 **고정 기능**이다.

    SetTexture [_MainTex] { combine texture }

유니티 4 는 고정 기능을 실행 중에 GLSL 로 흉내 낸다. 그 경로가 요즘 Mali
드라이버(예: 갤럭시 A35 · 안드로이드 16)에서 죽는다. 그래서 UI(프로그램
셰이더인 NGUI)는 멀쩡한데 차와 길만 새까맣게 나온다. Adreno 에서는 멀쩡하다.

유니티 4 는 셰이더의 GLSL 을 **평문으로** 넣어 두므로, 컴파일러 없이 텍스트만
써 넣으면 프로그램 셰이더가 된다. 여기서 그렇게 한다.

    python tools/progshader.py            갈아 끼운다
    python tools/progshader.py --show     지금 뭐가 들었는지 본다
    python tools/progshader.py --restore  원래대로 (백업에서)

레코드가 길어지므로 오브젝트를 파일 끝에 다시 놓고 표의 start/size 를 고친다.
오브젝트 순서는 표에만 있으면 되고 파일 안 순서와는 무관하다.
"""
import argparse
import io
import os
import shutil
import struct
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
sys.path.insert(0, CODE)

TARGET = os.path.join('assets', 'bin', 'Data',
                      '0000000000000000f000000000000000')
NAME = 'Mobile-Lightmap-Unlit'

# 유니티 4 의 GLES2 셰이더는 이런 꼴로 들어 있다. 그대로 흉내 낸다.
GLES = '''Program "vp" {
SubProgram "gles " {
"!!GLES
#define SHADER_API_GLES 1
#define tex2D texture2D
#ifdef VERTEX
#define gl_ModelViewProjectionMatrix glstate_matrix_mvp
uniform mat4 glstate_matrix_mvp;
varying highp vec2 xlv_TEXCOORD0;
attribute vec4 _glesMultiTexCoord0;
attribute vec4 _glesVertex;
void main ()
{
  gl_Position = (gl_ModelViewProjectionMatrix * _glesVertex);
  xlv_TEXCOORD0 = _glesMultiTexCoord0.xy;
}
#endif
#ifdef FRAGMENT
varying highp vec2 xlv_TEXCOORD0;
uniform sampler2D _MainTex;
void main ()
{
  BODYMARK
  gl_FragData[0] = SOLIDMARK texture2D (_MainTex, xlv_TEXCOORD0);
}
#endif"
}
}
Program "fp" {
SubProgram "gles " {
"!!GLES"
}
}'''

NEW_SHADER = '''Shader "Mobile/Unlit (Supports Lightmap)" {
Properties {
 _MainTex ("Base (RGB)", 2D) = "white" {}
}
SubShader {
 LOD 100
 Tags { "RenderType"="Opaque" }
 Pass {
  Tags { "RenderType"="Opaque" }
%s
 }
}
}
''' % GLES


def _load(tree):
    import UnityPy
    p = os.path.join(tree, TARGET)
    if not os.path.exists(p):
        raise SystemExit('셰이더 파일이 없습니다: %s' % p)
    return p, UnityPy.load(p)


def show(tree):
    p, env = _load(tree)
    for o in env.objects:
        if o.type.name != 'Shader':
            continue
        t = o.read_typetree()
        s = t.get('m_Script') or ''
        if isinstance(s, (bytes, bytearray)):
            s = bytes(s).decode('utf-8', 'replace')
        kind = ('프로그램' if 'SubProgram "' in s else
                ('고정기능' if 'SetTexture' in s else '?'))
        print('  pathID=%-4s %-26s %6d자  %s'
              % (o.path_id, t.get('m_Name', '?'), len(s), kind))
    return 0


def _bakpath():
    # 백업을 트리 **밖**에 둔다. 트리 안에 두면 APK 에 딸려 들어간다.
    d = os.path.join(HERE, 'backup', 'shader')
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, os.path.basename(TARGET) + '.fixedfunc')


def swap(tree, solid=False):
    from sfparse import parse
    p, env = _load(tree)
    bak = _bakpath()
    if not os.path.exists(bak):
        shutil.copy2(p, bak)
        print('  원본을 남겨 둠: backup/shader/')

    target = None
    for o in env.objects:
        if o.type.name != 'Shader':
            continue
        t = o.read_typetree()
        if t.get('m_Name') == NAME:
            target = (o, t)
            break
    if target is None:
        raise SystemExit('%s 를 못 찾았습니다' % NAME)
    o, t = target
    mark = {'red': 'vec4(1.0, 0.0, 0.0, 1.0); //',
            'uv': 'vec4(xlv_TEXCOORD0.x, xlv_TEXCOORD0.y, 0.0, 1.0); //',
            # 표본을 32배로 키운다. 묶여 있는데 어두운 것인지,
            # 아예 안 묶여 0 인지 가르는 시험이다.
            'amp': ('vec4(clamp(texture2D (_MainTex, xlv_TEXCOORD0).xyz'
                    ' * 32.0, 0.0, 1.0), 1.0); //'),
            # UV 를 한복판에 박는다. 텍스처가 묶여 있으면 몸통이 그 한 점
            # 색으로 **평평하게** 칠해진다. 그래도 검으면 안 묶인 것이다.
            'center': 'texture2D (_MainTex, vec2(0.5, 0.5)); //',
            'discard': '',
            # 표본과 UV 를 **한 화면에** 담는다. 빨강·초록은 텍스처,
            # 파랑은 UV.x 다. 파랑만 보이면 varying 을 좌표로 쓸 때만
            # 표본이 0 이라는 뜻이다.
            'mix': ('vec4(texture2D (_MainTex, xlv_TEXCOORD0).xy,'
                    ' xlv_TEXCOORD0.x * 0.6, 1.0); //'),
            # varying 을 식에 넣되 값은 한복판으로 죽인다. 이게 나오면
            # varying 자체가 아니라 그 **값**이 문제다.
            'killuv': ('texture2D (_MainTex,'
                       ' (xlv_TEXCOORD0 * 0.0) + vec2(0.5, 0.5)); //'),
            '': ''}[solid or '']
    # 표본이 0 인 픽셀을 버린다. 깊이 버퍼가 없어 **검은 그림자 복사본이
    # 차 위를 덮는지** 가리는 시험이다. 덮는 것이면 차가 드러난다.
    body = ('if (dot(texture2D (_MainTex, xlv_TEXCOORD0).xyz,'
            ' vec3(1.0)) < 0.02) discard;') if solid == 'discard' else ''
    if solid == 'discard':
        mark = ''
    src = NEW_SHADER.replace('SOLIDMARK ', mark).replace('BODYMARK', body)
    t['m_Script'] = src
    body = bytes(o.save_typetree(t))

    meta = parse(p)
    raw = bytearray(io.open(p, 'rb').read())
    doff = meta['data_offset']
    tbl = meta['obj_table_at']
    ent = meta['obj_entry_size']

    # 데이터 구역을 다시 짠다: 바꾼 오브젝트를 맨 뒤로 보낸다.
    others = [x for x in meta['objects'] if x['path_id'] != o.path_id]
    chunks = []
    pos = 0
    layout = {}
    for x in others:
        data = bytes(raw[doff + x['start']:doff + x['start'] + x['size']])
        layout[x['path_id']] = (pos, len(data))
        chunks.append(data)
        pos += len(data)
        pad = (-pos) % 8
        chunks.append(b'\0' * pad)
        pos += pad
    layout[o.path_id] = (pos, len(body))
    chunks.append(body)
    pos += len(body)

    newdata = b''.join(chunks)
    out = bytearray(raw[:doff]) + newdata

    # 오브젝트 표의 start/size 를 고친다.
    # **머리는 큰끝, 메타데이터는 파일이 정한 순서**다. 섞으면 파일이 깨진다.
    e = meta['endian']
    for i, x in enumerate(meta['objects']):
        st, sz = layout[x['path_id']]
        at = tbl + i * ent
        struct.pack_into(e + 'I', out, at + 4, st)
        struct.pack_into(e + 'I', out, at + 8, sz)

    # 머리의 file_size 는 큰끝이다
    struct.pack_into('>I', out, 4, len(out))

    io.open(p, 'wb').write(bytes(out))
    print('  %s 를 프로그램 셰이더로 바꿨습니다' % NAME)
    print('     레코드 %d -> %d바이트 · 파일 %d -> %d바이트'
          % ([x['size'] for x in meta['objects']
              if x['path_id'] == o.path_id][0], len(body),
             meta['file_size'], len(out)))
    return 0


def restore(tree):
    p = os.path.join(tree, TARGET)
    bak = _bakpath()
    if not os.path.exists(bak):
        old = p + '.fixedfunc.bak'          # 예전 자리
        if os.path.exists(old):
            bak = old
        else:
            raise SystemExit('남겨 둔 원본이 없습니다')
    shutil.copy2(bak, p)
    print('  원래대로 돌렸습니다')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', default=os.path.join(HERE, 'x77'))
    ap.add_argument('--show', action='store_true')
    ap.add_argument('--restore', action='store_true')
    ap.add_argument('--solid', choices=('red', 'uv', 'amp', 'center', 'mix', 'killuv', 'discard'),
                    help='시험용 — red: 빨강만, uv: UV 를 색으로, amp: 표본 32배, center: UV 를 한복판 고정')
    a = ap.parse_args()
    if a.show:
        return show(a.tree)
    if a.restore:
        return restore(a.tree)
    return swap(a.tree, a.solid)


if __name__ == '__main__':
    sys.exit(main())
