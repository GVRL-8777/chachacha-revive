// 응답 스키마 추출기 (기존 apidump + typemap 을 Cecil 하나로 통합).
//
// 이 게임은 JSON 키를 ((eType)i).ToString() 으로 만들고 JSONObject.GetXxx 로 읽는다.
// 따라서 각 응답 클래스의 중첩 eType 열거형 = 키 목록이고,
// 게터 IL 의 `ldc.i4 N ... box eType ... callvirt GetXxx` 에서 키→타입을 복원할 수 있다.
//
// 사용법: apischema.exe <dll> <managed> <out.json>
using System; using System.Collections.Generic; using System.Linq; using System.Text;
using Mono.Cecil; using Mono.Cecil.Cil;
static class A {
  static readonly Dictionary<string,string> T = new Dictionary<string,string> {
    {"GetString","string"},{"GetInt","int"},{"GetFloat","float"},{"GetLong","long"},
    {"GetDouble","double"},{"GetBoolean","bool"},{"GetJSONObject","object"},
    {"GetJSONArray","array"},{"GetIntArray","int[]"},{"GetStringArray","string[]"},
    {"GetLongArray","long[]"},{"GetDoubleArray","double[]"},{"GetBooleanArray","bool[]"}};

  static IEnumerable<TypeDefinition> All(TypeDefinition t) {
    yield return t; foreach (var n in t.NestedTypes) foreach (var x in All(n)) yield return x;
  }

  static int Main(string[] a) {
    var r = new DefaultAssemblyResolver(); r.AddSearchDirectory(a[1]);
    var asm = AssemblyDefinition.ReadAssembly(a[0], new ReaderParameters{AssemblyResolver=r});
    var types = asm.MainModule.Types.SelectMany(All).ToList();

    // 클래스 -> 경로 (그 클래스 안의 "/xxx" 리터럴)
    var path = new Dictionary<string,string>();
    foreach (var t in types)
      foreach (var m in t.Methods) {
        if (!m.HasBody) continue;
        foreach (var i in m.Body.Instructions) {
          var s = i.Operand as string;
          if (s != null && s.Length > 4 && s[0] == '/' && !s.Contains(" ") && !path.ContainsKey(t.FullName))
            path[t.FullName] = s;
        }
      }

    var sb = new StringBuilder("{\n");
    int n = 0;
    foreach (var t in types.OrderBy(x => x.FullName)) {
      var et = t.NestedTypes.FirstOrDefault(x => x.IsEnum && x.Name == "eType");
      if (et == null) continue;
      var members = et.Fields.Where(f => f.Name != "value__")
                      .OrderBy(f => Convert.ToInt32(f.Constant))
                      .Select(f => f.Name).ToList();
      // 게터에서 인덱스->타입
      var typed = new Dictionary<int,string>();
      foreach (var m in t.Methods) {
        if (!m.HasBody) continue;
        int last = -1;
        foreach (var i in m.Body.Instructions) {
          if (i.OpCode == OpCodes.Ldc_I4) last = (int)i.Operand;
          else if (i.OpCode == OpCodes.Ldc_I4_S) last = (sbyte)i.Operand;
          else if (i.OpCode.Name.StartsWith("ldc.i4.") && i.OpCode != OpCodes.Ldc_I4_M1) {
            int v; if (int.TryParse(i.OpCode.Name.Substring(7), out v)) last = v;
          } else if (i.OpCode == OpCodes.Call || i.OpCode == OpCodes.Callvirt) {
            var mr = i.Operand as MethodReference;
            if (mr != null && T.ContainsKey(mr.Name) && last >= 0) { typed[last] = T[mr.Name]; last = -1; }
          }
        }
      }
      if (n++ > 0) sb.Append(",\n");
      sb.AppendFormat(" \"{0}\": {{\n  \"path\": {1},\n  \"keys\": [{2}],\n  \"types\": {{",
        t.FullName,
        path.ContainsKey(t.FullName) ? "\"" + path[t.FullName] + "\"" : "null",
        string.Join(", ", members.Where(x => x != "Count" && x != "MaxCount")
                                 .Select(x => "\"" + x + "\"").ToArray()));
      bool first = true;
      foreach (var kv in typed.OrderBy(k => k.Key)) {
        if (kv.Key >= members.Count) continue;
        var key = members[kv.Key];
        if (key == "Count" || key == "MaxCount") continue;
        sb.AppendFormat("{0}\"{1}\": \"{2}\"", first ? "" : ", ", key, kv.Value); first = false;
      }
      sb.Append("}\n }");
    }
    sb.Append("\n}\n");
    System.IO.File.WriteAllText(a[2], sb.ToString(), Encoding.UTF8);
    Console.WriteLine("응답 클래스 {0}개 -> {1}", n, a[2]);
    return 0;
  }
}
