// localfix — 서버 없이 도는 빌드로 바꾼다.
//
// 게임 로직은 손대지 않는다. 바깥과 이야기하는 자리 넷만 갈아 끼운다.
//
//   1) Generic_HTTP.SendPacket 들머리에  ChaLocal.Note(url, body)
//      요청 본문은 이 지점에서 아직 **평문**이다. 암호화는 그 아래에서 한다.
//   2) 그 안의 `new WWW(url, bytes, headers)` -> ChaLocal.MakeWWW(...)
//      스택 모양이 같아 연산자만 바꾸면 된다. 실제로는 통신하지 않고
//      곧바로 끝나는 파일 요청을 돌려주며, 그 자리에서 답을 만들어 둔다.
//   3) www.text / www.error 전부 -> ChaLocal.Text / ChaLocal.Err
//      우리가 만든 WWW 인지 표로 확인하고, 아니면 진짜 값을 그대로 준다.
//      그래서 프로필 사진 내려받기 같은 남의 WWW 는 멀쩡히 돈다.
//   4) Generic_HTTP_Recv 안의 Aes.Decrypt(...) -> ChaLocal.Dec(...)
//      로컬 응답은 처음부터 평문이라 풀 것이 없다. **그 밖에서는 손대지 않는다** —
//      Generic_HTTP 는 토큰·키·IV 를 암호화해 들고 있고 게터가 Decrypt 로 푼다.
//   5) 복원 자산 번들은 PC 가 아니라 APK 안(StreamingAssets)에서 읽는다.
//
//   localfix.exe <입력.dll> <출력.dll> <ChaLocal.dll> [검색폴더]
using System;
using System.Collections.Generic;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

class LocalFix
{
    static ModuleDefinition mod;
    static int nText, nErr, nDec, nWWW, nBundle;

    static IEnumerable<TypeDefinition> All(TypeDefinition t)
    {
        yield return t;
        foreach (var n in t.NestedTypes)
            foreach (var x in All(n)) yield return x;
    }

    static MethodReference Ref(ModuleDefinition local, string name)
    {
        var t = local.Types.First(x => x.Name == "ChaLocal");
        var m = t.Methods.First(x => x.Name == name);
        return mod.ImportReference(m);
    }

    // ---------------------------------------------------------- 갈림길
    //
    // 갈고리 대부분은 ChaLocal 혼자 갈래를 나눌 수 있다(Note · MakeWWW ·
    // BundleWWW). 그런데 둘은 **게임 자신의 타입**이 있어야 원래 하던 일을
    // 할 수 있다 — Aes.Decrypt 와 CRSystem.myTrophy 다. ChaLocal.dll 은
    // Assembly-CSharp 을 참조할 수 없으므로(서로 물린다), 대신 여기서
    // Assembly-CSharp 안에 작은 갈림길을 만들어 준다.
    //
    //     if (ChaLocal.IsLocal()) return <ChaLocal 쪽>;
    //     else                    return <원래 하던 것>;
    //
    static TypeDefinition holder;

    static TypeDefinition Holder()
    {
        if (holder == null)
        {
            holder = new TypeDefinition("", "__ChaSwitch",
                TypeAttributes.Class | TypeAttributes.NotPublic
                | TypeAttributes.Sealed | TypeAttributes.AnsiClass,
                mod.TypeSystem.Object);
            mod.Types.Add(holder);
        }
        return holder;
    }

    /// `original` 을 대신할 갈림길 메서드를 만들어 돌려준다.
    static MethodReference Fork(string name, MethodReference original,
                                MethodReference localWay, MethodReference isLocal)
    {
        var m = new MethodDefinition(name,
            MethodAttributes.Public | MethodAttributes.Static
            | MethodAttributes.HideBySig, original.ReturnType);
        // 인스턴스 메서드면 자기 자신이 첫 인자로 온다(스택 모양이 같아진다)
        if (original.HasThis)
            m.Parameters.Add(new ParameterDefinition("self",
                ParameterAttributes.None, original.DeclaringType));
        foreach (var p in original.Parameters)
            m.Parameters.Add(new ParameterDefinition(
                p.Name, ParameterAttributes.None, p.ParameterType));

        Console.WriteLine("  갈림길 " + name
            + " : 원래 " + original.ReturnType.Name
            + " / 로컬 " + localWay.ReturnType.Name
            + " / 인자 " + m.Parameters.Count);
        if (original.ReturnType.FullName != localWay.ReturnType.FullName)
            Console.WriteLine("  [주의] 반환형이 다르다 — "
                + original.ReturnType.FullName + " vs " + localWay.ReturnType.FullName);

        var b = m.Body;
        var p2 = b.GetILProcessor();
        var toServer = Instruction.Create(OpCodes.Nop);

        p2.Append(Instruction.Create(OpCodes.Call, isLocal));
        p2.Append(Instruction.Create(OpCodes.Brfalse, toServer));
        for (int i = 0; i < m.Parameters.Count; i++)
            p2.Append(Instruction.Create(OpCodes.Ldarg, m.Parameters[i]));
        p2.Append(Instruction.Create(OpCodes.Call, localWay));
        p2.Append(Instruction.Create(OpCodes.Ret));

        p2.Append(toServer);
        for (int i = 0; i < m.Parameters.Count; i++)
            p2.Append(Instruction.Create(OpCodes.Ldarg, m.Parameters[i]));
        p2.Append(Instruction.Create(
            original.HasThis ? OpCodes.Callvirt : OpCodes.Call, original));
        p2.Append(Instruction.Create(OpCodes.Ret));

        Holder().Methods.Add(m);
        return m;
    }

