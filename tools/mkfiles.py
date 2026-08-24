# -*- coding: utf-8 -*-
"""`docs/FILES.md` — 저장소 파일 하나하나의 한 줄 설명 — 를 다시 만든다.

설명은 **파일 첫머리에서 긁어 옵니다.** 파이썬은 모듈 docstring, C#/셸은 맨 위
주석 덩이입니다. 그러니 설명을 고치고 싶으면 이 파일이 아니라 **그 파일의
첫머리**를 고치고 이것을 다시 돌리면 됩니다.

    python tools/mkfiles.py

새 파일을 넣었는데 어느 갈래에도 안 넣었다면 '갈래 없음' 으로 알려 줍니다.
"""
import ast
import io
import os
import re
import subprocess
import sys

CODE = os.path.dirname(os.path.abspath(__file__))
HERE = os.path.dirname(CODE)
OUT = os.path.join(HERE, 'docs', 'FILES.md')

# ── 갈래 ────────────────────────────────────────────────────────────────
# 이름순으로 늘어놓으면 fixatlas 옆에 fixext 가 오는데 둘은 아무 상관이 없다.
# 하는 일끼리 묶는다. research/ 는 정의상 잡동사니이므로 이름순으로 둔다.
GROUPS = {
    'tools': [
        ('이 폴더', 'README.md'),
        ('런처', """chatool.py chatool_page.py chatool_page_assets.py chatool_assets.py
            chabuild.py chasaves.py chahost.py chastate.py chaproj.py chalog.py
            chalang.py langkeys.py langcheck.py chapaths.py chapick.py
            chalauncher.py mkfiles.py"""),
        ('사설 서버', 'chacnserver.py mkskel.py'),
        ('APK 만들기', """pack.py buildapk.py setappname.py setpkg.py mkbundle.py
            mkpack.py packadd.py mapspec.py dump_systemtext.py"""),
        ('차 · 드라이버 · 자산', """chaassets.py chaanim.py chaanimglb.py newcar.py
            mktaegeuk.py carmesh.py addtaegeuk.py addhelly.py addtroy.py troyicon.py
            addcars5.py carsicon.py addvox5.py bundlechain.py
            cardb.py carprice.py trimcars.py chadrv.py drvprice.py drvfont.py
            chaskill.py voicefix.py voxout.py titlevoice.py"""),
        ('한글화', """mkkorean.py krmerge.py krtext.py krtitle.py korean_res.py
            bakedkr.py bakedcar.py bakedtext.py swapfont.py fitlabels.py
            scanwidth.py freetext.py report.py"""),
        ('UI 프리팹 손질', """activate.py atlasadd.py uiatlas.py hires.py fixatlas.py
            fixatlasref.py clonecard.py renamecard.py setsprite.py setsprname.py
            setpc.py movesprite.py moveobj.py expandarrays.py fixbuttons.py
            fixclip.py fixkeys.py fixlabels.py tradeui.py fixaqua.py"""),
        ('직렬화 파일 다루기', """sfparse.py sfedit.py sfx.py sfmerge.py sfmerge_new.py sfwrite.py
            sfwrite2.py sfwrite3.py sfwrite_replay.py setext.py fixext.py
            derename.py offset.py xdeps.py deps.py"""),
        ('그림 · 메시 · 셰이더', """progshader.py setshader.py texsettings.py
            uncompress.py meshuncompress.py dexegl.py"""),
        ('검사 · 조사', """audit.py checkbundle.py checkrefs.py conflicts.py
            sharedusage.py sharedone.py analyze.py vercmp.py scanaudio.py
            scansplit.py ildis.py ildump.py ilscan.py typemap.py mkreport.py"""),
    ],
    'patch': [
        ('이 폴더', 'README.md'),
        ('APK 에 들어가는 코드', 'ChaLocal.cs ChaLocalData.cs'),
        ('게임 DLL 패처', """localfix.cs patchcn.cs patch8.cs dbhook.cs tunnelfix.cs
            shopfix.cs titlefix.cs tradefix.cs rankfix.cs invitefix.cs modesfix.cs
            notutorial.cs pausefix.cs restore.cs strswap.cs chkrefs.cs"""),
        ('DLL 을 들여다보는 도구', """dump.cs alltype.cs cdump.cs tdump.cs lst.cs tn.cs
            tn2.cs fld.cs flddump.cs fldref.cs fieldinfo.cs sigdump.cs enums.cs
            enumdump.cs enumval.cs callsite.cs site3.cs s4.cs apidump.cs
            apischema.cs"""),
        ('C# 서버 쪽', 'Program.cs SchemaCollector.cs'),
        ('라이브러리', 'Mono.Cecil.dll'),
    ],
    'scripts': [
        ('이 폴더', 'README.md'),
        ('빌드', 'builddll.sh'),
        ('폰에서 돌려 보기', 'run.sh play.sh runlocal.sh relaunch.sh relaunch2.sh'),
        ('사진 찍기', """shot.sh race.sh racecheck.sh drv.sh drvshot.sh themesweep.sh
            tunnelsweep.sh tryfiles.sh drag.sh dragup.sh"""),
        ('조사', 'sweep.sh probe_cdn.sh'),
    ],
}

