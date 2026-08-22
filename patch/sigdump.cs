// 메서드 하나의 인자·반환 타입(시그니처)을 찍는다.
using System; using System.Linq; using Mono.Cecil;
static class S { static int Main(string[] a) {
  var r = new DefaultAssemblyResolver(); r.AddSearchDirectory(a[1]);
  var asm = AssemblyDefinition.ReadAssembly(a[0], new ReaderParameters{AssemblyResolver=r});
  var t = asm.MainModule.GetType(a[2]);
  foreach (var m in t.Methods.Where(m => m.Name == a[3]))
    Console.WriteLine("{0}({1}) -> {2}", m.Name,
      string.Join(", ", m.Parameters.Select(p => p.ParameterType.FullName).ToArray()),
      m.ReturnType.FullName);
  return 0; } }
