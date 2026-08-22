using System; using System.Linq; using Mono.Cecil;
class E {
  static void Main(string[] a) {
    var asm = AssemblyDefinition.ReadAssembly(a[0]);
    foreach (var t in asm.MainModule.GetTypes()) {
      if (!t.IsEnum) continue;
      if (a.Length > 1 && t.FullName.IndexOf(a[1], StringComparison.OrdinalIgnoreCase) < 0) continue;
      Console.WriteLine("### " + t.FullName);
      foreach (var f in t.Fields.Where(f => f.HasConstant))
        Console.WriteLine("   " + f.Constant + " = " + f.Name);
    }
  }
}