BLURB = {
    'tools': '런처 · 서버 · 빌드 도구. 서로 부르므로 한자리에 둡니다. '
             '**명령은 저장소 뿌리에서** 실행합니다.',
    'patch': 'C# 소스. Cecil 패처와, APK 안에 들어가는 코드입니다.',
    'scripts': '`adb` 로 폰을 부리는 잔심부름들. 뿌리에서 `sh scripts/이름.sh` 로 돌립니다.',
}

# 첫머리에서 긁을 수 없는 것들 (이진 파일, 자료 파일)
OVER = {
    '.gitignore': '**전부 막고 올릴 것만 여는** 방식의 무시 목록.',
    '.gitattributes': '줄 끝을 LF 로 통일합니다. 셸이 CRLF 로 받아 죽는 것을 막습니다.',
    'LICENSE': 'MIT. 다만 게임 자산의 권리는 넷마블 · CJ E&M 에 있습니다.',
    'README.md': '저장소 안내 — 무엇이 되었고, 어떤 APK 가 필요하고, 어떻게 만드는지.',
    'packspec.txt': '복원 번들에 담을 자산 목록(원본파일:이름:pathID:보정:평탄화).',
    'lang/en.json': '런처의 말 — 영어.',
    'lang/kr.json': '런처의 말 — 한국어.',
    'patch/Mono.Cecil.dll': 'Jb Evain 의 Mono.Cecil (MIT). '
                            '패처들이 .NET DLL 을 읽고 고치는 데 씁니다.',
    'docs/FILES.md': '이 문서. 파일 하나하나가 하는 일.',
}


def sentence(t):
    """앞머리 설명에서 **첫 문장 하나**만 뽑는다."""
    t = re.sub(r'\s+', ' ', (t or '').strip())
    if not t:
        return ''
    m = re.search(r'(니다\.|습니다\.|다\.|요\.|\.)(\s|$)', t)
    if m:
        t = t[:m.end(1)]
    return t.strip()


def head(path):
    """파일 첫머리의 설명을 한 문장으로."""
    try:
        s = io.open(path, encoding='utf-8', errors='replace').read()
    except Exception:
        return ''
    if path.endswith('.py'):
        try:
            d = ast.get_docstring(ast.parse(s))
            if d:
                return sentence(d)
        except Exception:
            pass
        buf = []
        for ln in s.splitlines()[:8]:
            ln = ln.strip()
            if ln.startswith('#') and 'coding' not in ln:
                buf.append(ln.lstrip('# '))
            elif buf:
                break
        return sentence(' '.join(buf))
    if path.endswith('.cs') or path.endswith('.sh'):
        buf = []
        for ln in s.splitlines()[:14]:
            ln = ln.strip()
            if ln.startswith('//'):
                buf.append(ln.lstrip('/ '))
            elif ln.startswith('#') and not ln.startswith('#!'):
                buf.append(ln.lstrip('# '))
            elif buf:
                break
        if buf:
            return sentence(' '.join(buf))
        m = re.search(r'<summary>(.*?)</summary>', s, re.S)
        if m:
            return sentence(m.group(1).replace('///', ' '))
    if path.endswith('.md'):
        for ln in s.splitlines():
            if ln.startswith('# '):
                return sentence(ln[2:])
    return ''


def tracked():
    out = subprocess.run(['git', 'ls-files'], cwd=HERE,
                         capture_output=True, text=True).stdout.split()
    return sorted(out)


