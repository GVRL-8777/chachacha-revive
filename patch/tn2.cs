using System; using System.Linq; using Mono.Cecil;
class T2 { static void Main(string[] a){
  var m = ModuleDefinition.ReadModule(a[0]);
  Func<TypeDefinition, System.Collections.Generic.IEnumerable<TypeDefinition>> all=null;
  all = x => new[]{x}.Concat(x.NestedTypes.SelectMany(y=>all(y)));
  foreach (var t in m.Types.SelectMany(x=>all(x)))
    if (t.IsEnum && t.Name.ToLower().Contains(a[1].ToLower()))
      Console.WriteLine("  " + t.FullName);
}}
