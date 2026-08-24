// 드라이버 9~12 번의 컷인이 **전부 나정비 얼굴**로 나오는 것을 고친다.
//
// `Player::_GetCutinModel` 은 이렇게 생겼다.
//
//   int r = 12;                                  // 12 = eCutinModelType.MaxCount
//   if (carName=="Poli")  r = 6;   ... helly → 9
//   else switch (driverType) {                   // Driver_1..8 → 0,1,2,3,4,5,10,11
//       ...
//   }
//   if (r == 12) Debug.LogError("not found cutinmodel");
//
// 스위치에 가지가 여덟뿐이라 드라이버 9~12(나정비 · 안별이 · 쌈바여인 ·
// 한이 가희)는 **전부 기본값 12** 로 떨어진다. 컷인 배열이 넷뿐이던 때는
// 12번이 배열 밖이라 아무것도 안 나왔는데, `tools/cutin5.py` 로 배열을
// 열넷으로 늘리면서 12번이 **나정비** 자리가 되어 넷 다 나정비가 나온다.
//
// 고치는 것
//
//   · `eCutinModelType` 에 NAJUNGBI(12) · AHNBYULE(13) 을 더한다.
//     이름이 있어야 보이스도 탄다 — `Cutin::SetVoiceAudioClip` 이
//     `"Character VOX/" + 열거자이름 + ...` 으로 경로를 짓기 때문이다.
//   · 스위치에 가지 둘을 더해 Driver_9 → 12, Driver_10 → 13 으로 보낸다.
//   · **기본값을 12 에서 14 로 올린다.** 안 그러면 짝이 없는 드라이버가
//     여전히 나정비를 뒤집어쓴다. 14 는 배열 밖이라 아무것도 안 나온다.
//     (쌈바여인 · 한이 가희는 컷인 그림도 보이스도 어느 판에도 없다.)
//   · "못 찾음" 경고의 기준값도 12 → 14 로 맞춘다.
//
// 사용법: drivercutin.exe <in.dll> <out.dll> [managed폴더]
using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class DC
{
    const int NAJUNGBI = 12;
    const int AHNBYULE = 13;
    const int NONE = 14;          // 배열 밖 = 컷인 없음

    static void AddEnum(TypeDefinition e, string name, int value, ModuleDefinition mod)
    {
        if (e.Fields.Any(x => x.Name == name)) return;
        var fd = new FieldDefinition(name,
            FieldAttributes.Public | FieldAttributes.Static |
            FieldAttributes.Literal | FieldAttributes.HasDefault,
            e);
        fd.Constant = value;
        e.Fields.Add(fd);
        Console.WriteLine("  {0}.{1} = {2}", e.Name, name, value);
    }

    static int Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine(
                "usage: drivercutin <in.dll> <out.dll> [managed-dir]");
            return 2;
        }
        var res = new DefaultAssemblyResolver();
        res.AddSearchDirectory(System.IO.Path.GetDirectoryName(
            System.IO.Path.GetFullPath(args[0])));
        res.AddSearchDirectory(args.Length > 2 ? args[2] : "mgbase");
        var mod = ModuleDefinition.ReadModule(
            args[0], new ReaderParameters { AssemblyResolver = res });

        // --- 열거자 넓히기 ---
        var cut = mod.GetTypes().FirstOrDefault(t => t.Name == "eCutinModelType");
        if (cut == null) { Console.WriteLine("eCutinModelType 없음"); return 1; }
        AddEnum(cut, "NAJUNGBI", NAJUNGBI, mod);
        AddEnum(cut, "AHNBYULE", AHNBYULE, mod);
        var max = cut.Fields.FirstOrDefault(f => f.Name == "MaxCount");
        if (max != null && (int)max.Constant != NONE)
        {
            max.Constant = NONE;
            Console.WriteLine("  eCutinModelType.MaxCount = {0}", NONE);
        }
        var drv = mod.GetTypes().FirstOrDefault(t => t.Name == "eDriverType");
        if (drv != null)
        {
            for (int i = 9; i <= 12; i++)
                AddEnum(drv, "Driver_" + i, i - 1, mod);
            var dmax = drv.Fields.FirstOrDefault(
                f => f.Name == "MAX_COUNT_DIRVER");
            if (dmax != null && (int)dmax.Constant != 12) dmax.Constant = 12;
        }

        // --- 스위치에 가지 둘 더하기 ---
        var player = mod.GetTypes().FirstOrDefault(t => t.Name == "Player");
        var me = player == null ? null : player.Methods.FirstOrDefault(
            m => m.Name == "_GetCutinModel" && m.HasBody);
        if (me == null) { Console.WriteLine("Player::_GetCutinModel 없음"); return 1; }
        var il = me.Body.GetILProcessor();
        var ins = me.Body.Instructions;

        var sw = ins.FirstOrDefault(i => i.OpCode == OpCodes.Switch);
        if (sw == null) { Console.WriteLine("스위치를 못 찾았다"); return 1; }
        var targets = (Instruction[])sw.Operand;
        if (targets.Length != 8)
        {
            Console.WriteLine("가지가 {0}개다 — 이미 고쳤거나 판이 다르다",
                              targets.Length);
            return 1;
        }
        // 기존 가지가 뛰어가는 자리(= 값을 돌려주기 직전)를 찾는다.
        Instruction end = null;
        for (var p = targets[targets.Length - 1]; p != null; p = p.Next)
            if (p.OpCode == OpCodes.Br || p.OpCode == OpCodes.Br_S)
            { end = (Instruction)p.Operand; break; }
        if (end == null) { Console.WriteLine("가지 끝을 못 찾았다"); return 1; }

        var made = new Instruction[2];
        int[] want = { NAJUNGBI, AHNBYULE };
        for (int k = 0; k < 2; k++)
        {
            var head = Instruction.Create(OpCodes.Ldc_I4, want[k]);
            il.InsertBefore(end, head);
            il.InsertBefore(end, Instruction.Create(OpCodes.Stloc_0));
            il.InsertBefore(end, Instruction.Create(OpCodes.Br, end));
            made[k] = head;
        }
        var nt = new Instruction[10];
        Array.Copy(targets, nt, 8);
        nt[8] = made[0];        // Driver_9  → NAJUNGBI
        nt[9] = made[1];        // Driver_10 → AHNBYULE
        sw.Operand = nt;
        Console.WriteLine("  스위치 8 → 10가지 (Driver_9 → {0} · Driver_10 → {1})",
                          NAJUNGBI, AHNBYULE);

        // --- 기본값과 경고 기준을 12 → 14 로 ---
        int n = 0;
        foreach (var i in ins)
        {
            if ((i.OpCode == OpCodes.Ldc_I4_S && Convert.ToInt32(i.Operand) == 12) ||
                (i.OpCode == OpCodes.Ldc_I4 && Convert.ToInt32(i.Operand) == 12))
            {
                // 스위치 가지 안에서 새로 넣은 12(NAJUNGBI)는 건드리지 않는다
                if (i == made[0]) continue;
                i.OpCode = OpCodes.Ldc_I4_S;
                i.Operand = (sbyte)NONE;
                n++;
            }
        }
        Console.WriteLine("  '짝 없음' 값을 12 → {0} 으로 ({1}곳)", NONE, n);

        mod.Write(args[1]);
        Console.WriteLine("드라이버 9~12 의 컷인을 제자리로 돌렸다");
        Console.WriteLine("저장: {0}", args[1]);
        return 0;
    }
}
