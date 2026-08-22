using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System.Text;

namespace chachacha_server.HTTP
{
    /// <summary>
    /// 미구현 엔드포인트로 들어오는 요청을 수집하고, 관측된 JSON에서 요청 스키마를 추론한다.
    /// 목적: 남은 엔드포인트들의 요청 스펙을 실물 트래픽으로 확보하는 것.
    /// </summary>
    internal static class SchemaCollector
    {
        private static readonly object gate = new object();
        private static readonly Dictionary<string, EndpointRecord> endpoints = new();
        private static string captureDir = "capture";
        private static int totalObservations = 0;

        /// <summary>필드 하나에 대해 관측된 타입/횟수/샘플</summary>
        internal class FieldRecord
        {
            public SortedSet<string> types = new();
            public int seen = 0;
            public bool nullable = false;
            public string? sample;
        }

        internal class EndpointRecord
        {
            public string path = "";
            public SortedSet<string> methods = new();
            public bool implemented = false;
            public int observations = 0;
            public int decryptedOk = 0;
            public int decryptFailed = 0;
            public int emptyBody = 0;
            /// <summary>평탄화된 필드 경로 -> 관측 정보. 예: "infoReq.accountSeq"</summary>
            public SortedDictionary<string, FieldRecord> fields = new();
            public List<string> rawSamples = new();
        }

        public static void Init(string dir)
        {
            lock (gate)
            {
                captureDir = dir;
                Directory.CreateDirectory(captureDir);
                Load();
            }
        }

        /// <summary>요청 1건 관측.</summary>
        /// <param name="path">정규화된 경로</param>
        /// <param name="plainJson">복호화(또는 평문) 성공 시 JSON 문자열, 실패 시 null</param>
        public static void Observe(string path, string method, byte[] rawBody, string? plainJson, bool implemented)
        {
            lock (gate)
            {
                totalObservations++;

                if (!endpoints.TryGetValue(path, out var rec))
                {
                    rec = new EndpointRecord { path = path };
                    endpoints[path] = rec;
                }
                rec.implemented = implemented;
                rec.methods.Add(method);
                rec.observations++;

                if (rawBody.Length == 0)
                {
                    rec.emptyBody++;
                }
                else if (plainJson == null)
                {
                    rec.decryptFailed++;
                    // 복호화 실패해도 원문은 남긴다. 나중에 키가 확보되면 재처리 가능.
                    if (rec.rawSamples.Count < 3)
                        rec.rawSamples.Add(Encoding.ASCII.GetString(rawBody));
                }
                else
                {
                    rec.decryptedOk++;
                    MergeSchema(rec, plainJson);
                    if (rec.rawSamples.Count < 3)
                        rec.rawSamples.Add(plainJson);
                }

                // 원본 관측을 append-only 로 남겨 재분석/리플레이가 가능하게 한다.
                AppendJsonl(path, method, rawBody, plainJson, implemented);

                if (!implemented)
                {
                    Console.ForegroundColor = ConsoleColor.Yellow;
                    Console.WriteLine($"[MISSING] {method} {path}  (관측 {rec.observations}회, 필드 {rec.fields.Count}개)");
                    Console.ResetColor();
                }

                // 미구현 엔드포인트 관측은 이 도구의 핵심 산출물이므로 즉시 저장한다.
                // (구현된 경로는 10건마다 저장해 디스크 I/O 를 아낀다)
                if (!implemented || totalObservations % 10 == 0) Save();
            }
        }

        private static void MergeSchema(EndpointRecord rec, string json)
        {
            JToken root;
            try { root = JToken.Parse(json); }
            catch { return; }

            foreach (var (key, token) in Flatten(root, ""))
            {
                if (!rec.fields.TryGetValue(key, out var f))
                {
                    f = new FieldRecord();
                    rec.fields[key] = f;
                }
                f.seen++;
                if (token.Type == JTokenType.Null) f.nullable = true;
                else
                {
                    f.types.Add(JsonTypeName(token));
                    if (f.sample == null)
                    {
                        var s = token.ToString();
                        f.sample = s.Length > 60 ? s.Substring(0, 60) + "..." : s;
                    }
                }
            }
        }

        /// <summary>중첩 JSON을 "a.b[].c" 형태의 평탄한 경로로 펼친다.</summary>
        private static IEnumerable<(string, JToken)> Flatten(JToken token, string prefix)
        {
            switch (token.Type)
            {
                case JTokenType.Object:
                    foreach (var prop in (JObject)token)
                    {
                        string key = prefix.Length == 0 ? prop.Key : prefix + "." + prop.Key;
                        if (prop.Value == null) continue;
                        if (prop.Value.Type == JTokenType.Object || prop.Value.Type == JTokenType.Array)
                        {
                            yield return (key, prop.Value);
                            foreach (var r in Flatten(prop.Value, key)) yield return r;
                        }
                        else yield return (key, prop.Value);
                    }
                    break;
                case JTokenType.Array:
                    // 배열 원소는 동일 스키마로 간주하고 "[]" 로 합친다.
                    foreach (var item in (JArray)token)
                        foreach (var r in Flatten(item, prefix + "[]")) yield return r;
                    break;
            }
        }

        private static string JsonTypeName(JToken t) => t.Type switch
        {
            JTokenType.Integer => "int",
            JTokenType.Float => "float",
            JTokenType.String => "string",
            JTokenType.Boolean => "bool",
            JTokenType.Date => "date",
            JTokenType.Object => "object",
            JTokenType.Array => "array",
            _ => t.Type.ToString().ToLower()
        };

