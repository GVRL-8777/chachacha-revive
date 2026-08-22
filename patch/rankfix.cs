// 주간순위를 소셜 플랫폼 없이도 그릴 수 있게 한다.
//
// CRSystem.SetDefaultRankData 는 이름(nickname)을 두 군데서만 채운다.
//   · userId 가 내 소셜 ID 와 같으면  -> Localization("Me") = "나"
//   · 카카오/넷마블 친구 목록에 있으면 -> 그 친구 닉네임
// 사설 서버에는 소셜 플랫폼이 없어 **둘 다 실패**하고 nickname 이 null 로 남는다.
// 그러면 RankUnit.set_userName(null) 이 널참조로 죽어 순위표가 통째로 안 뜬다.
//
// 그래서 메서드 **끝의 ret 앞에** 마무리 블록을 덧붙인다.
//   if (d.nickname == null) {
//       if (d.userId == "__me__") { d.isMe = true; d.nickname = Localization.Get("Me"); }
//       else d.nickname = d.userId;
//   }
// 원래 명령은 순서가 그대로고 뒤에만 붙으므로 중간 삽입이 아니다.
// ret 로 오던 분기들은 Cecil 이 새 첫 명령으로 다시 이어 준다(전부 이 블록을 탄다).
//
// 사용법: rankfix.exe <in.dll> <out.dll>
using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class RF
{
    const string MARK = "__me__";      // 서버가 내 줄에 넣어 주는 표식

    static int Main(string[] args)
    {
        string inDll = args[0], outDll = args[1];
        var mod = ModuleDefinition.ReadModule(inDll);

        var rankData = mod.GetTypes().First(t => t.Name == "RankData");
        var fNick = rankData.Fields.First(f => f.Name == "nickname");
        var fUser = rankData.Fields.First(f => f.Name == "userId");
        var fIsMe = rankData.Fields.First(f => f.Name == "isMe");

        var crs = mod.GetTypes().First(t => t.Name == "CRSystem");
        var m = crs.Methods.First(x => x.Name == "SetDefaultRankData");

        var loc = mod.GetTypes().First(t => t.Name == "Localization");
        var locInst = loc.Methods.First(x => x.Name == "get_instance");
        var locGet = loc.Methods.First(x => x.Name == "Get"
                                       && x.Parameters.Count == 1);
        var strEq = mod.ImportReference(
            mod.ImportReference(typeof(string)).Resolve().Methods
               .First(x => x.Name == "op_Equality"));

        var il = m.Body.GetILProcessor();
        var ret = m.Body.Instructions.Last();
        if (ret.OpCode != OpCodes.Ret) { Console.WriteLine("끝이 ret 이 아니다"); return 1; }

        // 이름이 이미 있으면 건너뛴다
        var skip = Instruction.Create(OpCodes.Nop);
        var notMe = Instruction.Create(OpCodes.Nop);
        var block = new[]
        {
            Instruction.Create(OpCodes.Ldarg_1),
            Instruction.Create(OpCodes.Ldfld, fNick),
            Instruction.Create(OpCodes.Brtrue, skip),
            // if (userId == "__me__")
            Instruction.Create(OpCodes.Ldarg_1),
            Instruction.Create(OpCodes.Ldfld, fUser),
            Instruction.Create(OpCodes.Ldstr, MARK),
            Instruction.Create(OpCodes.Call, strEq),
            Instruction.Create(OpCodes.Brfalse, notMe),
            Instruction.Create(OpCodes.Ldarg_1),
            Instruction.Create(OpCodes.Ldc_I4_1),
            Instruction.Create(OpCodes.Stfld, fIsMe),
            Instruction.Create(OpCodes.Ldarg_1),
            Instruction.Create(OpCodes.Call, locInst),
            Instruction.Create(OpCodes.Ldstr, "Me"),
            Instruction.Create(OpCodes.Callvirt, locGet),
            Instruction.Create(OpCodes.Stfld, fNick),
            Instruction.Create(OpCodes.Br, skip),
            // else nickname = userId
            notMe,
            Instruction.Create(OpCodes.Ldarg_1),
            Instruction.Create(OpCodes.Ldarg_1),
            Instruction.Create(OpCodes.Ldfld, fUser),
            Instruction.Create(OpCodes.Stfld, fNick),
            skip,
        };
        foreach (var ins in block) il.InsertBefore(ret, ins);
        m.Body.MaxStackSize = Math.Max(m.Body.MaxStackSize, 3);

        // ret 로 오던 분기를 새 블록의 첫 명령으로 돌린다
        int moved = 0;
        foreach (var ins in m.Body.Instructions)
        {
            if (ins.Operand == ret) { ins.Operand = block[0]; moved++; }
        }
        Console.WriteLine("SetDefaultRankData 마무리 블록 추가 (분기 " + moved + "개 이음)");

        mod.Write(outDll);
        Console.WriteLine("순위표 보정 -> " + outDll);
        return 0;
    }
}
