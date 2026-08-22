using System; using System.Linq; using Mono.Cecil;
class F { static void Main(string[] a){
  var m = ModuleDefinition.ReadModule(a[0]);
  var t = m.GetTypes().First(x => x.FullName == a[1]);
  int i = 0;
  foreach (var f in t.Fields) {
    if (f.IsStatic) continue;
    Console.WriteLine(i + "  " + f.FieldType.Name + "  " + f.Name);
    i++;
  }
}}