        private static void AppendJsonl(string path, string method, byte[] rawBody, string? plainJson, bool implemented)
        {
            try
            {
                var entry = new
                {
                    ts = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff"),
                    path,
                    method,
                    implemented,
                    bodyLen = rawBody.Length,
                    raw = rawBody.Length > 0 ? Encoding.ASCII.GetString(rawBody) : null,
                    json = plainJson
                };
                File.AppendAllText(Path.Combine(captureDir, "requests.jsonl"),
                    JsonConvert.SerializeObject(entry) + Environment.NewLine, Encoding.UTF8);
            }
            catch (Exception e) { Console.WriteLine("[collector] jsonl 기록 실패: " + e.Message); }
        }

        private static void Load()
        {
            string f = Path.Combine(captureDir, "schema.json");
            if (!File.Exists(f)) return;
            try
            {
                var loaded = JsonConvert.DeserializeObject<Dictionary<string, EndpointRecord>>(File.ReadAllText(f));
                if (loaded != null)
                {
                    foreach (var kv in loaded) endpoints[kv.Key] = kv.Value;
                    Console.WriteLine($"[collector] 기존 스키마 {endpoints.Count}개 엔드포인트 로드");
                }
            }
            catch (Exception e) { Console.WriteLine("[collector] 스키마 로드 실패: " + e.Message); }
        }

        public static void Save()
        {
            lock (gate)
            {
                try
                {
                    Directory.CreateDirectory(captureDir);
                    File.WriteAllText(Path.Combine(captureDir, "schema.json"),
                        JsonConvert.SerializeObject(endpoints, Formatting.Indented), Encoding.UTF8);
                    File.WriteAllText(Path.Combine(captureDir, "report.md"), BuildReport(), Encoding.UTF8);
                }
                catch (Exception e) { Console.WriteLine("[collector] 저장 실패: " + e.Message); }
            }
        }

        public static string BuildReport()
        {
            var sb = new StringBuilder();
            var impl = endpoints.Values.Where(e => e.implemented).OrderBy(e => e.path).ToList();
            var miss = endpoints.Values.Where(e => !e.implemented).OrderBy(e => e.path).ToList();

            sb.AppendLine("# 차차차 서버 - 요청 스키마 수집 리포트");
            sb.AppendLine();
            sb.AppendLine($"생성: {DateTime.Now:yyyy-MM-dd HH:mm:ss}  |  총 관측 {endpoints.Values.Sum(e => e.observations)}건");
            sb.AppendLine($"구현됨 {impl.Count}개 / 미구현 {miss.Count}개 엔드포인트 관측");
            sb.AppendLine();

            sb.AppendLine("## 미구현 엔드포인트 (작업 대상)");
            sb.AppendLine();
            if (miss.Count == 0) sb.AppendLine("_아직 없음._");
            foreach (var e in miss) AppendEndpoint(sb, e);

            sb.AppendLine();
            sb.AppendLine("## 구현된 엔드포인트 (관측된 요청 스키마)");
            sb.AppendLine();
            if (impl.Count == 0) sb.AppendLine("_아직 없음._");
            foreach (var e in impl) AppendEndpoint(sb, e);

            return sb.ToString();
        }

        private static void AppendEndpoint(StringBuilder sb, EndpointRecord e)
        {
            sb.AppendLine($"### `{e.path}`");
            sb.AppendLine();
            sb.AppendLine($"- 메서드: {string.Join(", ", e.methods)}");
            sb.AppendLine($"- 관측 {e.observations}회 (복호화 성공 {e.decryptedOk} / 실패 {e.decryptFailed} / 빈 바디 {e.emptyBody})");
            if (e.fields.Count > 0)
            {
                sb.AppendLine();
                sb.AppendLine("| 필드 | 타입 | 관측 | 샘플 |");
                sb.AppendLine("|---|---|---|---|");
                foreach (var kv in e.fields)
                {
                    string types = string.Join("\\|", kv.Value.types);
                    if (kv.Value.nullable) types += "?";
                    string sample = (kv.Value.sample ?? "").Replace("|", "\\|").Replace("\n", " ");
                    sb.AppendLine($"| `{kv.Key}` | {types} | {kv.Value.seen} | `{sample}` |");
                }
            }
            if (e.rawSamples.Count > 0)
            {
                sb.AppendLine();
                sb.AppendLine("<details><summary>원문 샘플</summary>");
                sb.AppendLine();
                sb.AppendLine("```");
                foreach (var s in e.rawSamples) sb.AppendLine(s.Length > 800 ? s.Substring(0, 800) + "..." : s);
                sb.AppendLine("```");
                sb.AppendLine("</details>");
            }
            sb.AppendLine();
        }

        public static void PrintSummary()
        {
            lock (gate)
            {
                var miss = endpoints.Values.Where(e => !e.implemented).OrderBy(e => e.path).ToList();
                Console.WriteLine();
                Console.WriteLine("==================== 수집 요약 ====================");
                Console.WriteLine($"관측 엔드포인트 {endpoints.Count}개 / 총 요청 {endpoints.Values.Sum(e => e.observations)}건");
                if (miss.Count > 0)
                {
                    Console.WriteLine($"미구현 {miss.Count}개:");
                    foreach (var e in miss)
                        Console.WriteLine($"   {e.path}  (관측 {e.observations}, 필드 {e.fields.Count})");
                }
                Console.WriteLine($"저장 위치: {Path.GetFullPath(captureDir)}");
                Console.WriteLine("===================================================");
            }
        }
    }
}
