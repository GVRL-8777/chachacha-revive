using System; using System.Collections.Generic; using System.Linq;
using Mono.Cecil; using Mono.Cecil.Cil;
class T { static void Main(string[] a){
  var res=new DefaultAssemblyResolver(); res.AddSearchDirectory(a[1]);
  var m=ModuleDefinition.ReadModule(a[0], new ReaderParameters{AssemblyResolver=res});
  Func<TypeDefinition,IEnumerable<TypeDefinition>> all=null;
  all=x=>new[]{x}.Concat(x.NestedTypes.SelectMany(y=>all(y)));
  foreach(var t in m.Types.SelectMany(x=>all(x))){
    if(t.FullName.Split('/')[0] != a[2]) continue;
    foreach(var me in t.Methods){
      Console.WriteLine("=== "+t.FullName+"::"+me.Name);
      if(!me.HasBody){ Console.WriteLine("   (본문 없음)"); continue; }
      foreach(var ins in me.Body.Instructions) Console.WriteLine("   "+ins);
    }
    foreach(var f in t.Fields) Console.WriteLine("--- field "+f.FieldType.Name+" "+f.Name);
  }
}}
