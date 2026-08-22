// 중국판(5577.com.cjenm.chachachacn) 패처.
//
// 이 배포판은 CDN(AssetBundleManager)이 없어 자산이 전부 로컬에 있다.
// 막히는 곳은 360/NetmarbleS 소셜 플러그인 초기화 실패 팝업뿐이므로,
// 타이틀에서 소셜 단계를 건너뛰고 게스트 레이스로 바로 들어가게 한다.
// (Generic_Title::OnGuestPlayOk 가 끝에서 Application.LoadLevelAsync("Game") 를 호출한다)
//
// 사용법: patchcn.exe <in.dll> <out.dll> <managed폴더> [지연프레임]
using System;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

class P
{
    static void Main(string[] a)
    {
        int delay = a.Length > 3 ? int.Parse(a[3]) : 150;
        var rp = new ReaderParameters();
        var res = new DefaultAssemblyResolver();
        res.AddSearchDirectory(a[2]);
        rp.AssemblyResolver = res;
        var asm = AssemblyDefinition.ReadAssembly(a[0], rp);
        var mod = asm.MainModule;

        var title = mod.Types.First(t => t.Name == "Generic_Title");
        var update = title.Methods.First(m => m.Name == "Update");
        var guestOk = title.Methods.First(m => m.Name == "OnGuestPlayOk");

        // 프레임 카운터. UI 가 준비되기 전에 부르면 m_GuestPlayButton 이 null 이라 죽는다.
        var fld = new FieldDefinition("__cnFrames",
            FieldAttributes.Public | FieldAttributes.Static, mod.TypeSystem.Int32);
        title.Fields.Add(fld);

        var il = update.Body.GetILProcessor();
        var first = update.Body.Instructions[0];
        Action<Instruction> put = x => il.InsertBefore(first, x);

        // if (__cnFrames >= 0) { if (++__cnFrames == delay) { __cnFrames = -1; OnGuestPlayOk(); } }
        put(Instruction.Create(OpCodes.Ldsfld, fld));
        put(Instruction.Create(OpCodes.Ldc_I4_0));
        put(Instruction.Create(OpCodes.Blt, first));
        put(Instruction.Create(OpCodes.Ldsfld, fld));
        put(Instruction.Create(OpCodes.Ldc_I4_1));
        put(Instruction.Create(OpCodes.Add));
        put(Instruction.Create(OpCodes.Stsfld, fld));
        put(Instruction.Create(OpCodes.Ldsfld, fld));
        put(Instruction.Create(OpCodes.Ldc_I4, delay));
        put(Instruction.Create(OpCodes.Bne_Un, first));
        put(Instruction.Create(OpCodes.Ldc_I4_M1));
        put(Instruction.Create(OpCodes.Stsfld, fld));
        put(Instruction.Create(OpCodes.Ldarg_0));
        put(Instruction.Create(OpCodes.Call, guestOk));
        Console.WriteLine("  Generic_Title::Update 진입부 -> " + delay + "프레임 뒤 OnGuestPlayOk (소셜 건너뜀)");

        asm.Write(a[1]);
        Console.WriteLine("출력: " + a[1]);
    }
}
