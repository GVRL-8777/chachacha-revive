import io
p='mkkorean.py'
lines=io.open(p,encoding='utf-8').read().split('\n')
sep = chr(92)+'n'   # 문자열 리터럴 안의 개행 이스케이프
for i,l in enumerate(lines):
    if l.strip().startswith('text =') and 'join' in l:
        ind=l[:len(l)-len(l.lstrip())]
        lines[i] = (ind + "# 원본은 항목마다 빈 줄이 뒤따르는 형식이다(파서가 이를 전제로 한다).\n"
                    + ind + "text = ''.join('%s = %s" + sep + sep + "' % (k, merged[k]) for k in order)")
        print('수정 완료: %d행'%(i+1))
        break
io.open(p,'w',encoding='utf-8').write('\n'.join(lines))
