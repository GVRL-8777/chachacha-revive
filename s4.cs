using System; using System.Collections.Generic; using System.Linq;
using Mono.Cecil; using Mono.Cecil.Cil;
class S4 { static void Main(string[] a){
  var res=new DefaultAssemblyResolver(); res.AddSearchDirectory(a[1]);
  var m=ModuleDefinition.ReadModule(a[0], new ReaderParameters{AssemblyResolver=res});
  Func<TypeDefinition,IEnumerable<TypeDefinition>> all=null;
  all=x=>new[]{x}.Concat(x.NestedTypes.SelectMany(y=>all(y)));
  foreach(var t in m.Types.SelectMany(x=>all(x))){
    if(t.FullName.Split('/')[0] != a[2]) continue;
    foreach(var me in t.Methods){
      if(!me.HasBody) continue;
      var ins=me.Body.Instructions;
      for(int i=0;i<ins.Count;i++){
        var mr=ins[i].Operand as MethodReference;
        if(mr==null||!mr.FullName.Contains(a[3])) continue;
        Console.WriteLine("=== "+t.FullName+"::"+me.Name);
        for(int k=Math.Max(0,i-10);k<Math.Min(ins.Count,i+2);k++)
          Console.WriteLine("   "+ins[k]);
      }
    }
  }
}}
