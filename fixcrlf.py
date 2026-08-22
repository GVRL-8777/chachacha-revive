import io
p='mkkorean.py'
lines=io.open(p,encoding='utf-8').read().split('\n')
CR = chr(92)+'r'
LF = chr(92)+'n'
for i,l in enumerate(lines):
    if l.strip().startswith('text =') and 'join' in l:
        ind=l[:len(l)-len(l.lstrip())]
        lines[i] = (ind + "# 원본은 항목마다 **CRLF 하나**로 끝난다.\n"
                    + ind + "# (LF 기준으로 세면 빈 줄이 있는 것처럼 보이지만 착시다 —\n"
                    + ind + "#  CRLF 를 두 번 넣으면 파서가 표를 통째로 못 읽는다)\n"
                    + ind + "text = ''.join('%s = %s" + CR + LF + "' % (k, merged[k]) for k in order)")
        print('CRLF 형식으로 수정: %d행'%(i+1))
        break
io.open(p,'w',encoding='utf-8').write('\n'.join(lines))
