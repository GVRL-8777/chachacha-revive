# -*- coding: utf-8 -*-
"""텍스처를 정적 캐시에 담고, Background 가 새로 만들어질 때마다 재적용하도록 고친다.
   (기존엔 한 번 붙이면 상태가 2로 굳어 두 번째 레이스부터 다시 흰 화면이 됐다)"""
import io

p = 'dbhook.cs'
s = io.open(p, encoding='utf-8').read()

# 1) 텍스처 캐시 필드 추가
old = '''            var fState = new FieldDefinition("__chaTexState",
                FieldAttributes.Public | FieldAttributes.Static, mod.TypeSystem.Int32);
            abm.Fields.Add(fWww); abm.Fields.Add(fState);'''
new = '''            var fState = new FieldDefinition("__chaTexState",
                FieldAttributes.Public | FieldAttributes.Static, mod.TypeSystem.Int32);
            // 내려받은 텍스처는 캐시해 둔다. 레이스를 다시 시작하면 Background 가 새로 만들어지므로
            // 상태만 0 으로 되돌리고 캐시된 텍스처를 그대로 다시 붙인다(재다운로드 없음).
            var fTex = new FieldDefinition("__chaTex",
                FieldAttributes.Public | FieldAttributes.Static,
                mod.ImportReference(Def(unityEngine, "UnityEngine.Texture2D")));
            abm.Fields.Add(fWww); abm.Fields.Add(fState); abm.Fields.Add(fTex);'''
assert old in s
s = s.replace(old, new, 1)

# 2) tick 앞부분: 캐시가 있으면 곧바로 적용 단계로
old2 = '''            tp.Append(Instruction.Create(OpCodes.Ldsfld, fState));
            tp.Append(Instruction.Create(OpCodes.Ldc_I4_2));
            tp.Append(Instruction.Create(OpCodes.Beq, stop));
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fState));
            tp.Append(Instruction.Create(OpCodes.Brtrue, poll));'''
new2 = '''            var apply = Instruction.Create(OpCodes.Nop);
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fState));
            tp.Append(Instruction.Create(OpCodes.Ldc_I4_2));
            tp.Append(Instruction.Create(OpCodes.Beq, stop));
            // 캐시된 텍스처가 있으면 다운로드를 건너뛰고 바로 적용한다.
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fTex));
            tp.Append(Instruction.Create(OpCodes.Brtrue, apply));
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fState));
            tp.Append(Instruction.Create(OpCodes.Brtrue, poll));'''
assert old2 in s
s = s.replace(old2, new2, 1)

# 3) 다운로드 성공 시 캐시에 저장하고, 적용 라벨을 붙인다
old3 = '''            tp.Append(Instruction.Create(OpCodes.Stloc, vTex));
            tp.Append(Instruction.Create(OpCodes.Ldloc, vTex));
            tp.Append(Instruction.Create(OpCodes.Brfalse, stop));
            tp.Append(Instruction.Create(OpCodes.Ldarg_0));'''
new3 = '''            tp.Append(Instruction.Create(OpCodes.Stloc, vTex));
            tp.Append(Instruction.Create(OpCodes.Ldloc, vTex));
            tp.Append(Instruction.Create(OpCodes.Brfalse, stop));
            tp.Append(Instruction.Create(OpCodes.Ldloc, vTex));
            tp.Append(Instruction.Create(OpCodes.Stsfld, fTex));
            tp.Append(apply);
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fTex));
            tp.Append(Instruction.Create(OpCodes.Stloc, vTex));
            tp.Append(Instruction.Create(OpCodes.Ldarg_0));'''
assert old3 in s
s = s.replace(old3, new3, 1)

# 4) __ChaBackground 끝에서 상태를 0 으로 되돌린다 (씬마다 재적용)
old4 = '''            if (debugLog != null)
            {
                bp3.Append(Instruction.Create(OpCodes.Ldstr, "[CHABG] Background 루트 조립"));
                bp3.Append(Instruction.Create(OpCodes.Call, debugLog));
            }'''
new4 = '''            bgResetHook = bp3;      // 아래에서 __chaTexState = 0 을 덧붙인다
            if (debugLog != null)
            {
                bp3.Append(Instruction.Create(OpCodes.Ldstr, "[CHABG] Background 루트 조립"));
                bp3.Append(Instruction.Create(OpCodes.Call, debugLog));
            }'''
assert old4 in s
s = s.replace(old4, new4, 1)

# bgResetHook 선언
s = s.replace('        MethodDefinition chaBg = null;',
              '        MethodDefinition chaBg = null;\n'
              '        ILProcessor bgResetHook = null;', 1)

# 텍스처 블록 끝에서 상태 리셋 삽입
old5 = '''            // Background::Update 진입부에 삽입 (진입부 삽입 = 안전한 패턴)'''
new5 = '''            // Background 가 새로 조립될 때마다 상태를 0 으로 되돌려 텍스처를 다시 붙인다.
            if (bgResetHook != null)
            {
                bgResetHook.Append(Instruction.Create(OpCodes.Ldc_I4_0));
                bgResetHook.Append(Instruction.Create(OpCodes.Stsfld, fState));
            }

            // Background::Update 진입부에 삽입 (진입부 삽입 = 안전한 패턴)'''
assert old5 in s
s = s.replace(old5, new5, 1)

io.open(p, 'w', encoding='utf-8').write(s)
print('dbhook.cs 텍스처 캐시 패치 완료')
