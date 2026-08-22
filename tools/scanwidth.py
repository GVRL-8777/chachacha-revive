# -*- coding: utf-8 -*-
"""한글화로 문자열이 얼마나 넓어졌는지 전수 조사한다.

전제: 중국판 UI 는 **중국어 원문이 딱 맞게 들어가도록** 잡혀 있다.
따라서 같은 폰트로 잰 (한국어 폭 / 중국어 폭) 비율이 큰 항목이 UI 를 벗어날 후보다.
줄바꿈(\\n)이 있는 문자열은 **가장 긴 줄**을 기준으로 잰다.

폭은 실제 렌더에 쓰는 malgunbd.ttf 의 advance 합으로 계산한다(정확히 NGUI 와 같진
않지만 상대 비교에는 충분하다). NGUI 색상 태그 [RRGGBB]/[-] 는 표시되지 않으므로 제외한다.
"""
import io
import re
import sys

from fontTools.ttLib import TTFont
import chapaths

CN_TABLE = 'st_cn.txt'
KR_TABLE = 'st_merged_kr.txt'
FONT = chapaths.font()
CRLF, LF, CR = chr(13) + chr(10), chr(10), chr(13)
NLTOK = chr(92) + 'n'          # 표 안의 리터럴 \n
TAG = re.compile(r'\[[0-9A-Fa-f]{6}\]|\[-\]|\[b\]|\[/b\]|\[i\]|\[/i\]|\[u\]|\[/u\]|\[s\]|\[/s\]')


def load(path):
    raw = io.open(path, 'rb').read().decode('utf-8')
    raw = raw.replace(CRLF, LF).replace(CR, LF)
    d, order = {}, []
    for ln in raw.split(LF):
        if ' = ' not in ln:
            continue
        k, v = ln.split(' = ', 1)
        k = k.strip()
        if k not in d:
            order.append(k)
        d[k] = v
    return d, order


class Meter(object):
    """폰트 advance 로 문자열 폭을 잰다(1000 유닛/em 정규화)."""

    def __init__(self, path):
        f = TTFont(path, fontNumber=0, lazy=True)
        self.upm = f['head'].unitsPerEm
        cmap = {}
        for t in f['cmap'].tables:
            cmap.update(t.cmap)
        self.cmap = cmap
        self.hmtx = f['hmtx']
        self.cache = {}

    def adv(self, ch):
        c = self.cache.get(ch)
        if c is None:
            g = self.cmap.get(ord(ch))
            c = self.hmtx[g][0] / float(self.upm) if g else 0.0
            self.cache[ch] = c
        return c

    def width(self, s):
        """가장 긴 줄의 폭(em 단위)."""
        s = TAG.sub('', s or '')
        best = 0.0
        for line in s.replace(NLTOK, LF).split(LF):
            best = max(best, sum(self.adv(c) for c in line))
        return best


def main():
    cn, order = load(CN_TABLE)
    kr, _ = load(KR_TABLE)
    m = Meter(FONT)
    rows = []
    for k in order:
        cv, kv = cn.get(k), kr.get(k)
        if not cv or not kv or cv == kv:
            continue
        wc, wk = m.width(cv), m.width(kv)
        if wc <= 0:
            continue
        rows.append((wk / wc, wk - wc, k, cv, kv, wc, wk))
    rows.sort(reverse=True)
    print("비교 대상 %d개 (중국어와 값이 다른 항목)" % len(rows))
    over = [r for r in rows if r[0] >= 1.5]
    print("폭이 1.5배 이상 늘어난 항목: %d개" % len(over))
    print("폭이 2.0배 이상 늘어난 항목: %d개\n" % len([r for r in rows if r[0] >= 2.0]))
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    print("%-26s %6s %6s  %s" % ('키', '배율', '증가', '중국어 -> 한국어'))
    for ratio, delta, k, cv, kv, wc, wk in rows[:lim]:
        print("%-26s %5.2f배 %+6.1f  %s -> %s"
              % (k, ratio, delta, cv.replace(NLTOK, ' ')[:26], kv.replace(NLTOK, ' ')[:40]))
    io.open('width_report.txt', 'wb').write(
        ('\n'.join("%.3f\t%.2f\t%s\t%s\t%s" % (r[0], r[1], r[2],
                                               r[3].replace(NLTOK, ' '),
                                               r[4].replace(NLTOK, ' ')) for r in rows)
         ).encode('utf-8'))
    print("\n전체 목록 -> width_report.txt")


if __name__ == '__main__':
    main()