    static int Main(string[] argv)
    {
        if (argv.Length < 3)
        {
            Console.WriteLine("쓰기: localfix.exe 입력.dll 출력.dll ChaLocal.dll [검색폴더]");
            return 2;
        }
        string dir = argv.Length > 3 ? argv[3] : "mgbase";
        var res = new DefaultAssemblyResolver();
        res.AddSearchDirectory(dir);
        res.AddSearchDirectory(System.IO.Path.GetDirectoryName(
            System.IO.Path.GetFullPath(argv[2])));
        mod = ModuleDefinition.ReadModule(argv[0],
                new ReaderParameters { AssemblyResolver = res });
        // csc 가 자동으로 붙이는 어셈블리 특성은 이 빌드의 mscorlib 에 없다.
        // 두어도 대개 탈은 없지만, 없는 참조를 남겨 둘 이유가 없다.
        // (읽는 중에는 같은 파일을 못 쓰니 한 번 닫고 갈아치운다)
        int dropped = 0;
        string tmp = argv[2] + ".tmp";
        using (var lw = ModuleDefinition.ReadModule(argv[2]))
        {
            foreach (var a in lw.Assembly.CustomAttributes
                              .Where(x => x.AttributeType.Namespace
                                     == "System.Runtime.CompilerServices").ToList())
            {
                lw.Assembly.CustomAttributes.Remove(a);
                dropped++;
            }
            if (dropped > 0) lw.Write(tmp);
        }
        if (dropped > 0)
        {
            System.IO.File.Delete(argv[2]);
            System.IO.File.Move(tmp, argv[2]);
            Console.WriteLine("ChaLocal.dll 에서 군더더기 특성 " + dropped + "개를 뺐다");
        }
        var local = ModuleDefinition.ReadModule(argv[2]);

        var mNote = Ref(local, "Note");
        var mMake = Ref(local, "MakeWWW");
        var mText = Ref(local, "Text");
        var mErr = Ref(local, "Err");
        var mDec = Ref(local, "Dec");
        var mBundle = Ref(local, "BundleWWW");
        var mIsLocal = Ref(local, "IsLocal");
        // 갈림길은 원래 부르던 것을 만난 자리에서 만든다(그때야 서명을 안다)
        MethodReference fDec = null;

        var types = mod.Types.SelectMany(x => All(x)).ToList();

        // ---- 1) SendPacket 들머리 + 그 안의 WWW 생성 -------------------
        var http = types.First(t => t.FullName == "Generic_HTTP");
        var send = http.Methods.First(m => m.Name == "SendPacket"
                                      && m.Parameters.Count == 7);
        var il = send.Body.GetILProcessor();
        var head = send.Body.Instructions[0];
        il.InsertBefore(head, Instruction.Create(OpCodes.Ldarg_1));   // url
        il.InsertBefore(head, Instruction.Create(OpCodes.Ldarg_2));   // body(평문)
        il.InsertBefore(head, Instruction.Create(OpCodes.Call, mNote));

        foreach (var ins in send.Body.Instructions)
        {
            var mr = ins.Operand as MethodReference;
            if (ins.OpCode != OpCodes.Newobj || mr == null) continue;
            if (!mr.DeclaringType.FullName.EndsWith("UnityEngine.WWW")) continue;
            if (mr.Parameters.Count != 3) continue;
            ins.OpCode = OpCodes.Call;
            ins.Operand = mMake;
            nWWW++;
        }

        // ---- 1-2) 두 번째 관문: NetDispatcher._MakeWWW -----------------
        // NetQuery 층이 따로 WWW 를 만든다. 로비·되팔기·랭킹이 이 길로 간다.
        // 평문 본문은 NetQueryData.queryString 에 있다(_BuildPacketStream
        // 이 그걸 암호화한다). 그래서 그 둘을 그대로 Note 에 넘긴다.
        var nd = types.FirstOrDefault(t2 => t2.FullName == "NetDispatcher");
        if (nd != null)
        {
            var mk = nd.Methods.FirstOrDefault(m2 => m2.Name == "_MakeWWW");
            if (mk != null && mk.HasBody)
            {
                MethodReference getUrl = null, getQs = null;
                foreach (var ins in mk.Body.Instructions)
                {
                    var mr = ins.Operand as MethodReference;
                    if (mr == null) continue;
                    if (mr.Name == "get_url") getUrl = mr;
                    if (mr.Name == "get_queryString") getQs = mr;
                }
                if (getUrl != null && getQs != null)
                {
                    var il2 = mk.Body.GetILProcessor();
                    var h2 = mk.Body.Instructions[0];
                    il2.InsertBefore(h2, Instruction.Create(OpCodes.Ldarg_1));
                    il2.InsertBefore(h2, Instruction.Create(OpCodes.Callvirt, getUrl));
                    il2.InsertBefore(h2, Instruction.Create(OpCodes.Ldarg_1));
                    il2.InsertBefore(h2, Instruction.Create(OpCodes.Callvirt, getQs));
                    il2.InsertBefore(h2, Instruction.Create(OpCodes.Call, mNote));
                    foreach (var ins in mk.Body.Instructions)
                    {
                        var mr = ins.Operand as MethodReference;
                        if (ins.OpCode != OpCodes.Newobj || mr == null) continue;
                        if (!mr.DeclaringType.FullName.EndsWith("UnityEngine.WWW")) continue;
                        if (mr.Parameters.Count != 3) continue;
                        ins.OpCode = OpCodes.Call;
                        ins.Operand = mMake;
                        nWWW++;
                    }
                    Console.WriteLine("NetDispatcher._MakeWWW 도 갈아 끼웠다");
                }
            }
        }

        // ---- 1-3) 캐릭터 구매 판정은 **건드리지 않는다** ---------------
        // 예전에는 `DriverUnit::OnBuyDriver` 의 `myTrophy < 카드값` 읽기를
        // `ChaLocal.BuyPower`(트로피 + 골드환산)로 바꿔 골드로도 살 수 있게
        // 했습니다. 그런데 그러면 트로피가 모자라도 카드가 그냥 사지는 것처럼
        // 보입니다. 게임 자신의 판정을 그대로 두면 트로피가 모자랄 때
        // **트로피 상점으로 보내 줍니다** — 그게 원래 모습입니다.

        // ---- 2) www.text · www.error · Aes.Decrypt · 번들 주소 ---------
        foreach (var t in types)
            foreach (var me in t.Methods)
            {
                if (!me.HasBody) continue;
                // Aes.Decrypt 는 응답을 푸는 데만 쓰이는 게 아니다.
                // Generic_HTTP 는 토큰·키·IV 를 **암호화한 채로** 들고 있어
                // 게터가 Decrypt 로 풀어 준다. 거기까지 통과 함수로 바꾸면
                // 게터가 암호문을 돌려줘 "IV length is different than
                // block size" 로 죽는다. 그 클래스만 뺀다.
                bool inRecv = t.FullName.Split('/')[0] != "Generic_HTTP";
                foreach (var ins in me.Body.Instructions)
                {
                    var mr = ins.Operand as MethodReference;
                    if (mr == null) continue;
                    string fn = mr.FullName;
                    if (fn.Contains("UnityEngine.WWW::get_text"))
                    { ins.OpCode = OpCodes.Call; ins.Operand = mText; nText++; }
                    else if (fn.Contains("UnityEngine.WWW::get_error"))
                    { ins.OpCode = OpCodes.Call; ins.Operand = mErr; nErr++; }
                    else if (fn.Contains("Aes::Decrypt") && inRecv)
                    {
                        if (fDec == null)
                            fDec = Fork("__ChaDec", mr, mDec, mIsLocal);
                        ins.OpCode = OpCodes.Call;
                        ins.Operand = fDec;
                        nDec++;
                    }
                    else if (t.FullName == "Generic_Title"
                             && ins.OpCode == OpCodes.Newobj
                             && mr.DeclaringType.FullName.EndsWith("UnityEngine.WWW")
                             && mr.Parameters.Count == 1)
                    { ins.OpCode = OpCodes.Call; ins.Operand = mBundle; nBundle++; }
                }
            }

        mod.Write(argv[1]);
        Console.WriteLine("SendPacket 들머리 1곳 · WWW 생성 " + nWWW + "곳");
        Console.WriteLine("www.text " + nText + "곳 · www.error " + nErr
                          + "곳 · Aes.Decrypt " + nDec + "곳");
        Console.WriteLine("번들 주소 " + nBundle + "곳 -> APK 안 StreamingAssets");
        Console.WriteLine("썼다: " + argv[1]);
        return (nWWW == 2 && nText > 0 && nBundle == 1) ? 0 : 1;
    }
}
