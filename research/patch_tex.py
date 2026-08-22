# -*- coding: utf-8 -*-
"""dbhook.cs 에 '도로 텍스처를 WWW 로 받아 원본 재질에 붙이는' 패치를 추가한다."""
import io
import os

# 폰이 PC 를 어느 주소로 부를지. 랜이면 PC 의 랜 주소를 적어 주면 된다.
#     export CHA_URL=http://192.168.0.100:8888
TEX_URL = os.environ.get('CHA_URL', 'http://127.0.0.1:8888').rstrip('/') + '/tex/'

p = 'dbhook.cs'
s = io.open(p, encoding='utf-8').read()

# 1) 텍스처 URL 인자 추가
old_arg = 'string cutAfter = args.Length > 6 ? args[6] : "mCollider";'
new_arg = (old_arg + '\n'
           '        string texUrl = args.Length > 7 ? args[7] '
           ': "%s";' % TEX_URL)
if 'texUrl' not in s:
    assert old_arg in s
    s = s.replace(old_arg, new_arg, 1)

# 2) __ChaFixMat 호출 제거 (재질 교체 대신 원본 재질에 텍스처를 붙인다)
call_block = ('                if (chaMat != null)\n'
              '                {\n'
              '                    ins_(Instruction.Create(OpCodes.Ldarg_0));\n'
              '                    ins_(Instruction.Create(OpCodes.Ldfld, curFld));\n'
              '                    ins_(Instruction.Create(OpCodes.Call, chaMat));\n'
              '                }\n')
s = s.replace(call_block, '')

