// 정규식에 걸리는 열거형들의 값을 찍는다.
using System; using System.Linq; using Mono.Cecil;
class P { static void Main(string[] a) {
  var res = new DefaultAssemblyResolver(); res.AddSearchDirectory(a[1]);
  var asm = AssemblyDefinition.ReadAssembly(a[0], new ReaderParameters { AssemblyResolver = res });
  var rx = new System.Text.RegularExpressions.Regex(a[2]);
  foreach (var t in asm.MainModule.Types.SelectMany(t => new[]{t}.Concat(t.NestedTypes)))
    if (t.IsEnum && rx.IsMatch(t.FullName)) {
      Console.WriteLine("== " + t.FullName);
      foreach (var f in t.Fields.Where(f => f.HasConstant))
        Console.WriteLine("   {0,-24} = {1}", f.Name, f.Constant);
    }
} }
