// DLL 안의 ldstr 리터럴을 통째로 치환한다 (Cecil 이 재작성하므로 길이 제약 없음).
// 사용법: strswap.exe <in.dll> <out.dll> <managed폴더> <from1> <to1> [<from2> <to2> ...]
using System; using System.Linq; using Mono.Cecil; using Mono.Cecil.Cil;
static class S {
  static int Main(string[] a) {
    if (a.Length < 5 || (a.Length - 3) % 2 != 0) {
      Console.Error.WriteLine("usage: strswap <in.dll> <out.dll> <managed> <from> <to> [...]");
      return 2;
    }
    var r = new DefaultAssemblyResolver(); r.AddSearchDirectory(a[2]);
    var asm = AssemblyDefinition.ReadAssembly(a[0], new ReaderParameters{AssemblyResolver=r});
    int n = 0;
    for (int p = 3; p + 1 < a.Length; p += 2) {
      string from = a[p], to = a[p + 1];
      int c = 0;
      foreach (var t in asm.MainModule.Types)
        foreach (var m in t.Methods) {
          if (!m.HasBody) continue;
          foreach (var i in m.Body.Instructions) {
            if (i.OpCode != OpCodes.Ldstr) continue;
            var s = i.Operand as string;
            if (s == null || !s.Contains(from)) continue;
            i.Operand = s.Replace(from, to);
            c++;
          }
        }
      Console.WriteLine("  \"{0}\" -> \"{1}\"  ({2}곳)", from, to, c);
      n += c;
    }
    asm.Write(a[1]);
    Console.WriteLine("총 {0}곳 치환 -> {1}", n, a[1]);
    return 0;
  }
}
