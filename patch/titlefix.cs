// titlefix — 타이틀 화면이 그냥 지나쳐 버리는 것을 고칩니다.
//
// 중국판은 소셜 로그인이 없어서 patchcn 이 Generic_Title::Update 들머리에
// "N 프레임 뒤 OnGuestPlayOk()" 라는 카운터를 심어 두었습니다. 그런데 그
// 카운터는 **넷마블·카카오 로고가 도는 동안에도** 돕니다. 로고에만 8초쯤
// 걸리니, 타이틀(Title_MainInteractionProcess)에 닿는 순간 이미 카운터가
// 차 있어 곧바로 로그인 -> 로딩 -> 로비로 넘어가 버립니다.
// 그래서 '다함께 차차차!' 보이스와 타이틀 그림을 볼 틈이 없습니다.
//
// 고치는 방법은 간단합니다. **타이틀 화면에 닿기 전에는 카운터를 0 으로
// 되돌립니다.** 그러면 카운터는 타이틀이 실제로 떠 있는 동안에만 흐릅니다.
// 세는 값도 줄여, 타이틀을 잠깐 보여 준 뒤 넘어가게 합니다.
//
//   titlefix.exe <입력.dll> <출력.dll> [프레임=180]
using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

class TitleFix
{
    static int Main(string[] argv)
    {
        if (argv.Length < 2)
        {
            Console.WriteLine("쓰기: titlefix.exe 입력.dll 출력.dll [프레임]");
            return 2;
        }
        int frames = argv.Length > 2 ? int.Parse(argv[2]) : 180;
        var mod = ModuleDefinition.ReadModule(argv[0]);

        var title = mod.Types.First(t => t.Name == "Generic_Title");
        var phase = mod.Types.First(t => t.Name == "TitlePhase");
        var mPhase = phase.Fields.First(f => f.Name == "mPhase");
        var counter = title.Fields.FirstOrDefault(f => f.Name == "__cnFrames");
        if (counter == null)
        {
            Console.WriteLine("__cnFrames 가 없다. patchcn 을 먼저 돌려라.");
            return 1;
        }
        var update = title.Methods.First(m => m.Name == "Update");
        var body = update.Body;
        var il = body.GetILProcessor();

        // 카운터 블록이 건너뛸 때 쓰는 자리를 찾는다. patchcn 이 심은
        // Blt / Bne_Un 이 모두 그 자리를 가리킨다.
        Instruction after = null;
        Instruction load300 = null;
        foreach (var ins in body.Instructions)
        {
            if ((ins.OpCode == OpCodes.Blt || ins.OpCode == OpCodes.Bne_Un)
                && ins.Operand is Instruction)
                after = (Instruction)ins.Operand;
            if (ins.OpCode == OpCodes.Ldc_I4 && ins.Next != null
                && ins.Next.OpCode == OpCodes.Bne_Un)
                load300 = ins;
        }
        if (after == null || load300 == null)
        {
            Console.WriteLine("카운터 블록을 못 찾았다.");
            return 1;
        }
        int old = (int)load300.Operand;

        // 카운터 블록이 시작되는 자리 = 첫 Ldsfld __cnFrames
        var head = body.Instructions.First(
            x => x.OpCode == OpCodes.Ldsfld && x.Operand == counter);

        // if (mPhase < Title_MainInteractionProcess) __cnFrames = 0;
        var skip = Instruction.Create(OpCodes.Nop);
        var ins0 = Instruction.Create(OpCodes.Ldarg_0);
        var ins1 = Instruction.Create(OpCodes.Ldfld, mPhase);
        var ins2 = Instruction.Create(OpCodes.Ldc_I4, 16);
        var ins3 = Instruction.Create(OpCodes.Bge, skip);
        var ins4 = Instruction.Create(OpCodes.Ldc_I4_0);
        var ins5 = Instruction.Create(OpCodes.Stsfld, counter);
        foreach (var x in new[] { ins0, ins1, ins2, ins3, ins4, ins5, skip })
            il.InsertBefore(head, x);

        load300.Operand = frames;

        mod.Write(argv[1]);
        Console.WriteLine("타이틀 전에는 카운터를 멈춘다 (mPhase < 16 이면 0 으로)");
        Console.WriteLine("자동 로그인 " + old + "프레임 -> " + frames
                          + "프레임 (타이틀이 떠 있는 동안만 센다)");
        Console.WriteLine("썼다: " + argv[1]);
        return 0;
    }
}