# 3) WWW 기반 텍스처 주입 코드 삽입
anchor = '        // ---- 맵 재질 보정 헬퍼 ----'
add = r'''        // ---- 도로 텍스처 주입 (WWW -> 원본 재질의 mainTexture) ----
        // 7.7.0 은 "…CompleteMap" 재질 껍데기만 남고 텍스처는 죽은 CDN 번들에 있다.
        // UnityEngine.dll 이 바이트코드 스트리핑돼 Texture2D 는 메서드가 0개(LoadImage 없음)지만
        // **WWW.texture 는 살아 있어서** 서버가 내려준 PNG 를 네이티브로 디코드할 수 있다.
        // PNG 는 구버전 8.apk 에서 뽑아낸 원본 아틀라스다.
        if (bgType != null)
        {
            var wwwT = Def(unityEngine, "UnityEngine.WWW");
            var wwwCtor = Import(wwwT.Methods.First(m => m.IsConstructor && m.Parameters.Count == 1
                                 && m.Parameters[0].ParameterType.FullName == "System.String"));
            var wwwDone = Import(wwwT.Methods.First(m => m.Name == "get_isDone"));
            var wwwTex = Import(wwwT.Methods.First(m => m.Name == "get_texture"));
            var matT2 = Def(unityEngine, "UnityEngine.Material");
            var setMainTex = Import(matT2.Methods.First(m => m.Name == "set_mainTexture"));
            var rendT4 = Def(unityEngine, "UnityEngine.Renderer");
            var getShared3 = Import(rendT4.Methods.First(m => m.Name == "get_sharedMaterial"));
            var goT3 = Def(unityEngine, "UnityEngine.GameObject");
            var getCIC2 = Import(goT3.Methods.First(
                m => m.Name == "GetComponentsInChildren" && m.Parameters.Count == 1
                     && m.Parameters[0].ParameterType.FullName == "System.Type"));
            var mapAttFld = bgType.Fields.First(f => f.Name == "mapAttachedObject");

            var fWww = new FieldDefinition("__chaWww",
                FieldAttributes.Public | FieldAttributes.Static, mod.ImportReference(wwwT));
            var fState = new FieldDefinition("__chaTexState",
                FieldAttributes.Public | FieldAttributes.Static, mod.TypeSystem.Int32);
            abm.Fields.Add(fWww); abm.Fields.Add(fState);

            var tick = new MethodDefinition("__ChaTexTick",
                MethodAttributes.Public | MethodAttributes.Static | MethodAttributes.HideBySig,
                mod.TypeSystem.Void);
            tick.Parameters.Add(new ParameterDefinition("bg", ParameterAttributes.None,
                                                        (TypeReference)bgType));
            tick.Body.InitLocals = true;
            var vTex = new VariableDefinition(mod.ImportReference(
                Def(unityEngine, "UnityEngine.Texture2D")));
            var vMap = new VariableDefinition(mod.ImportReference(goT3));
            var vArr = new VariableDefinition(new ArrayType(mod.ImportReference(
                Def(unityEngine, "UnityEngine.Component"))));
            var vIdx = new VariableDefinition(mod.TypeSystem.Int32);
            var vM = new VariableDefinition(mod.ImportReference(matT2));
            tick.Body.Variables.Add(vTex); tick.Body.Variables.Add(vMap);
            tick.Body.Variables.Add(vArr); tick.Body.Variables.Add(vIdx);
            tick.Body.Variables.Add(vM);
            var tp = tick.Body.GetILProcessor();
            var stop = Instruction.Create(OpCodes.Ret);
            var poll = Instruction.Create(OpCodes.Nop);

            tp.Append(Instruction.Create(OpCodes.Ldsfld, fState));
            tp.Append(Instruction.Create(OpCodes.Ldc_I4_2));
            tp.Append(Instruction.Create(OpCodes.Beq, stop));
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fState));
            tp.Append(Instruction.Create(OpCodes.Brtrue, poll));
            tp.Append(Instruction.Create(OpCodes.Ldstr, texUrl + "field01CompleteMap.png"));
            tp.Append(Instruction.Create(OpCodes.Newobj, wwwCtor));
            tp.Append(Instruction.Create(OpCodes.Stsfld, fWww));
            tp.Append(Instruction.Create(OpCodes.Ldc_I4_1));
            tp.Append(Instruction.Create(OpCodes.Stsfld, fState));
            tp.Append(Instruction.Create(OpCodes.Br, stop));
            tp.Append(poll);
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fWww));
            tp.Append(Instruction.Create(OpCodes.Callvirt, wwwDone));
            tp.Append(Instruction.Create(OpCodes.Brfalse, stop));
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fWww));
            tp.Append(Instruction.Create(OpCodes.Callvirt, wwwTex));
            tp.Append(Instruction.Create(OpCodes.Stloc, vTex));
            tp.Append(Instruction.Create(OpCodes.Ldloc, vTex));
            tp.Append(Instruction.Create(OpCodes.Brfalse, stop));
            tp.Append(Instruction.Create(OpCodes.Ldarg_0));
            tp.Append(Instruction.Create(OpCodes.Ldfld, mapAttFld));
            tp.Append(Instruction.Create(OpCodes.Stloc, vMap));
            tp.Append(Instruction.Create(OpCodes.Ldloc, vMap));
            tp.Append(Instruction.Create(OpCodes.Brfalse, stop));
            tp.Append(Instruction.Create(OpCodes.Ldloc, vMap));
            tp.Append(Instruction.Create(OpCodes.Ldtoken, mod.ImportReference(rendT4)));
            tp.Append(Instruction.Create(OpCodes.Call, getTypeFromHandle));
            tp.Append(Instruction.Create(OpCodes.Callvirt, getCIC2));
            tp.Append(Instruction.Create(OpCodes.Stloc, vArr));
            tp.Append(Instruction.Create(OpCodes.Ldloc, vArr));
            tp.Append(Instruction.Create(OpCodes.Ldlen));
            tp.Append(Instruction.Create(OpCodes.Conv_I4));
            tp.Append(Instruction.Create(OpCodes.Brfalse, stop));
            tp.Append(Instruction.Create(OpCodes.Ldc_I4_0));
            tp.Append(Instruction.Create(OpCodes.Stloc, vIdx));
            var test = Instruction.Create(OpCodes.Ldloc, vIdx);
            var body = Instruction.Create(OpCodes.Ldloc, vArr);
            tp.Append(Instruction.Create(OpCodes.Br, test));
            tp.Append(body);
            tp.Append(Instruction.Create(OpCodes.Ldloc, vIdx));
            tp.Append(Instruction.Create(OpCodes.Ldelem_Ref));
            tp.Append(Instruction.Create(OpCodes.Castclass, mod.ImportReference(rendT4)));
            tp.Append(Instruction.Create(OpCodes.Callvirt, getShared3));
            tp.Append(Instruction.Create(OpCodes.Stloc, vM));
            var skipOne = Instruction.Create(OpCodes.Nop);
            tp.Append(Instruction.Create(OpCodes.Ldloc, vM));
            tp.Append(Instruction.Create(OpCodes.Brfalse, skipOne));
            tp.Append(Instruction.Create(OpCodes.Ldloc, vM));
            tp.Append(Instruction.Create(OpCodes.Ldloc, vTex));
            tp.Append(Instruction.Create(OpCodes.Callvirt, setMainTex));
            tp.Append(skipOne);
            tp.Append(Instruction.Create(OpCodes.Ldloc, vIdx));
            tp.Append(Instruction.Create(OpCodes.Ldc_I4_1));
            tp.Append(Instruction.Create(OpCodes.Add));
            tp.Append(Instruction.Create(OpCodes.Stloc, vIdx));
            tp.Append(test);
            tp.Append(Instruction.Create(OpCodes.Ldloc, vArr));
            tp.Append(Instruction.Create(OpCodes.Ldlen));
            tp.Append(Instruction.Create(OpCodes.Conv_I4));
            tp.Append(Instruction.Create(OpCodes.Blt, body));
            tp.Append(Instruction.Create(OpCodes.Ldc_I4_2));
            tp.Append(Instruction.Create(OpCodes.Stsfld, fState));
            if (debugLog != null)
            {
                tp.Append(Instruction.Create(OpCodes.Ldstr, "[CHATEX] 도로 텍스처 적용"));
                tp.Append(Instruction.Create(OpCodes.Call, debugLog));
            }
            tp.Append(stop);
            abm.Methods.Add(tick);

            // Background::Update 진입부에 삽입 (진입부 삽입 = 안전한 패턴)
            var upd = bgType.Methods.FirstOrDefault(m => m.Name == "Update");
            if (upd != null && upd.HasBody)
            {
                var first = upd.Body.Instructions[0];
                var up = upd.Body.GetILProcessor();
                up.InsertBefore(first, Instruction.Create(OpCodes.Ldarg_0));
                up.InsertBefore(first, Instruction.Create(OpCodes.Call, tick));
                Console.WriteLine("  Background::Update 진입부 -> __ChaTexTick (도로 텍스처 수신)");
            }
        }

'''

assert anchor in s
s = s.replace(anchor, add + anchor, 1)
io.open(p, 'w', encoding='utf-8').write(s)
print('dbhook.cs 패치 완료')
