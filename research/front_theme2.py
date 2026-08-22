# -*- coding: utf-8 -*-
"""추가 테마를 배열 맨 앞(index 0)에 놓는다 — 들여쓰기에 무관하게 줄 단위로 처리."""
import io

p = 'patchcn.cs'
lines = io.open(p, encoding='utf-8').read().split('\n')
out = []
i = 0
changed = 0
while i < len(lines):
    ln = lines[i]
    st = ln.strip()

    # 1) 복사 루프에서 new[i] -> new[i+1]
    #    패턴: Ldloc, vNew / Ldloc, vI / Ldloc, vOld
    if (st == 'ap2.Append(Instruction.Create(OpCodes.Ldloc, vNew));'
            and i + 2 < len(lines)
            and lines[i + 1].strip() == 'ap2.Append(Instruction.Create(OpCodes.Ldloc, vI));'
            and lines[i + 2].strip() == 'ap2.Append(Instruction.Create(OpCodes.Ldloc, vOld));'):
        indent = ln[:len(ln) - len(ln.lstrip())]
        out.append(ln)
        out.append(lines[i + 1])
        out.append(indent + 'ap2.Append(Instruction.Create(OpCodes.Ldc_I4_1));')
        out.append(indent + 'ap2.Append(Instruction.Create(OpCodes.Add));   // new[i+1] = old[i]')
        i += 2
        changed += 1
        continue

    # 2) 새 테마를 vN 이 아니라 0 번에 넣는다
    if (st == 'ap2.Append(Instruction.Create(OpCodes.Ldloc, vN));'
            and i + 1 < len(lines)
            and lines[i + 1].strip() == 'ap2.Append(Instruction.Create(OpCodes.Newobj, mtdCtor));'):
        indent = ln[:len(ln) - len(ln.lstrip())]
        out.append(indent + 'ap2.Append(Instruction.Create(OpCodes.Ldc_I4_0));  // 맨 앞에 넣는다')
        changed += 1
        i += 1
        continue

    out.append(ln)
    i += 1

io.open(p, 'w', encoding='utf-8').write('\n'.join(out))
print('수정 %d곳' % changed)
