# -*- coding: utf-8 -*-
"""복사 루프를 new[i+1] = old[i] 로 고친다.

앞선 시도는 루프 첫 줄이 `ap2.Append(body);` 라는 걸 놓쳐 패치가 안 걸렸고,
그 결과 새 테마가 old[0] 을 덮어써서 배열 끝이 null 로 남아 예외가 쏟아졌다.
"""
import io

p = 'patchcn.cs'
lines = io.open(p, encoding='utf-8').read().split('\n')
out = []
i = 0
changed = 0
while i < len(lines):
    ln = lines[i]
    st = ln.strip()
    if (st == 'ap2.Append(body);'
            and i + 2 < len(lines)
            and lines[i + 1].strip() == 'ap2.Append(Instruction.Create(OpCodes.Ldloc, vI));'
            and lines[i + 2].strip() == 'ap2.Append(Instruction.Create(OpCodes.Ldloc, vOld));'
            and 'Ldc_I4_1' not in lines[i + 2]):
        indent = ln[:len(ln) - len(ln.lstrip())]
        out.append(ln)
        out.append(lines[i + 1])
        out.append(indent + 'ap2.Append(Instruction.Create(OpCodes.Ldc_I4_1));')
        out.append(indent + 'ap2.Append(Instruction.Create(OpCodes.Add));   // new[i+1] = old[i]')
        i += 2
        changed += 1
        continue
    out.append(ln)
    i += 1

io.open(p, 'w', encoding='utf-8').write('\n'.join(out))
print('복사 루프 수정 %d곳' % changed)
