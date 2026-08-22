// 지목한 필드를 읽거나 쓰는 자리를 전부 찾는다.
using System; using System.Linq; using Mono.Cecil; using Mono.Cecil.Cil;
class P {
  static void Main(string[] a) {
    var res = new DefaultAssemblyResolver(); res.AddSearchDirectory(a[1]);
    var asm = AssemblyDefinition.ReadAssembly(a[0], new ReaderParameters { AssemblyResolver = res });
    int n = 0;
    foreach (var t in asm.MainModule.Types)
      foreach (var m in t.Methods) {
        if (!m.HasBody) continue;
        foreach (var i in m.Body.Instructions) {
          var fr = i.Operand as FieldReference;
          if (fr == null || fr.Name != a[2]) continue;
          Console.WriteLine("  {0}::{1}  {2} {3}", t.Name, m.Name, i.OpCode, fr.DeclaringType.Name);
          n++;
        }
      }
    Console.WriteLine("[" + n + "곳]");
  }
}
