# -*- coding: utf-8 -*-
"""새 맵 테마를 로테이션에 **추가**하는 배선을 patchcn.cs 에 넣는다.

  1. `Background::Start` 진입부에서 `mapThemeOrder` 배열을 한 칸 늘리고
     새 테마(themeName="gbeach")를 채운다. 기존 테마는 그대로 남는다 = 추가.
  2. `ResourceByOption::Load(string)` 진입부에서 "Background/gbeach01" 요청을
     번들에서 꺼낸 GameObject 로 가로챈다. 그 외 요청은 원래대로 흘려보낸다.
     (SetMapResources 는 null 을 받아야 루프를 끝내므로 gbeach02 는 자연히 null 이 된다)
"""
import io

p = 'patchcn.cs'
s = io.open(p, encoding='utf-8').read()

anchor = '        // 360/NetmarbleS 플러그인은 이 환경에 존재하지 않는다.'
add = '''        // ---- 새 맵 테마 추가 배선 ----
        {
            var bgT = mod.Types.First(t => t.Name == "Background");
            var mtd = bgT.NestedTypes.First(t => t.Name == "MapThemeData");
            var fOrder = bgT.Fields.First(f => f.Name == "mapThemeOrder");
            var fTheme = mtd.Fields.First(f => f.Name == "themeName");
            var fLoop = mtd.Fields.First(f => f.Name == "loopCount");
            var fRes = mtd.Fields.First(f => f.Name == "mapRes");
            var mtdCtor = mtd.Methods.First(m => m.IsConstructor && m.Parameters.Count == 0);
            var alType = corlib.Types.First(t => t.FullName == "System.Collections.ArrayList");
            var alCtor = mod.ImportReference(alType.Methods.First(
                m => m.IsConstructor && m.Parameters.Count == 0));
            var mtdArr = new ArrayType((TypeReference)mtd);

            // --- __ChaAddTheme(Background bg) ---
            var addTheme = new MethodDefinition("__ChaAddTheme",
                MethodAttributes.Public | MethodAttributes.Static | MethodAttributes.HideBySig,
                mod.TypeSystem.Void);
            addTheme.Parameters.Add(new ParameterDefinition("bg", ParameterAttributes.None,
                                                            (TypeReference)bgT));
            addTheme.Body.InitLocals = true;
            var vOld = new VariableDefinition(mtdArr);
            var vNew = new VariableDefinition(mtdArr);
            var vI = new VariableDefinition(mod.TypeSystem.Int32);
            var vN = new VariableDefinition(mod.TypeSystem.Int32);
            addTheme.Body.Variables.Add(vOld); addTheme.Body.Variables.Add(vNew);
            addTheme.Body.Variables.Add(vI); addTheme.Body.Variables.Add(vN);
            var ap2 = addTheme.Body.GetILProcessor();
            var done = Instruction.Create(OpCodes.Ret);

            ap2.Append(Instruction.Create(OpCodes.Ldarg_0));
            ap2.Append(Instruction.Create(OpCodes.Ldfld, fOrder));
            ap2.Append(Instruction.Create(OpCodes.Stloc, vOld));
            ap2.Append(Instruction.Create(OpCodes.Ldloc, vOld));
            ap2.Append(Instruction.Create(OpCodes.Brfalse, done));   // 배열이 없으면 손대지 않는다
            ap2.Append(Instruction.Create(OpCodes.Ldloc, vOld));
            ap2.Append(Instruction.Create(OpCodes.Ldlen));
            ap2.Append(Instruction.Create(OpCodes.Conv_I4));
            ap2.Append(Instruction.Create(OpCodes.Stloc, vN));
            ap2.Append(Instruction.Create(OpCodes.Ldloc, vN));
            ap2.Append(Instruction.Create(OpCodes.Ldc_I4_1));
            ap2.Append(Instruction.Create(OpCodes.Add));
            ap2.Append(Instruction.Create(OpCodes.Newarr, (TypeReference)mtd));
            ap2.Append(Instruction.Create(OpCodes.Stloc, vNew));
            // 기존 항목 복사
            ap2.Append(Instruction.Create(OpCodes.Ldc_I4_0));
            ap2.Append(Instruction.Create(OpCodes.Stloc, vI));
            var test = Instruction.Create(OpCodes.Ldloc, vI);
            var body = Instruction.Create(OpCodes.Ldloc, vNew);
            ap2.Append(Instruction.Create(OpCodes.Br, test));
            ap2.Append(body);
            ap2.Append(Instruction.Create(OpCodes.Ldloc, vI));
            ap2.Append(Instruction.Create(OpCodes.Ldloc, vOld));
            ap2.Append(Instruction.Create(OpCodes.Ldloc, vI));
            ap2.Append(Instruction.Create(OpCodes.Ldelem_Ref));
            ap2.Append(Instruction.Create(OpCodes.Stelem_Ref));
            ap2.Append(Instruction.Create(OpCodes.Ldloc, vI));
            ap2.Append(Instruction.Create(OpCodes.Ldc_I4_1));
            ap2.Append(Instruction.Create(OpCodes.Add));
            ap2.Append(Instruction.Create(OpCodes.Stloc, vI));
            ap2.Append(test);
            ap2.Append(Instruction.Create(OpCodes.Ldloc, vN));
            ap2.Append(Instruction.Create(OpCodes.Blt, body));
            // 새 테마 채우기
            ap2.Append(Instruction.Create(OpCodes.Ldloc, vNew));
            ap2.Append(Instruction.Create(OpCodes.Ldloc, vN));
            ap2.Append(Instruction.Create(OpCodes.Newobj, mtdCtor));
            ap2.Append(Instruction.Create(OpCodes.Dup));
            ap2.Append(Instruction.Create(OpCodes.Ldstr, NEW_THEME));
            ap2.Append(Instruction.Create(OpCodes.Stfld, fTheme));
            ap2.Append(Instruction.Create(OpCodes.Dup));
            ap2.Append(Instruction.Create(OpCodes.Ldc_I4_3));
            ap2.Append(Instruction.Create(OpCodes.Stfld, fLoop));
            ap2.Append(Instruction.Create(OpCodes.Dup));
            ap2.Append(Instruction.Create(OpCodes.Newobj, alCtor));
            ap2.Append(Instruction.Create(OpCodes.Stfld, fRes));
            ap2.Append(Instruction.Create(OpCodes.Stelem_Ref));
            ap2.Append(Instruction.Create(OpCodes.Ldarg_0));
            ap2.Append(Instruction.Create(OpCodes.Ldloc, vNew));
            ap2.Append(Instruction.Create(OpCodes.Stfld, fOrder));
            ap2.Append(Instruction.Create(OpCodes.Ldstr, "[CNMAP] 테마 추가: " + NEW_THEME));
            ap2.Append(Instruction.Create(OpCodes.Call, dbg));
            ap2.Append(done);
            title.Methods.Add(addTheme);

            var bgStart = bgT.Methods.First(m => m.Name == "Start");
            var sp = bgStart.Body.GetILProcessor();
            var sf0 = bgStart.Body.Instructions[0];
            sp.InsertBefore(sf0, Instruction.Create(OpCodes.Ldarg_0));
            sp.InsertBefore(sf0, Instruction.Create(OpCodes.Call, addTheme));

            // --- __ChaMapHook(string path) : 새 테마 자산을 번들에서 꺼낸다 ---
            var hook = new MethodDefinition("__ChaMapHook",
                MethodAttributes.Public | MethodAttributes.Static | MethodAttributes.HideBySig,
                mod.ImportReference(tUObj));
            hook.Parameters.Add(new ParameterDefinition("path", ParameterAttributes.None,
                                                        mod.TypeSystem.String));
            var hp = hook.Body.GetILProcessor();
            var nul = Instruction.Create(OpCodes.Ldnull);
            var strEq = mod.ImportReference(corlib.Types.First(t => t.FullName == "System.String")
                .Methods.First(m => m.Name == "op_Equality"));
            hp.Append(Instruction.Create(OpCodes.Ldsfld, fBundle));
            hp.Append(Instruction.Create(OpCodes.Brfalse, nul));
            hp.Append(Instruction.Create(OpCodes.Ldarg_0));
            hp.Append(Instruction.Create(OpCodes.Ldstr, HOOK_PATH));
            hp.Append(Instruction.Create(OpCodes.Call, strEq));
            hp.Append(Instruction.Create(OpCodes.Brfalse, nul));
            hp.Append(Instruction.Create(OpCodes.Ldsfld, fBundle));
            hp.Append(Instruction.Create(OpCodes.Ldstr, ASSET_NAME));
            hp.Append(Instruction.Create(OpCodes.Ldtoken, mod.ImportReference(tGO)));
            hp.Append(Instruction.Create(OpCodes.Call, getTFH));
            hp.Append(Instruction.Create(OpCodes.Callvirt, bundleLoad));
            hp.Append(Instruction.Create(OpCodes.Ret));
            hp.Append(nul);
            hp.Append(Instruction.Create(OpCodes.Ret));
            title.Methods.Add(hook);

            // ResourceByOption::Load 진입부에서 가로채기
            var rbo = mod.Types.First(t => t.Name == "ResourceByOption");
            var rboLoad = rbo.Methods.First(m => m.Name == "Load" && m.Parameters.Count == 1);
            var rp2 = rboLoad.Body.GetILProcessor();
            var rf0 = rboLoad.Body.Instructions[0];
            var skip = Instruction.Create(OpCodes.Pop);
            rp2.InsertBefore(rf0, Instruction.Create(OpCodes.Ldarg_0));
            rp2.InsertBefore(rf0, Instruction.Create(OpCodes.Call, hook));
            rp2.InsertBefore(rf0, Instruction.Create(OpCodes.Dup));
            rp2.InsertBefore(rf0, Instruction.Create(OpCodes.Brfalse, skip));
            rp2.InsertBefore(rf0, Instruction.Create(OpCodes.Ret));
            rp2.InsertBefore(rf0, skip);
            Console.WriteLine("  Background::Start -> 테마 추가 / ResourceByOption::Load -> 번들 가로채기");
        }

        // 360/NetmarbleS 플러그인은 이 환경에 존재하지 않는다.'''

if '__ChaAddTheme' not in s:
    assert anchor in s
    s = s.replace(anchor, add, 1)
    s = s.replace('        const string ASSET_NAME = "data_gbeach01";',
                  '        const string ASSET_NAME = "data_gbeach01";\n'
                  '        const string NEW_THEME = "gbeach";\n'
                  '        const string HOOK_PATH = "Background/gbeach01";')
    io.open(p, 'w', encoding='utf-8').write(s)
    print('patchcn.cs: 맵 추가 배선 삽입')
else:
    print('이미 있음')
