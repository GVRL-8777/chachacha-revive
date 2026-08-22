# -*- coding: utf-8 -*-
"""도로 텍스처 적용 직후, 씬의 모든 Renderer 와 그 재질/텍스처 유무를 한 번만 찍는다.
   어떤 배경 오브젝트가 텍스처 없이(=흰색으로) 렌더되는지 정확히 알기 위한 것."""
import io

p = 'dbhook.cs'
s = io.open(p, encoding='utf-8').read()

old = '''            if (debugLog != null)
            {
                tp.Append(Instruction.Create(OpCodes.Ldstr, "[CHATEX] 도로 텍스처 적용"));
                tp.Append(Instruction.Create(OpCodes.Call, debugLog));
            }'''

new = '''            if (debugLog != null)
            {
                tp.Append(Instruction.Create(OpCodes.Ldstr, "[CHATEX] 도로 텍스처 적용"));
                tp.Append(Instruction.Create(OpCodes.Call, debugLog));

                // 씬 전체 렌더러 인벤토리를 한 번만 찍는다.
                var uObjD2 = Def(unityEngine, "UnityEngine.Object");
                var findAll = Import(uObjD2.Methods.First(
                    m => m.Name == "FindObjectsOfType" && m.Parameters.Count == 1
                         && m.Parameters[0].ParameterType.FullName == "System.Type"));
                var nameM2 = Import(uObjD2.Methods.First(m => m.Name == "get_name"));
                var compGO = Import(Def(unityEngine, "UnityEngine.Component")
                                    .Methods.First(m => m.Name == "get_gameObject"));
                var matMain = Import(matT2.Methods.First(m => m.Name == "get_mainTexture"));
                var strD3 = Def(mscorlib, "System.String");
                var cc3 = Import(strD3.Methods.First(m => m.Name == "Concat"
                    && m.Parameters.Count == 2
                    && m.Parameters[0].ParameterType.FullName == "System.Object"
                    && m.Parameters[1].ParameterType.FullName == "System.Object"));
                var vAll = new VariableDefinition(new ArrayType(mod.ImportReference(uObjD2)));
                var vJ = new VariableDefinition(mod.TypeSystem.Int32);
                var vR2 = new VariableDefinition(mod.ImportReference(rendT4));
                var vM2 = new VariableDefinition(mod.ImportReference(matT2));
                tick.Body.Variables.Add(vAll); tick.Body.Variables.Add(vJ);
                tick.Body.Variables.Add(vR2); tick.Body.Variables.Add(vM2);

                tp.Append(Instruction.Create(OpCodes.Ldtoken, mod.ImportReference(rendT4)));
                tp.Append(Instruction.Create(OpCodes.Call, getTypeFromHandle));
                tp.Append(Instruction.Create(OpCodes.Call, findAll));
                tp.Append(Instruction.Create(OpCodes.Stloc, vAll));
                tp.Append(Instruction.Create(OpCodes.Ldc_I4_0));
                tp.Append(Instruction.Create(OpCodes.Stloc, vJ));
                var t2 = Instruction.Create(OpCodes.Ldloc, vJ);
                var b2 = Instruction.Create(OpCodes.Ldloc, vAll);
                tp.Append(Instruction.Create(OpCodes.Br, t2));
                tp.Append(b2);
                tp.Append(Instruction.Create(OpCodes.Ldloc, vJ));
                tp.Append(Instruction.Create(OpCodes.Ldelem_Ref));
                tp.Append(Instruction.Create(OpCodes.Castclass, mod.ImportReference(rendT4)));
                tp.Append(Instruction.Create(OpCodes.Stloc, vR2));
                tp.Append(Instruction.Create(OpCodes.Ldloc, vR2));
                tp.Append(Instruction.Create(OpCodes.Callvirt, getShared3));
                tp.Append(Instruction.Create(OpCodes.Stloc, vM2));
                // "[CHAINV] " + go.name
                tp.Append(Instruction.Create(OpCodes.Ldstr, "[CHAINV] "));
                tp.Append(Instruction.Create(OpCodes.Ldloc, vR2));
                tp.Append(Instruction.Create(OpCodes.Callvirt, compGO));
                tp.Append(Instruction.Create(OpCodes.Callvirt, nameM2));
                tp.Append(Instruction.Create(OpCodes.Call, cc3));
                // + " | " + material
                tp.Append(Instruction.Create(OpCodes.Ldstr, " | "));
                tp.Append(Instruction.Create(OpCodes.Call, cc3));
                tp.Append(Instruction.Create(OpCodes.Ldloc, vM2));
                tp.Append(Instruction.Create(OpCodes.Call, cc3));
                // + " | tex=" + mainTexture   (재질이 null 이면 건너뛴다)
                var noMat = Instruction.Create(OpCodes.Nop);
                var afterTex = Instruction.Create(OpCodes.Nop);
                tp.Append(Instruction.Create(OpCodes.Ldstr, " | tex="));
                tp.Append(Instruction.Create(OpCodes.Call, cc3));
                tp.Append(Instruction.Create(OpCodes.Ldloc, vM2));
                tp.Append(Instruction.Create(OpCodes.Brfalse, noMat));
                tp.Append(Instruction.Create(OpCodes.Ldloc, vM2));
                tp.Append(Instruction.Create(OpCodes.Callvirt, matMain));
                tp.Append(Instruction.Create(OpCodes.Call, cc3));
                tp.Append(Instruction.Create(OpCodes.Br, afterTex));
                tp.Append(noMat);
                tp.Append(Instruction.Create(OpCodes.Ldstr, "(재질없음)"));
                tp.Append(Instruction.Create(OpCodes.Call, cc3));
                tp.Append(afterTex);
                tp.Append(Instruction.Create(OpCodes.Call, debugLog));
                tp.Append(Instruction.Create(OpCodes.Ldloc, vJ));
                tp.Append(Instruction.Create(OpCodes.Ldc_I4_1));
                tp.Append(Instruction.Create(OpCodes.Add));
                tp.Append(Instruction.Create(OpCodes.Stloc, vJ));
                tp.Append(t2);
                tp.Append(Instruction.Create(OpCodes.Ldloc, vAll));
                tp.Append(Instruction.Create(OpCodes.Ldlen));
                tp.Append(Instruction.Create(OpCodes.Conv_I4));
                tp.Append(Instruction.Create(OpCodes.Blt, b2));
            }'''

assert old in s
s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8').write(s)
print('dbhook.cs 렌더러 인벤토리 패치 완료')
