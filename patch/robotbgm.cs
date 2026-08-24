// 로보카 차(헬리 · 폴리 · 엠버 · 로이)로 달리면 BGM 이 아예 안 나오는 것을 고친다.
//
// 원인은 중국판이 로보카 전용 테마를 들어내면서 **가드만 남겨 둔** 것이다.
//
//   Player::GameStart      if (baseData.robot == null) bgmSound.Play();
//
// 즉 변신 차(robot != null)는 무대 BGM 을 **일부러 건너뛴다.** 한국 정식판
// 5.1.0 을 뜯어 보면 그 자리에 짝이 있다.
//
//   Player::SetPlayBGM(bool on)
//       if (on) {
//           if (baseData.robot == null) mainBgmSound[playLevel].Play();
//           else                        robocaBGMSound.Play();
//       } else { ... }
//
// 로보카 차는 무대 BGM 대신 **자기 테마**(`Roboca_BGM`)를 틀었다. 중국판엔
// 로보카 차가 없어 `robocaBGMSound` 필드째 사라졌고, 가드만 남아 아무것도
// 안 울리게 되었다. 실기에서 확인했다 — 효과음은 나는데 BGM 만 없다.
//
// 그 테마는 우리에게 아직 있다. 공여판 번들이 들고 있던 `Roboca_BGM`
// (1.46 MB, MP3) 이 `car/helly/sound/Roboca_BGM` 으로 그대로 남아 있다.
// 그래서 필드를 새로 만들지 않고 **있는 `bgmSound` 의 클립만 갈아 끼운다.**
// 볼륨 · 루프 같은 나머지 설정을 그대로 물려받으므로 손댈 것이 적다.
//
//   if (baseData.robot != null) {
//       AudioClip c = Generic_Title.__ChaResLoad(ROBOCA) as AudioClip;
//       if (c != null) bgmSound.clip = c;
//   }
//   bgmSound.Play();                      // 이제 **늘** 튼다
//
// 테마를 못 찾으면 그냥 무대 BGM 이 나온다 — 조용해지는 일은 없다.
//
// 사용법: robotbgm.exe <in.dll> <out.dll> [managed폴더]
using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class RB
{
    // 번들은 경로의 **마지막 마디**를 소문자로 만들어 찾는다 → roboca_bgm
    const string ROBOCA = "Car/Helly/Sound/Roboca_BGM";

    static int Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine(
                "usage: robotbgm <in.dll> <out.dll> [managed-dir]");
            return 2;
        }
        var res = new DefaultAssemblyResolver();
        res.AddSearchDirectory(System.IO.Path.GetDirectoryName(
            System.IO.Path.GetFullPath(args[0])));
        res.AddSearchDirectory(args.Length > 2 ? args[2] : "mgbase");
        var mod = ModuleDefinition.ReadModule(
            args[0], new ReaderParameters { AssemblyResolver = res });

        var player = mod.GetTypes().FirstOrDefault(x => x.Name == "Player");
        if (player == null) { Console.WriteLine("Player 없음"); return 1; }
        var start = player.Methods.FirstOrDefault(
            m => m.Name == "GameStart" && m.HasBody);
        if (start == null) { Console.WriteLine("Player::GameStart 없음"); return 1; }

        var ue = res.Resolve(mod.AssemblyReferences.First(
            r => r.Name == "UnityEngine")).MainModule;
        var clipType = mod.ImportReference(ue.GetType("UnityEngine.AudioClip"));
        var setClip = mod.ImportReference(ue.GetType("UnityEngine.AudioSource")
            .Methods.First(m => m.Name == "set_clip"));
        var title = mod.GetTypes().First(x => x.Name == "Generic_Title");
        var load = title.Methods.First(
            m => m.Name == "__ChaResLoad" && m.Parameters.Count == 1);
        var bgm = player.Fields.First(f => f.Name == "bgmSound");

        // `bgmSound.Play()` 를 여는 자리와, 그 앞의 `robot == null` 가지를 찾는다.
        var ins = start.Body.Instructions;
        Instruction guard = null, play = null;
        for (int i = 0; i < ins.Count - 1; i++)
        {
            if (ins[i].OpCode != OpCodes.Brfalse &&
                ins[i].OpCode != OpCodes.Brfalse_S) continue;
            var nx = ins[i + 1];
            if (nx.OpCode != OpCodes.Ldarg_0) continue;
            if (ins[i + 2].OpCode != OpCodes.Ldfld ||
                ((FieldReference)ins[i + 2].Operand).Name != "bgmSound") continue;
            guard = ins[i];
            play = nx;
            break;
        }
        if (guard == null)
        {
            Console.WriteLine("GameStart 안에서 BGM 가드를 못 찾았다 "
                              + "(이미 고쳤거나 판이 다르다)");
            return 1;
        }

        var v = new VariableDefinition(clipType);
        start.Body.Variables.Add(v);
        start.Body.InitLocals = true;

        var il = start.Body.GetILProcessor();
        // robot == null 이면 **바로** 무대 BGM 으로 간다 (가지를 뒤집는다)
        il.Replace(guard, Instruction.Create(OpCodes.Brtrue, play));
        // robot != null 인 길: 테마를 찾아 클립만 갈아 끼운다
        il.InsertBefore(play, Instruction.Create(OpCodes.Ldstr, ROBOCA));
        il.InsertBefore(play, Instruction.Create(OpCodes.Call, load));
        il.InsertBefore(play, Instruction.Create(OpCodes.Isinst, clipType));
        il.InsertBefore(play, Instruction.Create(OpCodes.Stloc, v));
        il.InsertBefore(play, Instruction.Create(OpCodes.Ldloc, v));
        il.InsertBefore(play, Instruction.Create(OpCodes.Brfalse, play));
        il.InsertBefore(play, Instruction.Create(OpCodes.Ldarg_0));
        il.InsertBefore(play, Instruction.Create(OpCodes.Ldfld, bgm));
        il.InsertBefore(play, Instruction.Create(OpCodes.Ldloc, v));
        il.InsertBefore(play, Instruction.Create(OpCodes.Callvirt, setClip));

        mod.Write(args[1]);
        Console.WriteLine("로보카 차도 BGM 이 울리게 고쳤다 (테마 {0})", ROBOCA);
        Console.WriteLine("저장: {0}", args[1]);
        return 0;
    }
}