# 폴더마다 제 소개. GitHub 는 폴더를 열면 그 안의 README.md 를 밑에 펼쳐 준다.
FOLDER = {
    'tools': ('런처 · 서버 · 빌드 도구',
              """이 게임을 되살리는 데 **실제로 쓰는** 프로그램들입니다. 세이브를 고치고,
APK 를 굽고, 자산을 뽑고 넣고, 사설 서버를 띄웁니다.

서로를 불러 쓰기 때문에 한 폴더에 함께 둡니다. **명령은 저장소 뿌리에서**
실행하세요. 도구들은 뿌리를 작업 폴더로 보고 `x77/` · `saves/` · `lang/` 을
찾습니다.

```
python tools/chatool.py          브라우저 런처 (여기서 거의 다 됩니다)
python tools/chapaths.py         원본 APK 가 어디 있는지 확인
```"""),
    'patch': ('게임 DLL 을 뜯어고치는 C# 소스',
              """게임의 `Assembly-CSharp.dll` 은 죽은 서버에 붙으려 하고, 중국 배포판은
여러 기능을 잠가 두었습니다. 여기 있는 프로그램들이 그 DLL 을 **Mono.Cecil 로
직접 고쳐** 서버 없이도 돌게 만듭니다.

세 갈래입니다.

- **APK 에 들어가는 코드** — `ChaLocal.cs` 는 게임 안에서 같이 도는 코드입니다.
  서버가 할 일을 폰 안에서 대신합니다.
- **패처** — 원본 DLL 을 읽어 호출 지점을 바꿔치기합니다.
- **들여다보는 도구** — 어느 메서드가 어디서 불리는지, 필드가 어떤 순서인지
  알아내는 작은 프로그램들. 패치를 만들기 전에 이것들로 먼저 봅니다."""),
    'scripts': ('폰을 부리는 잔심부름',
                """`adb` 로 폰에 APK 를 밀어 넣고, 게임을 띄우고, 화면을 찍습니다.
고칠 때마다 손으로 하기엔 번거로운 일들을 묶어 둔 것입니다.

뿌리에서 실행합니다.

```
sh scripts/runlocal.sh           로컬 APK 를 깔고 서버 없이 띄운다
sh scripts/race.sh 꼬리표 8       한 판 달리며 8장 찍는다
```

PC 서버가 필요한 스크립트는 주소를 환경변수로 받습니다.

```
export CHA_URL=http://192.168.0.100:8888
```"""),
    'research': ('한 번 쓰고 만 조사용 스크립트',
                 """게임 자산이 어떻게 생겼는지 알아내려고 **그때그때 만들어 쓴** 도구들입니다.
지금은 아무 데서도 부르지 않으니 안 쓰셔도 됩니다.

그래도 지우지 않고 둔 까닭은, 무엇을 어떻게 알아냈는지가 여기 남아 있기
때문입니다. 직렬화 파일의 바이트 배치, 배포판 사이의 자산 대응, 죽은 CDN 의
주소가 어디에 박혀 있었는지 — 같은 것을 다시 파려는 분에게는 이쪽이
완성된 도구보다 쓸모 있을 수 있습니다."""),
    'docs': ('연구 기록',
             """무엇이 어디까지 되었고, 어떻게 했는지 적어 둔 글들입니다.
코드를 읽기 전에 이쪽을 먼저 보시면 빠릅니다."""),
    'lang': ('런처의 말',
             """런처 화면에 뜨는 문구입니다. 한국어 원문이 곧 열쇠이고, 파일마다 그
번역을 담습니다.

새 언어를 넣으시려면 이 폴더에 `<코드>.json` 을 하나 더 두시면 됩니다.
런처가 알아서 목록에 띄웁니다.

```
python tools/langkeys.py            빠진 열쇠가 있는지 본다
python tools/langkeys.py --write    새 열쇠를 채워 넣는다
```"""),
}


