// 주행 중 일시정지로 나가면 로비 BGM 이 안 나오는 것을 고친다.
//
// 원인은 켠 쪽과 끈 쪽이 짝이 안 맞는 것이다.
//
//   Player::PressedPauseButton          AudioListener.pause = true
//                                       Time.timeScale = 0
//   Player::PressedContinuePlayButton   둘 다 되돌린다
//
//   ReturnMenu::OnReturnMyCarRoom       Time.timeScale = 1 **만** 되돌린다
//   ReturnMenu::OnReturnShop            (같음)
//   ReturnMenu::OnReturnReady           (같음)
//
// 즉 '계속하기'로 나오면 소리가 살아나지만, '내차고로'·'상점으로'·
// '준비화면으로' 나오면 `AudioListener.pause` 가 **켜진 채로 씬이 바뀐다**.
// AudioListener 는 씬을 넘어가도 그 값을 들고 있으므로 로비에서 BGM 이
// 통째로 죽는다. 원판부터 있던 흠이다(중국판 IL 로 확인).
//
// 고치는 법은 세 메서드 **입구**에 `AudioListener.pause = false` 한 줄을
// 넣는 것뿐이다. 입구 삽입은 이 프로젝트에서 안전한 것으로 확인된 방식이고,
// 이미 꺼져 있을 때 또 꺼도 아무 일도 없다.
//
// 사용법: pausefix.exe <in.dll> <out.dll> [managed폴더]
using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class PF
{
    static readonly string[] WAYS = {
        "OnReturnMyCarRoom", "OnReturnShop", "OnReturnReady",
    };

    static int Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine(
                "usage: pausefix <in.dll> <out.dll> [managed-dir]");
            return 2;
        }
        // UnityEngine.dll 은 입력 DLL 옆이 아니라 managed 폴더에 있다.
        var res = new DefaultAssemblyResolver();
        res.AddSearchDirectory(System.IO.Path.GetDirectoryName(
            System.IO.Path.GetFullPath(args[0])));
        res.AddSearchDirectory(args.Length > 2 ? args[2] : "mgbase");
        var mod = ModuleDefinition.ReadModule(
            args[0], new ReaderParameters { AssemblyResolver = res });

        var t = mod.GetTypes().FirstOrDefault(x => x.Name == "ReturnMenu");
        if (t == null) { Console.WriteLine("ReturnMenu 없음"); return 1; }

        // UnityEngine.AudioListener::set_pause(bool)
        var ue = res.Resolve(mod.AssemblyReferences.First(
            r => r.Name == "UnityEngine")).MainModule;
        var listener = ue.GetType("UnityEngine.AudioListener");
        var setPause = mod.ImportReference(listener.Methods.First(
            m => m.Name == "set_pause" && m.Parameters.Count == 1));

        int n = 0;
        foreach (var name in WAYS)
        {
            var me = t.Methods.FirstOrDefault(m => m.Name == name);
            if (me == null || !me.HasBody)
            {
                Console.WriteLine("  건너뜀: {0} 없음", name);
                continue;
            }
            var il = me.Body.GetILProcessor();
            var first = me.Body.Instructions[0];
            il.InsertBefore(first, Instruction.Create(OpCodes.Ldc_I4_0));
            il.InsertBefore(first, Instruction.Create(OpCodes.Call, setPause));
            Console.WriteLine("  {0} 입구에 AudioListener.pause = false", name);
            n++;
        }
        if (n == 0) { Console.WriteLine("고칠 것이 없다"); return 1; }

        mod.Write(args[1]);
        Console.WriteLine("일시정지로 나가도 BGM 이 살아나게 고쳤다 ({0}곳)", n);
        Console.WriteLine("저장: {0}", args[1]);
        return 0;
    }
}
