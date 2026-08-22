using System; using System.Linq; using Mono.Cecil;
static class F { static int Main(string[] a) {
  var r = new DefaultAssemblyResolver(); r.AddSearchDirectory(a[1]);
  var asm = AssemblyDefinition.ReadAssembly(a[0], new ReaderParameters{AssemblyResolver=r});
  var t = asm.MainModule.GetType(a[2]);
  foreach (var f in t.Fields) Console.WriteLine("{0,-34} {1}", f.Name, f.FieldType.FullName);
  return 0; } }