def folder_readmes(files, desc):
    """폴더마다 README.md 를 써 준다. GitHub 가 폴더 화면에 펼쳐 준다."""
    made = []
    for folder, (title, blurb) in FOLDER.items():
        mine = [f for f in files if f.startswith(folder + '/')]
        if not mine:
            continue
        L = ['# `%s/` — %s' % (folder, title), '', blurb, '',
             '---', '', '## 담긴 파일 %d개' % len(mine), '']
        done = set()
        for gtitle, names in GROUPS.get(folder, []):
            rows = []
            for n in names.split():
                f = '%s/%s' % (folder, n)
                if f not in desc:
                    continue
                rows.append('| `%s` | %s |' % (n, desc[f]))
                done.add(f)
            if rows:
                L += ['### %s' % gtitle, '', '| 파일 | 하는 일 |', '|---|---|'] + rows + ['']
        rest = [f for f in mine if f not in done and not f.endswith('/README.md')]
        if rest:
            if done:
                L += ['### 그 밖', '']
            L += ['| 파일 | 하는 일 |', '|---|---|']
            L += ['| %s | %s |'
                  % (('[`%s`](%s)' % (f[len(folder) + 1:], f[len(folder) + 1:]))
                     if f.endswith('.md') else ('`%s`' % f[len(folder) + 1:]),
                     desc[f]) for f in rest]
            L += ['']
        L += ['---', '',
              '전체 목록은 [`docs/FILES.md`](../docs/FILES.md) 에 있습니다.']
        path = os.path.join(HERE, folder, 'README.md')
        io.open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
        made.append('%s/README.md' % folder)
    return made


def main():
    files = tracked()
    if not files:
        raise SystemExit('git 이 아무 파일도 알려 주지 않습니다 (저장소가 맞습니까?)')
    desc = {f: OVER.get(f) or head(os.path.join(HERE, f)) for f in files}

    blank = [f for f in files if not desc[f]]
    if blank:
        print('설명이 없는 파일 %d개 — 그 파일 첫머리에 한 줄 적어 주세요:' % len(blank))
        for f in blank:
            print('   %s' % f)

    L = ['# 파일 하나하나가 하는 일', '',
         '저장소에 든 %d개 파일의 한 줄 요약입니다. 같은 설명이 각 파일 첫머리에도'
         % len(files),
         '주석으로 붙어 있고, 이 문서는 거기서 긁어 만듭니다'
         ' (`python tools/mkfiles.py`).', '']
    used = set()

    for folder in ('tools', 'patch', 'scripts'):
        L += ['---', '', '## `%s/`' % folder, '', BLURB[folder], '']
        for title, names in GROUPS[folder]:
            rows = []
            for n in names.split():
                f = '%s/%s' % (folder, n)
                if f not in desc:
                    print('갈래에는 있는데 저장소에 없음: %s' % f)
                    continue
                rows.append('| `%s` | %s |' % (n, desc[f]))
                used.add(f)
            L += ['### %s' % title, '', '| 파일 | 하는 일 |', '|---|---|'] + rows + ['']
        stray = [f for f in files if f.startswith(folder + '/') and f not in used]
        if stray:
            print('갈래 없음 (%s/): %s' % (folder, ' '.join(os.path.basename(x)
                                                          for x in stray)))
            L += ['### 그 밖', '', '| 파일 | 하는 일 |', '|---|---|']
            L += ['| `%s` | %s |' % (os.path.basename(f), desc[f]) for f in stray] + ['']
            used |= set(stray)

    L += ['---', '', '## `research/`', '',
          '자산을 뜯어보며 **한 번 쓰고 만** 스크립트들입니다. 다른 데서 부르지 않으니',
          '안 쓰셔도 되고, 무엇을 어떻게 알아냈는지 궁금하실 때 보시면 됩니다.', '',
          '| 파일 | 하는 일 |', '|---|---|']
    for f in [x for x in files if x.startswith('research/')]:
        L.append('| `%s` | %s |' % (f[9:], desc[f]))
        used.add(f)

    L += ['', '---', '', '## `docs/`', '', '| 문서 | 무엇을 적었나 |', '|---|---|']
    for f in [x for x in files if x.startswith('docs/')]:
        L.append('| [`%s`](%s) | %s |' % (f[5:], f[5:], desc[f]))
        used.add(f)

    rest = [f for f in files if f not in used]
    L += ['', '---', '', '## 그 밖', '', '| 파일 | 하는 일 |', '|---|---|']
    L += ['| `%s` | %s |' % (f, desc[f]) for f in rest]

    io.open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    print('%s — 파일 %d개' % (os.path.relpath(OUT, HERE).replace('\\', '/'), len(files)))

    for m in folder_readmes(files, desc):
        print('%s' % m)
    return 0 if not blank else 1


if __name__ == '__main__':
    sys.exit(main())
