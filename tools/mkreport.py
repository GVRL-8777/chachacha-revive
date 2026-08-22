# -*- coding: utf-8 -*-
"""조사 결과를 훑어보기 좋은 HTML 문서로 만든다."""
import io, json, html
from scanwidth import Meter, load, NLTOK

cn,_ = load('st_cn.txt'); kr,_ = load('st_merged_kr.txt')
m = Meter('C:/Windows/Fonts/malgunbd.ttf')
rows = json.load(io.open('labels.json', encoding='utf-8'))

wide, tall, seen = [], [], set()
for r in rows:
    k = r['key']
    if not k or k not in cn or k not in kr or cn[k] == kr[k]:
        continue
    wc, wk = m.width(cn[k]), m.width(kr[k])
    if wc <= 0: continue
    sig = (k, r['go'])
    if sig in seen: continue
    seen.add(sig)
    rec = dict(key=k, go=r['go'], f=r['file'][:8], size=r['size'], wrap=r['wrap'],
               ratio=wk/wc, grow=wk-wc, cn=cn[k].replace(NLTOK,' '), kr=kr[k].replace(NLTOK,' '))
    if r['wrap'] == 0:
        wide.append(rec)
    else:
        lc, lk = len(cn[k].split(NLTOK)), len(kr[k].split(NLTOK))
        if wk/wc > 1.3 or lk > lc: tall.append(rec)
wide.sort(key=lambda x: -x['grow']); tall.sort(key=lambda x: -x['ratio'])
baked = [r for r in rows if not r['key'] and any('\u4e00'<=c<='\u9fff' for c in r['text'])]
baked.sort(key=lambda r: (r['file'], r['go']))

def sev(r):
    if r['grow'] >= 12 or r['ratio'] >= 4: return 'crit','심각'
    if r['grow'] >= 5 or r['ratio'] >= 2: return 'warn','주의'
    return 'mild','경미'

e = html.escape
def bar(ratio):
    pct = min(100, (ratio-1)/4*100)
    return '<span class="bar"><i style="width:%.0f%%"></i></span>' % pct

def table(items, cols):
    out = ['<div class="scroll"><table><thead><tr>']
    out += ['<th%s>%s</th>' % (c[2], c[0]) for c in cols]
    out.append('</tr></thead><tbody>')
    for r in items:
        s, label = sev(r)
        out.append('<tr class="%s">' % s)
        for c in cols: out.append(c[1](r, s, label))
        out.append('</tr>')
    out.append('</tbody></table></div>')
    return ''.join(out)

COLS = [
 ('심각도', lambda r,s,l: '<td><span class="chip %s">%s</span></td>'%(s,l), ''),
 ('문자열 키', lambda r,s,l: '<td class="mono">%s</td>'%e(r['key']), ''),
 ('오브젝트', lambda r,s,l: '<td class="mono dim">%s</td>'%e(r['go']), ''),
 ('글자<br>크기', lambda r,s,l: '<td class="num">%g</td>'%r['size'], ' class="num"'),
 ('늘어난 폭', lambda r,s,l: '<td class="num">%s %.1f배</td>'%(bar(r['ratio']),r['ratio']), ' class="num"'),
 ('중국어 원문', lambda r,s,l: '<td class="dim">%s</td>'%e(r['cn'][:28]), ''),
 ('한국어', lambda r,s,l: '<td>%s</td>'%e(r['kr'][:46]), ''),
]
BCOLS = [
 ('자산 파일', lambda r,s,l: '<td class="mono dim">%s…</td>'%e(r['file'][:8]), ''),
 ('오브젝트', lambda r,s,l: '<td class="mono">%s</td>'%e(r['go']), ''),
 ('글자<br>크기', lambda r,s,l: '<td class="num">%g</td>'%r['size'], ' class="num"'),
 ('박혀 있는 중국어', lambda r,s,l: '<td>%s</td>'%e(r['text'].replace('\n',' ')[:60]), ''),
]

tpl = io.open('report_tpl.html', encoding='utf-8').read()
io.open('kr_report.html','w',encoding='utf-8').write(tpl
  .replace('{{TOTAL}}', str(len(rows)))
  .replace('{{KEYED}}', str(len([r for r in rows if r['key']])))
  .replace('{{WIDE}}', str(len(wide)))
  .replace('{{TALL}}', str(len(tall)))
  .replace('{{BAKED}}', str(len(baked)))
  .replace('{{T_WIDE}}', table(wide, COLS))
  .replace('{{T_TALL}}', table(tall, COLS))
  .replace('{{T_BAKED}}', table(baked, BCOLS)))
print('가로넘침 %d / 세로늘어남 %d / 박힌중국어 %d -> kr_report.html'%(len(wide),len(tall),len(baked)))
