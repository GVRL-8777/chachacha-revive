# -*- coding: utf-8 -*-
"""차차차 통합 도구 — 세이브 런처 · 자산 뽑기/칠하기/들여오기 · APK 내보내기.

하나의 프로그램이고, 얼굴만 둘이다.
  · 웹 런처   : `chatool web`  — 브라우저로 열린다. 파이선이 없는 PC 에서도
                exe 한 개만 있으면 된다(HTML/JS 는 이 파일 안에 들어 있다).
  · 창 런처   : `chatool app`  — 같은 서버를 데스크톱 창으로 감싼다.
                **기능과 동작은 웹 런처와 완전히 같다**(같은 백엔드를 쓴다).

세이브는 saves/ 아래에 여러 개 둘 수 있지만 **한 번에 하나만** 고른다.
고른 것이 chastate.json 으로 복사되어 서버가 읽고, ADB 로 기기에도 넣는다.

명령
  chatool                            앱 창으로 런처를 연다 (기본)
  chatool web [--port 8099]          브라우저로 연다
  chatool app
  chatool cars                       차 목록
  chatool extract <차이름> [-o 폴더] 텍스처 PNG · 메시 OBJ · UV 안내선
  chatool repaint <차이름> <png>     텍스처 다시 칠하기
  chatool import  <obj> --like <차>  OBJ 로 그 차의 메시만 갈아 끼운다
  chatool newcar  <이름> --obj a.obj --png b.png   새 차로 추가한다
  chatool build   [--mode server|local] [--install]
  chatool index                      자산 색인 다시 만들기

파이선 없는 PC 용 단일 실행파일:
  chatool pack-exe                   (PyInstaller 로 chatool.exe 를 만든다)
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time

# CODE 는 도구가 놓인 자리, HERE 는 작업 트리(x77 · saves · lang …)가 있는 자리다.
if getattr(sys, 'frozen', False):
    # 얼려서(exe) 돌 때는 __file__ 이 임시 압축해제 폴더를 가리킨다.
    # 작업 폴더는 **실행파일이 놓인 자리**로 잡아야 x77/ · saves/ 를 찾는다.
    CODE = os.path.dirname(os.path.abspath(sys.executable))
    HERE = CODE
else:
    # 도구는 tools/ 안에 있고, 작업 트리는 그 위에 있다.
    CODE = os.path.dirname(os.path.abspath(__file__))
    HERE = os.path.dirname(CODE)
# pack-exe 로 구운 것은 dist/ 안에 떨어진다. 거기엔 작업 트리가 없으므로
# 한 칸 위도 본다. 그래야 dist\chatool.exe 를 그 자리에서 바로 쓸 수 있다.
if not os.path.isdir(os.path.join(HERE, 'x77')):
    _up = os.path.dirname(HERE)
    if os.path.isdir(os.path.join(_up, 'x77')):
        HERE = _up
sys.path.insert(0, HERE)

SAVES = os.path.join(HERE, 'saves')
ACTIVE = os.path.join(SAVES, 'active.txt')
LIVE = os.path.join(HERE, 'chastate.json')
TREE = os.path.join(HERE, 'x77')
# 우리 판의 패키지. **하나로 고정**입니다.
#
# 예전에는 프리셋마다 앱을 갈랐지만(rag · rich), 갈라 놓으니 같은 게임이
# 둘로 보이고 세이브도 따로 놀았습니다. 이제 APK 는 한 벌이고, 시작 상태는
# **세이브 파일**로 가릅니다 — PC 에서 내보내고 폰에서 읽어 들입니다.
PKG = 'com.cjenm.chachacha.revive'
APP_LABEL = '다함께 차차차'
# 원판의 패키지. **클래스 이름은 그대로 두었습니다** — dex 안 클래스를
# 건드리지 않으려고 매니페스트에만 새 이름을 씁니다. 그래서 액티비티는
# 절대 이름으로 불러야 합니다(상대 이름은 안 먹습니다).
PKG_CLASSES = 'com.cjenm.chachachacn'

# 예전에 깔았던 앱들. 기기에서 세이브를 되찾을 수 있게 이름만 알아 둡니다.
LEGACY_APPS = [
    ('com.cjenm.chachacharevive.rag', '다함께 차차차 (예전 rag)'),
    ('com.cjenm.chachacharevive.rich', '다함께 차차차 (예전 rich)'),
    ('com.cjenm.chachacharevive', '다함께 차차차 (예전)'),
    ('com.cjenm.chachachacn', '一起车车车 (원판)'),
]
KNOWN_APPS = [(PKG, APP_LABEL)] + LEGACY_APPS


def device_save_of(pkg):
    return '/storage/emulated/0/Android/data/%s/files/chasave.json' % pkg


def activity_of(pkg):
    return '%s/%s.CustomUnityPlayerActivity' % (pkg, PKG_CLASSES)


ACTIVITY = activity_of(PKG)
DEVICE_SAVE = device_save_of(PKG)


def _run(cmd, **kw):
    kw.setdefault('capture_output', True)
    kw.setdefault('text', True)
    kw.setdefault('encoding', 'utf-8')
    kw.setdefault('errors', 'replace')
    return subprocess.run(cmd, **kw)


# ================================================================= 세이브 슬롯
def _default_state():
    import chastate
    return chastate.default()


def slots():
    os.makedirs(SAVES, exist_ok=True)
    return sorted(f[:-5] for f in os.listdir(SAVES)
                  if f.endswith('.json') and not f.startswith('.'))


def active_name():
    if os.path.exists(ACTIVE):
        n = io.open(ACTIVE, encoding='utf-8').read().strip()
        if n in slots():
            return n
    s = slots()
    return s[0] if s else None


def slot_path(name):
    return os.path.join(SAVES, name + '.json')


def read_slot(name):
    return json.load(io.open(slot_path(name), encoding='utf-8'))


def write_slot(name, data):
    os.makedirs(SAVES, exist_ok=True)
    tmp = slot_path(name) + '.tmp'
    io.open(tmp, 'w', encoding='utf-8').write(
        json.dumps(data, ensure_ascii=False, indent=2))
    os.replace(tmp, slot_path(name))


def set_active(name):
    """고른 세이브를 실제로 쓰이는 자리(chastate.json)로 복사한다."""
    os.makedirs(SAVES, exist_ok=True)
    io.open(ACTIVE, 'w', encoding='utf-8').write(name)
    shutil.copyfile(slot_path(name), LIVE)


def ensure_saves():
    """처음 실행이면 지금 쓰던 chastate.json 을 '기본' 슬롯으로 들여온다."""
    os.makedirs(SAVES, exist_ok=True)
    if slots():
        return
    if os.path.exists(LIVE):
        shutil.copyfile(LIVE, slot_path('기본'))
    else:
        write_slot('기본', _default_state())
    io.open(ACTIVE, 'w', encoding='utf-8').write('기본')


# ================================================================= ADB
# 기기가 둘 이상 꽂혀 있으면 adb 는 그냥 실패한다("more than one device").
# 그래서 고른 기기를 갈무리해 두고 모든 명령에 `-s <일련번호>` 를 붙인다.
def chosen_device():
    """고른 기기. 안 골랐거나 빠졌으면 None."""
    import chalang
    want = chalang.conf().get('device') or ''
    if not want:
        return None
    return want if want in adb_devices() else None


def pick_device(serial):
    import chalang
    chalang.save_conf(device=serial or '')
    return chosen_device()


def adb_cmd(*args):
    """`adb -s <기기> …` 를 만든다. 안 골랐으면 굳이 안 붙인다."""
    who = chosen_device()
    return ['adb'] + (['-s', who] if who else []) + list(args)


def adb_ok():
    r = _run(adb_cmd('get-state'))
    return r.returncode == 0 and 'device' in (r.stdout or '')


def adb_devices():
    """꽂혀 있는 기기의 일련번호. **여기만은** `-s` 를 붙이면 안 된다."""
    r = _run(['adb', 'devices'])
    out = []
    for ln in (r.stdout or '').splitlines()[1:]:
        if '\t' in ln and ln.split('\t')[1].strip() == 'device':
            out.append(ln.split('\t')[0])
    return out


def _label(pkg):
    for p, l in KNOWN_APPS:
        if p == pkg:
            return l
    return pkg


def adb_apps():
    """기기에 깔려 있는 우리 앱들. 폴더가 있으면 깔린 것으로 본다.

    `pm list packages` 는 이 기기에서 다중 사용자 권한 오류를 낸다.
    바깥 저장소 폴더는 앱이 한 번 돌면 생기고 shell 로 읽을 수 있다."""
    out = []
    for pkg, label in KNOWN_APPS:
        d = '/storage/emulated/0/Android/data/%s' % pkg
        r = _run(adb_cmd('shell', 'ls', '-d', d))
        if r.returncode == 0 and pkg in (r.stdout or ''):
            out.append({'pkg': pkg, 'label': label})
    return out


def _pick_pkg(pkg):
    """빈 값이면 기기에 있는 것 중 하나를 고른다. 하나뿐이면 그것으로."""
    if pkg:
        return pkg, ''
    apps = adb_apps()
    if len(apps) == 1:
        return apps[0]['pkg'], ''
    if not apps:
        return PKG, ''
    return apps[0]['pkg'], ('앱이 %d개 깔려 있어 %s 를 골랐습니다. '
                            '다른 쪽이면 목록에서 고르세요.'
                            % (len(apps), apps[0]['label']))


def adb_push_save(name, pkg=None):
    pkg, note = _pick_pkg(pkg)
    dst = device_save_of(pkg)
    _run(adb_cmd('shell', 'mkdir', '-p', os.path.dirname(dst)))
    r = _run(adb_cmd('push', slot_path(name), dst))
    msg = (r.stdout or '') + (r.stderr or '')
    return r.returncode == 0, (note + ' ' + msg).strip(), pkg


def adb_pull_save(name, pkg=None):
    pkg, note = _pick_pkg(pkg)
    tmp = os.path.join(SAVES, '.pulled.json')
    r = _run(adb_cmd('pull', device_save_of(pkg), tmp))
    if r.returncode != 0 or not os.path.exists(tmp):
        return False, (r.stderr or r.stdout or '기기에 세이브가 없습니다'), pkg
    shutil.move(tmp, slot_path(name))
    return True, (note or '가져왔습니다'), pkg


# ================================================================= 자산
def cmd_cars(args):
    import chaassets as A
    for c in A.car_list(TREE):
        mark = ' (가챠)' if c['gotya'] else ''
        print('%3d  %-16s %s  등급 %s%s'
              % (c['carNo'], c['name'], c['startClass'],
                 '/'.join(c['classes']), mark))


def _car_assets(idx, name, klass=None):
    """차 이름으로 (메시행, 텍스처행) 을 찾는다.

    자산 이름은 `Meteor_A` · `Lamborghini_S_LOW` 처럼 등급이 붙어 있다.
    정확한 이름이 오면 그걸 쓰고, 맨 이름이 오면 등급 붙은 것을 찾아본다.
    메시와 텍스처가 **같은 이름**에 함께 있는 쪽을 먼저 고른다."""
    import chaassets as A
    cands = [name]
    if klass:
        cands.append('%s_%s' % (name, klass))
    cands += ['%s_%s' % (name, s) for s in ('A', 'B', 'C', 'S', 'R', 'LOW')]
    mesh = tex = None
    for c in cands:
        m = A.find(idx, c, 'Mesh')
        t = A.find(idx, c, 'Texture2D')
        if m and t:
            return m[0], t[0]
        if m and not mesh:
            mesh = m[0]
        if t and not tex:
            tex = t[0]
    return mesh, tex


def _need_index():
    import chaassets as A
    idx = A.load_index()
    if idx is None:
        print('자산 색인이 없다. 만드는 중… (몇 분 걸린다)')
        idx = A.build_index(TREE, progress=lambda i, n, f:
                            sys.stdout.write('\r  %d/%d' % (i, n)))
        print()
    return idx


def cmd_extract(args):
    import chaassets as A
    idx = _need_index()
    out = args.out or os.path.join(HERE, 'extract', args.car)
    os.makedirs(out, exist_ok=True)
    mesh, tex = _car_assets(idx, args.car)
    if tex:
        png = os.path.join(out, args.car + '.png')
        size = A.export_texture(TREE, tex[0], tex[1], png)
        print('텍스처: %s (%dx%d)' % (png, size[0], size[1]))
    if mesh:
        v, uv, tri, nm = A.read_mesh(TREE, mesh[0], mesh[1])
        obj = os.path.join(out, args.car + '.obj')
        A.write_obj(obj, v, uv, tri, nm)
        c, e = A.bounds(v)
        print('메시: %s (정점 %d · 삼각형 %d · %.2f x %.2f x %.2f)'
              % (obj, len(v), len(tri) // 3, e[0] * 2, e[1] * 2, e[2] * 2))
        if tex:
            g = os.path.join(out, args.car + '_uv.png')
            A.uv_guide(png, uv, tri, g)
            print('UV 안내선: %s  ← 이 위에 칠하면 된다' % g)
    if not mesh and not tex:
        print('그런 이름의 자산이 없다: %s' % args.car)


def cmd_repaint(args):
    import chaassets as A
    idx = _need_index()
    _, tex = _car_assets(idx, args.car)
    if not tex:
        raise SystemExit('텍스처를 못 찾았다: %s' % args.car)
    n = A.import_texture(TREE, tex[0], tex[1], args.png)
    print('다시 칠했다: %s <- %s (%d바이트, 길이 보존)' % (args.car, args.png, n))
    print('이제 `chatool build --install` 로 APK 를 다시 만들어라.')


def cmd_import(args):
    import chaassets as A
    from sfparse import parse
    idx = _need_index()
    mesh, _ = _car_assets(idx, args.like)
    if not mesh:
        raise SystemExit('기준 차의 메시를 못 찾았다: %s' % args.like)
    v, uv, tri = A.read_obj(args.obj)
    if not v:
        raise SystemExit('OBJ 에 면이 없다')
    old_v, old_uv, old_tri, old_name = A.read_mesh(TREE, mesh[0], mesh[1])
    ctr, ext = A.bounds(old_v)
    if not args.no_fit:
        v = A.fit_to(v, ctr, ext)
    note = '감기 그대로'
    if args.winding == 'flip':
        A.flip_winding(tri)
        note = '감기 통째로 뒤집음'
    elif args.winding == 'auto':
        note = '감기 %d개 바깥쪽으로 맞춤' % A.orient(v, tri)
    c2, e2 = A.bounds(v)
    print('들여옴: 정점 %d · 삼각형 %d · %.2f x %.2f x %.2f · %s'
          % (len(v), len(tri) // 3, e2[0] * 2, e2[1] * 2, e2[2] * 2, note))
    p = os.path.join(TREE, A.DATA, mesh[0])
    sf = A._sf(p)
    o = sf.objects[mesh[1]]
    t = A.pack_mesh(o.read_typetree(), v, uv, tri, old_name)
    blob = bytes(o.save_typetree(t))
    # 백업은 **작업 트리 밖**에 둔다. 안에 두면 APK 에 같이 실려 들어간다.
    bdir = os.path.join(HERE, 'backup')
    os.makedirs(bdir, exist_ok=True)
    bak = os.path.join(bdir, mesh[0] + '.bak')
    if not os.path.exists(bak):
        shutil.copyfile(p, bak)
    size = A.replace_object(TREE, mesh[0], mesh[1], blob)
    print('교체 완료: %s (%d바이트)'
          % (mesh[0][:12], size))
    print('원본 백업: %s' % bak)
    print('이제 `chatool build --install` 로 APK 를 다시 만들어라.')
    print('차고에서 멀쩡해도 **주행 화면**을 꼭 확인하라. 까맣게 나오면')
    print('  `--winding flip` 으로 다시 넣으면 된다.')


# ================================================================= 빌드
MANAGED = os.path.join('assets', 'bin', 'Data', 'Managed')
def _find_csc():
    """`ChaLocal.dll` 을 구울 컴파일러를 찾는다.

    **v3.5 여야 합니다.** 이 게임의 mscorlib 는 .NET 2.0 이라 최신 컴파일러로
    구우면 없는 것을 참조해 기기에서 죽습니다. 윈도우가 어느 드라이브에
    깔렸든 찾도록 `SystemRoot` 에서 출발합니다. `CHA_CSC` 로 직접 짚어 줄
    수도 있습니다."""
    env = os.environ.get('CHA_CSC')
    if env and os.path.exists(env):
        return env
    root = (os.environ.get('SystemRoot') or os.environ.get('WINDIR')
            or os.path.join('C:', os.sep, 'Windows'))
    base = os.path.join(root, 'Microsoft.NET', 'Framework')
    for v in ('v3.5', 'v2.0.50727'):
        p = os.path.join(base, v, 'csc.exe')
        if os.path.exists(p):
            return p
    return os.path.join(base, 'v3.5', 'csc.exe')      # 없으면 이 이름으로 알림


CSC = _find_csc()


def _newer(a, b):
    """a 를 b 로 다시 베껴야 하는가(또는 b 가 없는가).

    시각만 보면 **되돌린 파일을 놓친다.** `shutil.copy2` 는 원본 시각을
    그대로 물려주므로, 예전 번들을 backup 에서 되살리면 그 시각이 이미
    담아 둔 것보다 옛것이 되어 다시 안 베낀다 — 낡은 번들이 그대로 APK 에
    들어간다(실기에서 겪었다). 크기가 다르면 시각과 무관하게 베낀다."""
    if not os.path.exists(b):
        return True
    if not os.path.exists(a):
        return False
    if os.path.getsize(a) != os.path.getsize(b):
        return True
    return os.path.getmtime(a) > os.path.getmtime(b)


def _bake_save(slot, say):
    """고른 세이브를 ChaLocalData.cs 에 굽는다. 그 APK 의 시작 상태가 된다.

    APK 는 한 벌이므로 여기가 유일한 '판' 이다. 다른 상태로 시작하고
    싶으면 세이브를 바꿔 굽거나, 폰에 세이브를 넣으면 된다."""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    cmd = [sys.executable, os.path.join(CODE, 'mkskel.py'), '--pkg', PKG]
    if slot and slot in slots():
        cmd += ['--save', slot_path(slot)]
    r = _run(cmd, cwd=HERE, env=env)
    if r.returncode != 0:
        say((r.stdout or '') + (r.stderr or ''))
        raise SystemExit('세이브를 굽지 못했습니다')
    say('구워 넣는 세이브: %s' % (slot or '(기본값)'))


def _ensure_cecil():
    """Cecil 로 만든 패처 exe 들은 Mono.Cecil.dll 이 **제 옆에** 있어야 돈다.

    .NET 은 어셈블리를 실행파일이 놓인 폴더에서 찾는다. 저장소에서는 그 DLL 을
    patch/ 에 두므로, 패처를 돌리기 전에 작업 폴더로 한 벌 가져다 놓는다.
    """
    src = os.path.join(HERE, 'patch', 'Mono.Cecil.dll')
    dst = os.path.join(HERE, 'Mono.Cecil.dll')
    if os.path.exists(src) and _newer(src, dst):
        shutil.copy2(src, dst)
    return dst


def _make_local_dll(say, force=False):
    """ChaLocal.dll 과 ACLOCAL.dll 을 (필요하면) 다시 만든다."""
    _ensure_cecil()
    src = [os.path.join(HERE, 'patch', f)
       for f in ('ChaLocal.cs', 'ChaLocalData.cs')]
    dll = os.path.join(HERE, 'ChaLocal.dll')
    if force or any(_newer(x, dll) for x in src):
        if not os.path.exists(CSC):
            raise SystemExit(
                'ChaLocal.cs 를 구울 csc(v3.5) 를 못 찾았습니다.\n'
                '  찾아본 자리: %s\n'
                '  윈도우에서 .NET Framework 3.5 를 켜거나, 자리를 알려 주세요:\n'
                '      set CHA_CSC=<csc.exe 자리>' % CSC)
        # csc(v3.5) 는 슬래시를 옵션 머리로 보므로 소스는 **절대 경로**로 준다.
        r = _run([CSC, '-nologo', '-noconfig', '-target:library',
                  '-out:ChaLocal.dll', '-r:mgbase/UnityEngine.dll'] + src,
                 cwd=HERE)
        if r.returncode != 0:
            say((r.stdout or '') + (r.stderr or ''))
            raise SystemExit('ChaLocal.dll 컴파일 실패')
        say('ChaLocal.dll 을 다시 만들었습니다')
    acc = os.path.join(HERE, 'ACCN.dll')
    out = os.path.join(HERE, 'ACLOCAL.dll')
    if force or _newer(acc, out) or _newer(dll, out):
        r = _run([os.path.join(HERE, 'localfix.exe'), 'ACCN.dll', 'ACLOCAL.dll',
                  'ChaLocal.dll', 'mgbase'], cwd=HERE)
        say(((r.stdout or '') + (r.stderr or '')).strip())
        if r.returncode != 0:
            raise SystemExit('localfix 실패')
    return dll, out


def _stage(mode, say, slot=None):
    """x77 작업 트리를 고른 모드에 맞게 맞춘다."""
    mgd = os.path.join(TREE, MANAGED)
    tgt = os.path.join(mgd, 'Assembly-CSharp.dll')
    helper = os.path.join(mgd, 'ChaLocal.dll')
    bundle_src = os.path.join(HERE, 'bundles', 'pack.unity3d')
    bundle_dst = os.path.join(TREE, 'assets', 'pack.unity3d')
    if mode in ('local', 'both'):
        # 'both' 도 로컬판과 **같은 것을 굽는다.** ChaLocal 안의 갈고리들이
        # `chamode.txt` 를 보고 갈리므로, 한 벌에 두 길이 다 들어 있다.
        # 서버로 갈 때 쓸 주소는 자산에 이미 박혀 있다(chahost).
        _bake_save(slot, say)
        dll, acl = _make_local_dll(say, force=True)
        shutil.copyfile(acl, tgt)
        shutil.copyfile(dll, helper)
        # 복원 자산 번들은 PC 에서 받는 대신 APK 안에 넣는다
        if os.path.exists(bundle_src):
            if _newer(bundle_src, bundle_dst):
                shutil.copyfile(bundle_src, bundle_dst)
            say('번들 동봉: %.1f MB' % (os.path.getsize(bundle_dst) / 1048576.0))
        else:
            say('[주의] bundles/pack.unity3d 가 없습니다. 복원한 맵이 빠집니다.')
        say(_msg('로컬 전용으로 맞췄습니다 (서버 없이 돕니다)') if mode == 'local'
            else _msg('한 벌에 둘 다 넣었습니다. 게임 안에서 판을 바꿉니다.'))
    else:
        acc = os.path.join(HERE, 'ACCN.dll')
        if os.path.exists(acc):
            shutil.copyfile(acc, tgt)
        for p in (helper, bundle_dst):
            if os.path.exists(p):
                os.remove(p)
        say('서버용으로 맞췄습니다 (PC 의 chacnserver.py 가 있어야 합니다)')


def cmd_newcar(args):
    """모델을 새 차로 추가합니다. 기존 차를 덮어쓰지 않습니다."""
    import newcar
    newcar.add(args.name, args.obj, args.png, args.label, args.klass,
               args.gold, args.trophy, args.winding, not args.no_fit)


def cmd_build(args):
    build_apk(args.mode, getattr(args, 'slot', None),
              getattr(args, 'out', None), args.install, print)


def build_apk(mode, slot=None, out=None, install=False, say=print):
    """APK 한 벌을 굽는다. 얼굴(터미널·Flet 런처)이 같이 쓴다.

    `say` 는 한 줄씩 받아 가는 함수다. 터미널은 print, 창 런처는 화면에
    붙인다. 실패하면 SystemExit 을 던진다."""
    # APK 는 한 벌입니다. 시작 상태는 **지금 고른 세이브**를 구워 넣습니다.
    slot = slot or active_name()
    _stage(mode, say, slot)
    out = out or 'chachacha_revive.apk'
    steps = [
        ([sys.executable, os.path.join(CODE, 'pack.py'),
          'base.apk', 'chacn.apk', 'x77'], 'APK 재조립'),
        ([sys.executable, os.path.join(CODE, 'setappname.py'), 'chacn.apk', '_named.apk',
          '一起车车车', APP_LABEL], '앱 이름'),
        ([sys.executable, os.path.join(CODE, 'setpkg.py'),
          '_named.apk', out, PKG], '패키지 이름'),
        (['jarsigner', '-keystore', 'test.keystore', '-storepass', 'android',
          '-keypass', 'android', out, 'test'], '서명'),
    ]
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    for cmd, step in steps:          # `label` 은 앱 이름이라 덮어쓰면 안 된다
        r = _run(cmd, cwd=HERE, env=env)
        tail = (r.stdout or '').strip().splitlines()
        say('%-12s %s' % (step, tail[-1] if tail else 'ok'))
        if r.returncode != 0:
            say((r.stderr or '')[:400])
            raise SystemExit('%s 에서 실패' % step)
    say('만들었습니다: %s' % out)
    if install:
        r = _run(adb_cmd('install', '-r', '--bypass-low-target-sdk-block',
                         out), cwd=HERE)
        say('설치: %s' % ((r.stdout or '').strip().splitlines() or ['?'])[-1])
    if mode in ('local', 'both'):
        say('앱 이름 %s · 패키지 %s' % (APP_LABEL, PKG))
        say('구워 넣은 세이브: %s' % (slot or '(기본)'))
        say('세이브는 폰 안 %s 에 있습니다.' % DEVICE_SAVE)
        say("런처의 '기기에 넣기'로 올리고 '기기에서 가져오기'로 되받으면 됩니다.")


def cmd_index(args):
    import chaassets as A
    A.build_index(TREE, progress=lambda i, n, f:
                  sys.stdout.write('\r  %d/%d  %s   ' % (i, n, f[:12])))
    print('\n색인 완료: %s' % A.INDEX)


def cmd_pack_exe(args):
    """파이선 없는 PC 용 단일 실행파일."""
    # 런처 자체는 표준 라이브러리만 쓴다. Qt 계열이 둘 이상 깔려 있으면
    # PyInstaller 가 충돌로 멈추므로 아예 뺀다(쓰지도 않는다).
    # flet(창 런처)은 저장소에서 뺐습니다. exe 는 브라우저 런처만 담습니다.
    skip = ['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'nicegui', 'flet',
            'matplotlib',
            'tkinter', 'IPython', 'pytest', 'numpy.f2py']
    cmd = [sys.executable, '-m', 'PyInstaller', '--onefile', '--name', 'chatool',
           '--console', '--noconfirm',
           '--collect-all', 'UnityPy',
           # UnityPy 가 소리 자산 때문에 fmod 를 딸고 온다. DLL 과 그 밑의
           # archspec 자료까지 담아야 뽑기가 돈다(모듈만 담으면 죽는다).
           '--collect-all', 'fmod_toolkit',
           '--collect-all', 'archspec',
           # 창 런처가 쓰는 것들
           '--collect-all', 'webview', '--collect-all', 'clr_loader',
           '--collect-all', 'pythonnet']
    # archspec 의 자료는 archspec/json/ 인데 __init__.py 가 없어
    # --collect-all 이 못 본다. 자리를 찾아 손으로 붙인다.
    try:
        import archspec
        jd = os.path.join(os.path.dirname(archspec.__file__), 'json')
        if os.path.isdir(jd):
            cmd += ['--add-data', '%s%sarchspec/json' % (jd, os.pathsep)]
    except Exception:
        pass
    for m in skip:
        cmd += ['--exclude-module', m]
    cmd += ['--hidden-import', 'newcar', '--hidden-import', 'mkpack',
            '--hidden-import', 'mktaegeuk', '--hidden-import', 'sfmerge',
            '--hidden-import', 'mkbundle', '--hidden-import', 'sfwrite',
            '--hidden-import', 'chaassets', '--hidden-import', 'chatool_page',
            '--hidden-import', 'chatool_assets',
            '--hidden-import', 'chatool_page_assets',
            '--hidden-import', 'chastate', '--hidden-import', 'sfparse',
            # _api 안에서 늦게 들여오는 것들. 손으로 적어 줘야 담깁니다.
            '--hidden-import', 'chasaves', '--hidden-import', 'chabuild',
            '--hidden-import', 'chahost', '--hidden-import', 'chalog',
            '--hidden-import', 'chaproj', '--hidden-import', 'chaskill',
            '--hidden-import', 'chadrv', '--hidden-import', 'chapick',
            os.path.join(CODE, 'chatool.py')]
    print('PyInstaller 실행 중… (몇 분 걸린다)')
    r = subprocess.run(cmd, cwd=HERE)
    if r.returncode == 0:
        print('완성: %s' % os.path.join(HERE, 'dist', 'chatool.exe'))
        print('이 exe 하나만 있으면 파이선 없이 웹 런처가 돌아간다.')
    return r.returncode


# ================================================================= 런처 서버
# 세이브 두 벌을 견줘 **달라진 칸 이름**만 뽑는다.
_SAVE_LABEL = {
    'player.nickName': '별명', 'player.gold': '골드', 'player.trophy': '트로피',
    'player.tire': '타이어', 'player.car': '타는 차', 'player.driver': '드라이버',
    'carsOwned': '보유 차량', 'driversOwned': '보유 드라이버',
    'carClass': '차 등급', 'carTune': '차 튜닝', 'items': '아이템',
    'skills': '스킬', 'invite.count': '초대 횟수', 'dormancy.days': '휴면 일수',
    'notice.title': '공지 제목', 'notice.body': '공지 내용',
    'records': '기록', 'presents': '수신함', 'preset': '프리셋',
}


_SKILLMETA = [None]


def _skill_meta():
    """스킬 표. 자산에서 읽으므로 한 번만 읽고 붙들어 둔다."""
    if _SKILLMETA[0] is None:
        try:
            import chaskill
            _SKILLMETA[0] = chaskill.meta(TREE)
        except Exception:
            _SKILLMETA[0] = []
    return _SKILLMETA[0]


def _flat(d, pre=''):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            key = pre + k
            if isinstance(v, dict) and key in ('player', 'invite', 'notice',
                                               'dormancy'):
                out.update(_flat(v, key + '.'))
            else:
                out[key] = json.dumps(v, ensure_ascii=False, sort_keys=True)
    return out


def _what_changed(before, after):
    a, b = _flat(before), _flat(after)
    out = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            out.append(_SAVE_LABEL.get(k, k))
    return out


def _msg(src, **kw):
    """화면에 뜨는 말. 지금 고른 언어로 옮긴다.

    열쇠가 한국어 원문 그대로라, 번역이 없으면 한국어가 나옵니다."""
    import chalang
    out = chalang.t(src, **kw)
    return out


def _api(path, body):
    """런처 백엔드. 웹 얼굴과 창 얼굴이 **똑같이** 이걸 쓴다."""
    import chastate
    ensure_saves()
    import chalog

    if path == '/api/ui':
        import chalang
        c = chalang.conf()
        return {'ok': True, 'lang': c['lang'], 'theme': c['theme'],
                'langs': chalang.codes(), 'strings': chalang.pack(c['lang'])}

    if path == '/api/ui/set':
        import chalang
        chalang.reload()
        c = chalang.save_conf(lang=body.get('lang'), theme=body.get('theme'))
        return {'ok': True, 'lang': c['lang'], 'theme': c['theme'],
                'strings': chalang.pack(c['lang'])}

    if path == '/api/state':
        name = active_name()
        return {
            'slots': slots(),
            'active': name,
            'data': read_slot(name) if name else None,
            'meta': {
                'cars': [{'no': i, 'name': n, 'cls': c}
                         for i, n, c in chastate.CARS],
                'drivers': [{'no': i, 'name': n} for i, n in chastate.DRIVERS],
                'items': chastate.ITEMS,
                'skills': _skill_meta(),
                'presets': [{'key': k, 'label': chastate.PRESET_LABEL.get(k, k)}
                            for k in chastate.PRESETS],
                'pkg': PKG, 'app': APP_LABEL,
                'max': {'gold': chastate.MAX_GOLD,
                        'trophy': chastate.MAX_TROPHY,
                        'tire': chastate.MAX_TIRE},
            },
            'adb': {'ok': adb_ok(), 'devices': adb_devices(),
                    'chosen': chosen_device() or ''},
        }

    if path == '/api/save':
        name = body.get('name') or active_name()
        data = body['data']
        # 무엇이 달라졌는지 한 줄로 남긴다. 값 하나하나가 아니라 **어느 칸이**
        # 달라졌는지만 적는다 — 나중에 내역만 보고도 감이 잡힌다.
        before = read_slot(name) if name in slots() else {}
        write_slot(name, data)
        if name == active_name():
            shutil.copyfile(slot_path(name), LIVE)
        diff = _what_changed(before, data)
        chalog.add('save', _msg('세이브를 저장했습니다: %s%s')
                   % (name, (' — ' + ' · '.join(diff)) if diff else ''),
                   {'바뀐 칸': diff} if diff else None)
        return {'ok': True, 'msg': _msg('저장했습니다: %s') % name,
                'changed': diff}

    if path == '/api/slot/new':
        name = (body.get('name') or '').strip() or _msg('새 세이브')
        base = name
        k = 2
        while name in slots():
            name = '%s %d' % (base, k)
            k += 1
        src = body.get('copyFrom')
        write_slot(name, read_slot(src) if src in slots() else _default_state())
        chalog.add('save', _msg('세이브를 만들었습니다: %s%s')
                   % (name, (_msg(' (%s 복제)') % src) if src in slots() else ''))
        return {'ok': True, 'name': name, 'msg': _msg('만들었습니다: %s') % name}

    if path == '/api/slot/select':
        name = body['name']
        if name not in slots():
            return {'ok': False, 'msg': _msg('그런 세이브가 없습니다')}
        set_active(name)
        chalog.add('save', _msg('세이브를 골랐습니다: %s') % name)
        return {'ok': True, 'msg': _msg('이제 이것을 씁니다: %s') % name}

    if path == '/api/slot/delete':
        name = body['name']
        if name not in slots():
            return {'ok': False, 'msg': _msg('그런 세이브가 없습니다')}
        if len(slots()) == 1:
            return {'ok': False, 'msg': _msg('마지막 하나는 지울 수 없습니다')}
        os.remove(slot_path(name))
        if active_name() is None or name == body.get('active'):
            set_active(slots()[0])
        chalog.add('save', _msg('세이브를 지웠습니다: %s') % name)
        return {'ok': True, 'msg': _msg('지웠습니다: %s') % name}

    if path == '/api/slot/rename':
        old, new = body['name'], (body.get('to') or '').strip()
        if not new or new in slots():
            return {'ok': False, 'msg': _msg('쓸 수 없는 이름입니다')}
        os.rename(slot_path(old), slot_path(new))
        if active_name() == old or not os.path.exists(ACTIVE):
            set_active(new)
        chalog.add('save', _msg('세이브 이름을 바꿨습니다: %s -> %s') % (old, new))
        return {'ok': True, 'msg': _msg('이름을 바꿨습니다: %s') % new}

    # ---------------------------------------------------------- 세이브 파일
    if path == '/api/slot/preset':
        # 프리셋으로 세이브를 새로 만든다. 프리셋은 이제 **세이브의 밑그림**이다.
        key = body.get('preset') or ''
        if key not in chastate.PRESETS:
            return {'ok': False, 'msg': _msg('그런 프리셋이 없습니다: %s') % key}
        name = (body.get('name') or '').strip()             or chastate.PRESET_LABEL.get(key, key)
        base, k = name, 2
        while name in slots():
            name = '%s %d' % (base, k)
            k += 1
        write_slot(name, chastate.preset(key))
        set_active(name)
        chalog.add('save', _msg('프리셋으로 세이브를 만들었습니다: %s (%s)')
                   % (name, key))
        return {'ok': True, 'name': name,
                'msg': _msg('만들었습니다: %s') % name}

    if path == '/api/slot/export':
        import chapick
        name = body.get('name') or active_name()
        if name not in slots():
            return {'ok': False, 'msg': _msg('그런 세이브가 없습니다')}
        dst = chapick.save_file(_msg('세이브를 어디에 저장할까요'),
                                chapick.default_dir(HERE), name + '.json')
        if not dst:
            return {'ok': False, 'msg': _msg('취소했습니다')}
        shutil.copyfile(slot_path(name), dst)
        chalog.add('save', _msg('세이브를 파일로 내보냈습니다: %s') % dst)
        return {'ok': True, 'msg': _msg('내보냈습니다: %s') % dst}

    if path == '/api/slot/import':
        import chapick
        src = chapick.open_file(_msg('세이브 파일을 고르세요'),
                                chapick.default_dir(HERE))
        if not src:
            return {'ok': False, 'msg': _msg('취소했습니다')}
        try:
            data = json.load(io.open(src, encoding='utf-8'))
        except Exception as e:
            return {'ok': False, 'msg': _msg('세이브 파일이 아닙니다: %s') % e}
        name = os.path.splitext(os.path.basename(src))[0]
        base, k = name, 2
        while name in slots():
            name = '%s %d' % (base, k)
            k += 1
        write_slot(name, data)
        set_active(name)
        chalog.add('save', _msg('세이브를 파일에서 읽었습니다: %s -> %s') % (src, name))
        return {'ok': True, 'msg': _msg('읽었습니다: %s') % name}

    # ---------------------------------------------------------- 드라이버
    if path == '/api/driver/list':
        import chadrv
        import chatool_assets as CA
        rows = chadrv.profiles(TREE)
        d = os.path.join(CA.extract_dir(), '_drivers')
        os.makedirs(d, exist_ok=True)
        for r in rows:
            png = os.path.join(d, 'drv%02d.png' % r['no'])
            if not os.path.exists(png):
                try:
                    chadrv.portrait(TREE, r['no'], png)
                except Exception:
                    pass
            r['png'] = ('_drivers/drv%02d.png' % r['no'])                 if os.path.exists(png) else None
        return {'ok': True, 'rows': rows, 'base': chadrv.BASE_DRIVER}

    if path == '/api/driver/text':
        import chadrv
        no = int(body.get('no') or 0)
        if not 1 <= no <= chadrv.COUNT:
            return {'ok': False, 'msg': _msg('그런 드라이버가 없습니다')}
        done = []
        try:
            for key, val in (('Char%d' % no, body.get('name')),
                             ('Char%dExp' % no, body.get('exp'))):
                if val is None:
                    continue
                old_v = chadrv.set_text(TREE, key, val)
                done.append('%s: %r -> %r' % (key, old_v, val))
        except Exception as e:
            return {'ok': False, 'msg': str(e)}
        if done:
            chalog.add('asset', _msg('드라이버 %d번 글을 고쳤습니다') % no,
                       {'바꾼 것': done})
        return {'ok': True, 'msg': _msg('고쳤습니다') if done else _msg('바꿀 것이 없습니다'),
                'done': done}

    if path == '/api/driver/export':
        import chadrv
        import chatool_assets as CA
        nos = [int(x) for x in (body.get('nos') or []) if str(x).isdigit()]
        if not nos:
            return {'ok': False, 'msg': _msg('드라이버를 골라 주세요')}
        import chapick
        root = body.get('dir') or chapick.folder(
            _msg('드라이버를 어디에 내보낼까요'), chapick.default_dir(HERE))
        if not root:
            return {'ok': False, 'msg': _msg('취소했습니다')}

        def go(say):
            os.makedirs(root, exist_ok=True)
            say(_msg('%s 로 내보냅니다') % root)
            n = 0
            for no in nos:
                n += len(chadrv.export(TREE, no, root, say))
            chalog.add('asset', _msg('드라이버 %d명을 내보냈습니다') % len(nos),
                       {'번호': nos})
            say(_msg('끝났습니다. 파일 %d개') % n)
            say('@@' + json.dumps({'dir': root, 'files': n},
                                  ensure_ascii=False))
        import chatool_assets
        return {'ok': True, 'job': chatool_assets.run_job(
            _msg('드라이버 내보내기'), go)}

    # ---------------------------------------------------------- 내역·프로젝트
    if path == '/api/log':
        import chalog
        return {'ok': True, 'rows': chalog.read(
            int(body.get('limit') or 400), body.get('kind') or None,
            (body.get('find') or '').strip() or None)}

    if path == '/api/log/clear':
        import chalog
        return {'ok': chalog.clear(), 'msg': _msg('기록을 비웠습니다')}

    if path == '/api/log/export':
        import chalog
        import chatool_assets
        p2 = chalog.export()
        chatool_assets.open_folder(os.path.dirname(p2))
        return {'ok': True, 'path': p2, 'msg': _msg('내보냈습니다: %s') % p2}

    if path == '/api/proj/list':
        import chaproj
        return {'ok': True, 'items': chaproj.items()}

    if path == '/api/proj/save':
        import chaproj
        name = (body.get('name') or '').strip()
        if not name:
            return {'ok': False, 'msg': _msg('이름을 적어 주세요')}
        cur = active_name()
        d = chaproj.save(name, read_slot(cur) if cur else _default_state(),
                         body.get('preset') or '', body.get('note') or '',
                         body.get('mark') or '')
        return {'ok': True, 'msg': _msg('프로젝트를 저장했습니다: %s') % name,
                'saved': d['saved']}

    if path == '/api/proj/load':
        import chaproj
        import chalog
        name = (body.get('name') or '').strip()
        try:
            d = chaproj.load(name)
        except KeyError as e:
            return {'ok': False, 'msg': str(e)}
        slot = body.get('into') or (_msg('%s (프로젝트)') % name)
        write_slot(slot, d.get('save') or _default_state())
        set_active(slot)
        chalog.add('project', _msg('프로젝트를 불러왔습니다: %s -> 세이브 %s')
                   % (name, slot))
        return {'ok': True, 'msg': _msg('불러왔습니다: %s (세이브 %s)') % (name, slot)}

    if path == '/api/proj/delete':
        import chaproj
        return {'ok': chaproj.remove((body.get('name') or '').strip()),
                'msg': _msg('지웠습니다')}

    if path == '/api/proj/rename':
        import chaproj
        try:
            chaproj.rename(body.get('name') or '', (body.get('to') or '').strip())
        except Exception as e:
            return {'ok': False, 'msg': str(e)}
        return {'ok': True, 'msg': _msg('이름을 바꿨습니다')}

    if path == '/api/adb/pick':
        # 기기가 둘 이상이면 어느 쪽에 넣을지 골라야 한다.
        who = pick_device(body.get('serial') or '')
        return {'ok': True, 'chosen': who or '',
                'msg': _msg('이 기기를 씁니다: %s') % who if who
                       else _msg('기기를 자동으로 고릅니다')}

    if path == '/api/adb/mode':
        # 폰의 판을 바꾼다. 앱 안 겹판에서도 바꿀 수 있지만, 여기서 하면
        # 굽지 않고도 갈아 끼울 수 있다. 앱은 껐다 켜야 먹는다.
        want = 'server' if (body.get('mode') == 'server') else 'local'
        tmp = os.path.join(SAVES, '.chamode.txt')
        io.open(tmp, 'w', encoding='utf-8').write(want)
        remote = ('/storage/emulated/0/Android/data/%s/files/chamode.txt' % PKG)
        _run(adb_cmd('shell', 'mkdir', '-p', os.path.dirname(remote)))
        r = _run(adb_cmd('push', tmp, remote))
        ok = r.returncode == 0
        try:
            os.remove(tmp)
        except OSError:
            pass
        if ok:
            chalog.add('device', _msg('폰의 판을 %s 로 바꿨습니다') % want)
        return {'ok': ok, 'mode': want,
                'msg': _msg('폰의 판을 %s 로 바꿨습니다. 앱을 껐다 켜세요.')
                       % want if ok
                       else ((r.stderr or r.stdout or '').strip())}

    if path == '/api/adb/apps':
        return {'ok': True, 'apps': adb_apps(), 'known': [
            {'pkg': p, 'label': l} for p, l in KNOWN_APPS]}

    if path == '/api/adb/push':
        name = body.get('name') or active_name()
        ok, msg, pkg = adb_push_save(name, body.get('pkg'))
        chalog.add('device', (_msg('%s 에 세이브를 넣었습니다: %s') % (_label(pkg), name))
                   if ok else (_msg('세이브 넣기 실패: %s') % msg))
        return {'ok': ok, 'msg': (_msg('%s 에 넣었습니다: %s')
                                  % (_label(pkg), name)) if ok else msg}

    if path == '/api/adb/pull':
        name = body.get('name') or (_msg('기기 %s') % time.strftime('%m%d-%H%M'))
        ok, msg, pkg = adb_pull_save(name, body.get('pkg'))
        chalog.add('device', (_msg('%s 에서 세이브를 가져왔습니다: %s')
                              % (_label(pkg), name)) if ok
                   else (_msg('세이브 가져오기 실패: %s') % msg))
        return {'ok': ok, 'msg': (_msg('%s 에서 가져왔습니다: %s')
                                  % (_label(pkg), name)) if ok else msg}

    # ---------------------------------------------------- 세이브 들여다보기
    # 목록에 한 줄 요약을 붙이고, 고른 것의 속을 펼칩니다. 창 런처에만
    # 있던 것을 브라우저 얼굴에도 붙였습니다.
    if path == '/api/slot/brief':
        import chasaves
        out = {}
        for n in slots():
            try:
                out[n] = chasaves.brief(read_slot(n), _msg)
            except Exception as e:
                out[n] = _msg('읽을 수 없습니다 (%s)') % e
        return {'ok': True, 'brief': out}

    if path == '/api/slot/detail':
        import chasaves
        name = body.get('name') or active_name()
        if not name or name not in slots():
            return {'ok': False, 'msg': _msg('그런 세이브가 없습니다')}
        data = read_slot(name)
        st = chasaves.stat(name)
        return {'ok': True, 'name': name, 'path': slot_path(name),
                'when': st['when'], 'size': st['size'],
                'active': active_name() == name,
                'brief': chasaves.brief(data, _msg),
                'sections': [{'key': k, 'title': t, 'rows': r}
                             for (k, _kr), (t, r)
                             in zip(chasaves.sections(data),
                                    chasaves.sections(data, _msg))],
                'cars': [{'cls': c, 'names': ns}
                         for c, ns in chasaves.car_lines(data)]}

    if path == '/api/slot/presets':
        import chasaves
        return {'ok': True, 'presets': chasaves.presets(_msg)}

    # ---------------------------------------------------------- 폰 세이브
    # 앱이 읽는 chasave.json 하나만이 아니라, 게임 안 겹판이 만든
    # slot01.json … 과 예전에 깔았던 패키지까지 함께 훑습니다.
    if path == '/api/dev/list':
        import chasaves
        if not adb_ok():
            return {'ok': True, 'adb': False, 'saves': [],
                    'msg': _msg('폰이 연결되어 있지 않습니다')}
        rows = chasaves.device_saves(_msg)
        return {'ok': True, 'adb': True, 'saves': rows,
                'msg': (_msg('세이브 %d개를 찾았습니다') % len(rows)) if rows
                       else _msg('폰에 세이브가 없습니다')}

    if path == '/api/dev/peek':
        import chasaves
        data, err = chasaves.device_read(body.get('remote') or '', _msg)
        if data is None:
            return {'ok': False, 'msg': err}
        return {'ok': True, 'brief': chasaves.brief(data, _msg),
                'sections': [{'key': k, 'title': t, 'rows': r}
                             for (k, _kr), (t, r)
                             in zip(chasaves.sections(data),
                                    chasaves.sections(data, _msg))],
                'cars': [{'cls': c, 'names': ns}
                         for c, ns in chasaves.car_lines(data)]}

    if path == '/api/dev/pull':
        import chasaves
        nm, err = chasaves.device_pull(body.get('remote') or '',
                                       body.get('name'), _msg)
        if not nm:
            return {'ok': False, 'msg': err}
        chalog.add('device', _msg("폰에서 '%s' 를 가져왔습니다") % nm,
                   body.get('remote'))
        return {'ok': True, 'name': nm, 'msg': _msg("'%s' 로 가져왔습니다") % nm}

    if path == '/api/dev/push':
        import chasaves
        name = body.get('name') or active_name()
        remote = body.get('remote') or None
        ok, msg = chasaves.device_push(name, remote)
        if ok:
            chalog.add('device', _msg("'%s' 를 폰에 넣었습니다") % name, remote)
        return {'ok': ok, 'msg': _msg('폰에 넣었습니다') if ok else msg}

    if path == '/api/dev/rm':
        import chasaves
        remote = body.get('remote') or ''
        ok, msg = chasaves.device_remove(remote, _msg)
        if ok:
            chalog.add('device', _msg('폰에서 %s 를 지웠습니다')
                       % os.path.basename(remote), remote)
        return {'ok': ok, 'msg': _msg('지웠습니다') if ok else msg}

    # ------------------------------------------------------------ 굽기 설정
    if path == '/api/build/ways':
        import chabuild
        info = chabuild.ways(_msg)
        return {'ok': True, 'ways': info['ways'], 'limit': info['limit'],
                'now': info['now'], 'conf': chabuild.load_conf()}

    if path == '/api/build/conf':
        import chabuild
        chabuild.save_conf(body or {})
        return {'ok': True}

    if path == '/api/build/stale':
        import chabuild
        return {'ok': True, 'apk': chabuild.OUT, 'when': chabuild.apk_when(),
                'rows': [{'what': _msg(w), 'rel': r}
                         for w, r in chabuild.stale()]}

    if path == '/api/build/fresh':
        import chabuild
        nm = chabuild.fresh_save()
        return {'ok': True, 'name': nm, 'msg': _msg("'%s' 를 만들었습니다") % nm}

    if (path.startswith('/api/assets/') or path.startswith('/api/build')
            or path == '/api/job'):
        import chatool_assets
        return chatool_assets.api(path, body)

    return {'ok': False, 'msg': _msg('모르는 요청입니다: %s') % path}


def serve(host='127.0.0.1', port=8099, open_browser=True):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, ctype, data):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ('/', '/index.html'):
                self._send(200, 'text/html; charset=utf-8', PAGE.encode('utf-8'))
            elif self.path.startswith('/file?'):
                # 뽑아 놓은 텍스처·안내선·OBJ 를 화면에 보여 주기 위한 통로.
                import urllib.parse
                import chatool_assets
                q = urllib.parse.parse_qs(self.path.split('?', 1)[1])
                blob, ctype = chatool_assets.serve_file((q.get('p') or [''])[0])
                if blob is None:
                    self._send(404, 'text/plain; charset=utf-8', b'no')
                else:
                    self._send(200, ctype, blob)
            elif self.path.startswith('/api/'):
                try:
                    r = _api(self.path, {})
                except Exception as e:
                    r = {'ok': False, 'msg': '%s: %s' % (type(e).__name__, e)}
                self._send(200, 'application/json; charset=utf-8',
                           json.dumps(r, ensure_ascii=False).encode('utf-8'))
            else:
                self._send(404, 'text/plain; charset=utf-8', b'no')

        def do_POST(self):
            n = int(self.headers.get('Content-Length') or 0)
            try:
                body = json.loads(self.rfile.read(n) or b'{}')
            except Exception:
                body = {}
            try:
                r = _api(self.path, body)
            except Exception as e:
                r = {'ok': False, 'msg': '%s: %s' % (type(e).__name__, e)}
            self._send(200, 'application/json; charset=utf-8',
                       json.dumps(r, ensure_ascii=False).encode('utf-8'))

    # 화면은 `main()` 이 채워 넣지만, 서버를 직접 부르는 길도 있다
    # (창 런처 · 시험). 비어 있으면 여기서 들여온다 — 안 그러면 빈 쪽이 나간다.
    global PAGE
    if not PAGE:
        import chatool_page
        PAGE = chatool_page.PAGE

    ensure_saves()
    srv = ThreadingHTTPServer((host, port), H)
    url = 'http://%s:%d/' % ('127.0.0.1' if host == '0.0.0.0' else host, port)
    print('차차차 런처: %s' % url)
    print('(끄려면 Ctrl+C)')
    if open_browser:
        import threading
        import webbrowser
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\n끝냈습니다')
    return url


def cmd_web(args):
    serve(args.host, args.port, open_browser=not args.no_open)


def cmd_app(args):
    """창 런처. 백엔드는 웹 런처와 같은 것을 쓴다."""
    import threading
    t = threading.Thread(target=serve,
                         args=(args.host, args.port, False), daemon=True)
    t.start()
    time.sleep(0.8)
    url = 'http://127.0.0.1:%d/' % args.port
    try:
        import webview
        webview.create_window('다함께 차차차 — 런처', url,
                              width=1280, height=880,
                              min_size=(980, 640), text_select=True)
        webview.start()
        return
    except Exception:
        pass
    print('창을 못 열었습니다. 브라우저로 엽니다.')
    import webbrowser
    webbrowser.open(url)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\n끝냈습니다')


PAGE = ''  # 아래에서 채운다 (chatool_page.py)


def main():
    global PAGE
    import chatool_page
    PAGE = chatool_page.PAGE

    import argparse
    ap = argparse.ArgumentParser(prog='chatool',
                                 description='다함께 차차차 통합 도구')
    sub = ap.add_subparsers(dest='cmd')

    for nm, fn in (('web', cmd_web), ('app', cmd_app)):
        p = sub.add_parser(nm)
        p.add_argument('--host', default='127.0.0.1')
        p.add_argument('--port', type=int, default=8099)
        p.add_argument('--no-open', action='store_true')
        p.set_defaults(func=fn)

    sub.add_parser('cars').set_defaults(func=cmd_cars)
    sub.add_parser('index').set_defaults(func=cmd_index)
    sub.add_parser('pack-exe').set_defaults(func=cmd_pack_exe)

    p = sub.add_parser('extract')
    p.add_argument('car')
    p.add_argument('-o', '--out')
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser('repaint')
    p.add_argument('car')
    p.add_argument('png')
    p.set_defaults(func=cmd_repaint)

    p = sub.add_parser('import')
    p.add_argument('obj')
    p.add_argument('--like', required=True, help='크기·자리를 맞출 기준 차')
    p.add_argument('--winding', choices=['keep', 'flip', 'auto'], default='keep',
                   help='앞면 방향. 주행에서 까맣게 나오면 flip')
    p.add_argument('--no-fit', action='store_true',
                   help='기준 차 크기에 맞추지 않고 원래 크기 그대로')
    p.set_defaults(func=cmd_import)

    p = sub.add_parser('newcar')
    p.add_argument('name', help='영문 이름')
    p.add_argument('--obj', required=True)
    p.add_argument('--png', required=True)
    p.add_argument('--label', help='게임에 보일 이름')
    p.add_argument('--class', dest='klass', default='S',
                   choices=['C', 'B', 'A', 'S'])
    p.add_argument('--gold', type=int, default=0)
    p.add_argument('--trophy', type=int, default=150)
    p.add_argument('--winding', choices=['keep', 'flip', 'auto'],
                   default='keep')
    p.add_argument('--no-fit', action='store_true')
    p.set_defaults(func=cmd_newcar)

    p = sub.add_parser('build')
    p.add_argument('--mode', choices=['server', 'local'], default='server')
    p.add_argument('--slot', help='APK 에 구워 넣을 세이브 이름')
    p.add_argument('--out', help='APK 파일 이름')
    p.add_argument('--install', action='store_true')
    p.set_defaults(func=cmd_build)

    args = ap.parse_args()
    if not getattr(args, 'func', None):
        # 그냥 실행하면 **앱 창**으로 뜹니다. 브라우저로 열려면 `web`.
        args = ap.parse_args(['app'])
        args.func = cmd_app
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main() or 0)
