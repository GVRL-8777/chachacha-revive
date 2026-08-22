using System; using System.Linq; using Mono.Cecil;
static class FI {
  static int Main(string[] a){
    var mod = ModuleDefinition.ReadModule(a[0]);
    var t = mod.GetTypes().First(x=>x.Name==a[1]);
    foreach(var f in t.Fields)
      Console.WriteLine("{0:X8}  {1,-28} {2}  static={3}",
        f.MetadataToken.ToUInt32(), f.Name, f.FieldType.FullName, f.IsStatic);
    return 0;
  }
}
