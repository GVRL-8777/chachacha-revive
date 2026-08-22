# -*- coding: utf-8 -*-
"""1단계 배선: 번들을 내려받아 AssetBundle.Load 가 실제로 동작하는지 실기에서 확인한다.

  · 서버: /bundle/<이름> 을 bundles/ 폴더에서 서빙
  · 클라: Generic_Title::Update 진입부에서 WWW 로 번들을 받고
          Load("Data_Gbeach01", typeof(GameObject)) 결과를 로그로 찍는다
"""
import io

# ---------- 서버 ----------
p = 'chacnserver.py'
s = io.open(p, encoding='utf-8').read()
if '/bundle/' not in s:
    old = '            if path.startswith("/tex/"):'
    new = '''            if path.startswith("/bundle/"):
                fp = os.path.join(SP, "bundles", os.path.basename(path))
                if os.path.isfile(fp):
                    data = open(fp, "rb").read()
                    log("         BUNDLE: %s (%d KB)" % (os.path.basename(fp), len(data) // 1024))
                    hdr = ("HTTP/1.1 200 OK", "Content-Type: application/octet-stream",
                           "Content-Length: %d" % len(data), "Connection: close", "", "")
                    self.request.sendall(CRLF.join(hdr).encode() + data)
                else:
                    log("         BUNDLE 없음: %s" % fp)
                    self.request.sendall(
                        CRLF.join(("HTTP/1.1 404 Not Found", "Content-Length: 0", "", "")).encode())
                return

            if path.startswith("/tex/"):'''
    if old in s:
        s = s.replace(old, new, 1)
    else:
        # /tex/ 블록이 없으면 경로 정규화 직전에 끼워 넣는다
        anchor = '            path = normalize(target.split("?")[0]).rstrip("/") or "/"'
        s = s.replace(anchor, new.replace('            if path.startswith("/tex/"):', '') + anchor, 1)
    io.open(p, 'w', encoding='utf-8').write(s)
    import ast
    ast.parse(io.open(p, encoding='utf-8').read())
    print('chacnserver.py: /bundle/ 서빙 추가')

# ---------- 클라이언트 패처 ----------
p2 = 'patchcn.cs'
s2 = io.open(p2, encoding='utf-8').read()

anchor = '        // 360/NetmarbleS 플러그인은 이 환경에 존재하지 않는다.'
add = '''        // ---- 번들 로딩 배선 ----
        // 색인(mainData)을 못 건드리므로, 추가 자산은 에셋번들로 얹는다.
        // WWW.assetBundle / AssetBundle.Load 는 restore.exe 로 선언을 되살려 뒀다.
        {
            var ue = res.Resolve(mod.AssemblyReferences.First(r => r.Name == "UnityEngine")).MainModule;
            var corlib = res.Resolve(mod.AssemblyReferences.First(r => r.Name == "mscorlib")).MainModule;
            TypeDefinition U(string n) { return ue.Types.First(t => t.FullName == n); }

            var tWWW = U("UnityEngine.WWW");
            var tBundle = U("UnityEngine.AssetBundle");
            var tUObj = U("UnityEngine.Object");
            var tGO = U("UnityEngine.GameObject");
            var tType = corlib.Types.First(t => t.FullName == "System.Type");
            var tStr = corlib.Types.First(t => t.FullName == "System.String");

            var wwwCtor = mod.ImportReference(tWWW.Methods.First(
                m => m.IsConstructor && m.Parameters.Count == 1
                     && m.Parameters[0].ParameterType.FullName == "System.String"));
            var wwwDone = mod.ImportReference(tWWW.Methods.First(m => m.Name == "get_isDone"));
            var wwwErr = mod.ImportReference(tWWW.Methods.First(m => m.Name == "get_error"));
            var wwwBundle = mod.ImportReference(tWWW.Methods.First(m => m.Name == "get_assetBundle"));
            var bundleLoad = mod.ImportReference(tBundle.Methods.First(
                m => m.Name == "Load" && m.Parameters.Count == 2));
            var getTFH = mod.ImportReference(tType.Methods.First(m => m.Name == "GetTypeFromHandle"));
            var concat = mod.ImportReference(tStr.Methods.First(
                m => m.Name == "Concat" && m.Parameters.Count == 2
                     && m.Parameters[0].ParameterType.FullName == "System.Object"));

            var fWww = new FieldDefinition("__cnWww",
                FieldAttributes.Public | FieldAttributes.Static, mod.ImportReference(tWWW));
            var fBundle = new FieldDefinition("__cnBundle",
                FieldAttributes.Public | FieldAttributes.Static, mod.ImportReference(tBundle));
            var fState = new FieldDefinition("__cnBState",
                FieldAttributes.Public | FieldAttributes.Static, mod.TypeSystem.Int32);
            title.Fields.Add(fWww); title.Fields.Add(fBundle); title.Fields.Add(fState);

            var tick = new MethodDefinition("__ChaBundleTick",
                MethodAttributes.Public | MethodAttributes.Static | MethodAttributes.HideBySig,
                mod.TypeSystem.Void);
            var tb = tick.Body;
            tb.InitLocals = true;
            var vObj = new VariableDefinition(mod.ImportReference(tUObj));
            tb.Variables.Add(vObj);
            var tp = tb.GetILProcessor();
            var end = Instruction.Create(OpCodes.Ret);
            var poll = Instruction.Create(OpCodes.Nop);

            tp.Append(Instruction.Create(OpCodes.Ldsfld, fState));
            tp.Append(Instruction.Create(OpCodes.Ldc_I4_2));
            tp.Append(Instruction.Create(OpCodes.Beq, end));
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fState));
            tp.Append(Instruction.Create(OpCodes.Brtrue, poll));
            tp.Append(Instruction.Create(OpCodes.Ldstr, BUNDLE_URL));
            tp.Append(Instruction.Create(OpCodes.Newobj, wwwCtor));
            tp.Append(Instruction.Create(OpCodes.Stsfld, fWww));
            tp.Append(Instruction.Create(OpCodes.Ldc_I4_1));
            tp.Append(Instruction.Create(OpCodes.Stsfld, fState));
            tp.Append(Instruction.Create(OpCodes.Br, end));
            tp.Append(poll);
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fWww));
            tp.Append(Instruction.Create(OpCodes.Callvirt, wwwDone));
            tp.Append(Instruction.Create(OpCodes.Brfalse, end));
            tp.Append(Instruction.Create(OpCodes.Ldc_I4_2));
            tp.Append(Instruction.Create(OpCodes.Stsfld, fState));
            // 에러 로그
            tp.Append(Instruction.Create(OpCodes.Ldstr, "[CNBUNDLE] error="));
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fWww));
            tp.Append(Instruction.Create(OpCodes.Callvirt, wwwErr));
            tp.Append(Instruction.Create(OpCodes.Call, concat));
            tp.Append(Instruction.Create(OpCodes.Call, dbg));
            // 번들 열기
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fWww));
            tp.Append(Instruction.Create(OpCodes.Callvirt, wwwBundle));
            tp.Append(Instruction.Create(OpCodes.Stsfld, fBundle));
            tp.Append(Instruction.Create(OpCodes.Ldstr, "[CNBUNDLE] bundle="));
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fBundle));
            tp.Append(Instruction.Create(OpCodes.Call, concat));
            tp.Append(Instruction.Create(OpCodes.Call, dbg));
            // Load 시도
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fBundle));
            tp.Append(Instruction.Create(OpCodes.Brfalse, end));
            tp.Append(Instruction.Create(OpCodes.Ldsfld, fBundle));
            tp.Append(Instruction.Create(OpCodes.Ldstr, ASSET_NAME));
            tp.Append(Instruction.Create(OpCodes.Ldtoken, mod.ImportReference(tGO)));
            tp.Append(Instruction.Create(OpCodes.Call, getTFH));
            tp.Append(Instruction.Create(OpCodes.Callvirt, bundleLoad));
            tp.Append(Instruction.Create(OpCodes.Stloc, vObj));
            tp.Append(Instruction.Create(OpCodes.Ldstr, "[CNBUNDLE] Load 결과="));
            tp.Append(Instruction.Create(OpCodes.Ldloc, vObj));
            tp.Append(Instruction.Create(OpCodes.Call, concat));
            tp.Append(Instruction.Create(OpCodes.Call, dbg));
            tp.Append(end);
            title.Methods.Add(tick);

            // Update 진입부에서 매 프레임 진행시킨다
            il.InsertBefore(first, Instruction.Create(OpCodes.Call, tick));
            Console.WriteLine("  Generic_Title::Update -> __ChaBundleTick (번들 다운로드/로드 검증)");
        }

        // 360/NetmarbleS 플러그인은 이 환경에 존재하지 않는다.'''

if '__ChaBundleTick' not in s2:
    assert anchor in s2
    s2 = s2.replace(anchor, add, 1)
    s2 = s2.replace('        string mode = a.Length > 4 ? a[4] : "guest";   // guest | server',
                    '        string mode = a.Length > 4 ? a[4] : "guest";   // guest | server\n'
                    '        const string BUNDLE_URL = "http://192.168.0.10:8888/bundle/greece.unity3d";\n'
                    '        const string ASSET_NAME = "Data_Gbeach01";')
    io.open(p2, 'w', encoding='utf-8').write(s2)
    print('patchcn.cs: 번들 검증 코드 추가')
