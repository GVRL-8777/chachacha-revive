// 로컬 전용 차차차 — 서버 없이 폰 안에서 다 끝낸다.
//
// 게임 코드는 그대로 두고 통신 관문만 갈아 끼운다(localfix.exe 가 한다).
//
//    Generic_HTTP.SendPacket  ──▶  Note(url, body)      요청을 받아 두고
//         │ WWW 를 만들지 않는다        │
//         ▼                             ▼
//    WaitForXxx 코루틴          ◀──  Text(www)          응답 JSON 을 돌려준다
//         │                             │
//         ▼                             ▼
//    기존 파싱·화면 그대로         chasave.json (기기 안)
//
// 응답 뼈대와 가격표는 손으로 옮기지 않았다. ChaLocalData.cs 가
// 사설 서버(chacnserver.py)에서 그대로 떠 온 것이다.
using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

public static class ChaLocal
{
    // ================================================================ 미니 JSON
    // System.Web 같은 건 이 빌드에 없다. 필요한 만큼만 직접 짠다.
    sealed class Jp
    {
        string s;
        int i;

        public static object Parse(string t)
        {
            if (t == null) return null;
            Jp j = new Jp();
            j.s = t;
            j.i = 0;
            try { return j.Val(); }
            catch { return null; }
        }

        void Ws()
        {
            while (i < s.Length && (s[i] == ' ' || s[i] == '\t'
                   || s[i] == '\n' || s[i] == '\r')) i++;
        }

        object Val()
        {
            Ws();
            if (i >= s.Length) return null;
            char c = s[i];
            if (c == '{') return Obj();
            if (c == '[') return Arr();
            if (c == '"') return Str();
            if (c == 't') { i += 4; return true; }
            if (c == 'f') { i += 5; return false; }
            if (c == 'n') { i += 4; return null; }
            return Num();
        }

        Hashtable Obj()
        {
            Hashtable h = new Hashtable();
            i++;                                     // '{'
            Ws();
            if (i < s.Length && s[i] == '}') { i++; return h; }
            while (i < s.Length)
            {
                Ws();
                string k = Str();
                Ws();
                if (i < s.Length && s[i] == ':') i++;
                h[k] = Val();
                Ws();
                if (i < s.Length && s[i] == ',') { i++; continue; }
                if (i < s.Length && s[i] == '}') { i++; break; }
                break;
            }
            return h;
        }

        ArrayList Arr()
        {
            ArrayList a = new ArrayList();
            i++;                                     // '['
            Ws();
            if (i < s.Length && s[i] == ']') { i++; return a; }
            while (i < s.Length)
            {
                a.Add(Val());
                Ws();
                if (i < s.Length && s[i] == ',') { i++; continue; }
                if (i < s.Length && s[i] == ']') { i++; break; }
                break;
            }
            return a;
        }

        string Str()
        {
            StringBuilder b = new StringBuilder();
            if (i < s.Length && s[i] == '"') i++;
            while (i < s.Length && s[i] != '"')
            {
                char c = s[i++];
                if (c != '\\') { b.Append(c); continue; }
                if (i >= s.Length) break;
                char e = s[i++];
                if (e == 'n') b.Append('\n');
                else if (e == 't') b.Append('\t');
                else if (e == 'r') b.Append('\r');
                else if (e == 'b') b.Append('\b');
                else if (e == 'f') b.Append('\f');
                else if (e == 'u')
                {
                    int cp = 0;
                    for (int k = 0; k < 4 && i < s.Length; k++, i++)
                    {
                        char d = s[i];
                        int dv = d >= '0' && d <= '9' ? d - '0'
                               : (d >= 'a' && d <= 'f' ? d - 'a' + 10
                               : (d >= 'A' && d <= 'F' ? d - 'A' + 10 : 0));
                        cp = cp * 16 + dv;
                    }
                    b.Append((char)cp);
                }
                else b.Append(e);
            }
            if (i < s.Length) i++;                   // 닫는 따옴표
            return b.ToString();
        }

        object Num()
        {
            int st = i;
            bool real = false;
            while (i < s.Length)
            {
                char c = s[i];
                if (c == '.' || c == 'e' || c == 'E') real = true;
                else if (!(char.IsDigit(c) || c == '-' || c == '+')) break;
                i++;
            }
            string t = s.Substring(st, i - st);
            if (real)
            {
                double dv;
                double.TryParse(t, NumberStyles.Float,
                                CultureInfo.InvariantCulture, out dv);
                return dv;
            }
            long lv;
            long.TryParse(t, out lv);
            return lv;
        }
    }

    static void Wr(StringBuilder b, object v)
    {
        if (v == null) { b.Append("null"); return; }
        if (v is string) { WrStr(b, (string)v); return; }
        if (v is bool) { b.Append(((bool)v) ? "true" : "false"); return; }
        Hashtable h = v as Hashtable;
        if (h != null)
        {
            b.Append('{');
            bool first = true;
            foreach (DictionaryEntry e in h)
            {
                if (!first) b.Append(',');
                first = false;
                WrStr(b, Convert.ToString(e.Key));
                b.Append(':');
                Wr(b, e.Value);
            }
            b.Append('}');
            return;
        }
        ArrayList a = v as ArrayList;
        if (a != null)
        {
            b.Append('[');
            for (int k = 0; k < a.Count; k++)
            {
                if (k > 0) b.Append(',');
                Wr(b, a[k]);
            }
            b.Append(']');
            return;
        }
        if (v is double || v is float)
        {
            b.Append(Convert.ToDouble(v, CultureInfo.InvariantCulture)
                     .ToString("R", CultureInfo.InvariantCulture));
            return;
        }
        // 나머지는 전부 정수로 낸다. 소수점이 붙으면 클라이언트 게터가 버린다.
        b.Append(Convert.ToInt64(v).ToString(CultureInfo.InvariantCulture));
    }

    static void WrStr(StringBuilder b, string s)
    {
        b.Append('"');
        for (int k = 0; k < s.Length; k++)
        {
            char c = s[k];
            if (c == '"') b.Append("\\\"");
            else if (c == '\\') b.Append("\\\\");
            else if (c == '\n') b.Append("\\n");
            else if (c == '\r') b.Append("\\r");
            else if (c == '\t') b.Append("\\t");
            else if (c < ' ') b.Append("\\u").Append(((int)c).ToString("x4"));
            else b.Append(c);
        }
        b.Append('"');
    }

    static string Write(object v)
    {
        StringBuilder b = new StringBuilder(512);
        Wr(b, v);
        return b.ToString();
    }

    static object Copy(object v)
    {
        Hashtable h = v as Hashtable;
        if (h != null)
        {
            Hashtable o = new Hashtable();
            foreach (DictionaryEntry e in h) o[e.Key] = Copy(e.Value);
            return o;
        }
        ArrayList a = v as ArrayList;
        if (a != null)
        {
            ArrayList o = new ArrayList(a.Count);
            for (int k = 0; k < a.Count; k++) o.Add(Copy(a[k]));
            return o;
        }
        return v;
    }

    // ---------------------------------------------------------- 꺼내 쓰기
    static object Get(Hashtable h, string k)
    {
        return (h == null || !h.ContainsKey(k)) ? null : h[k];
    }

    static string GetS(Hashtable h, string k)
    {
        object v = Get(h, k);
        return v == null ? "" : Convert.ToString(v);
    }

    static long GetL(Hashtable h, string k)
    {
        object v = Get(h, k);
        if (v == null || v is string || v is bool) return 0;
        try { return Convert.ToInt64(v); }
        catch { return 0; }
    }

    static int GetI(Hashtable h, string k) { return (int)GetL(h, k); }

    static bool GetB(Hashtable h, string k)
    {
        object v = Get(h, k);
        return v is bool && (bool)v;
    }

    static Hashtable GetH(Hashtable h, string k) { return Get(h, k) as Hashtable; }
    static ArrayList GetA(Hashtable h, string k) { return Get(h, k) as ArrayList; }

    // ================================================================ 자료
    static Hashtable D;                 // ChaLocalData 에서 읽은 표 전체
    static Hashtable Skel;
    static Hashtable Save;              // 세이브 파일 내용 (chastate.json 모양)
    static string SavePath;
    static bool ready;

    // 살아 있는 값들. 사설 서버의 PLAYER/CAR_CLASS/... 와 같은 자리다.
    static string nickName = "Racer";
    static long gold, trophy, tire;
    static int carNo = 1, carSeq = 2, characterNo = 1;
    static long bestScore, bestScoreHurdle, prevScore, maxDistance, playCount;
    static int inviteCnt;
    static Hashtable carClass = new Hashtable();   // int -> string
    static Hashtable owned = new Hashtable();      // int -> true
    static Hashtable tune = new Hashtable();       // "no|carAccel" -> int
    static Hashtable drivers = new Hashtable();    // int -> true
    static ArrayList presents = new ArrayList();
    static Hashtable items = new Hashtable();     // 코드(1~7) -> 개수
    // 스킬은 **차마다** 붙는다. 열쇠는 차번호*1000 + 스킬번호 다.
    // 문자열 열쇠를 쓰면 되돌릴 때 Convert.ToInt64(string) 이 필요한데,
    // 유니티의 깎인 mscorlib 에는 그게 없다(기기에서 죽는다).
    static Hashtable skills = new Hashtable();

    static long SkillKey(long car, long no) { return car * 1000L + no; }
    static Hashtable nameToNo = new Hashtable();
    static Hashtable noToName = new Hashtable();
    static Hashtable startClass = new Hashtable(); // name -> class
    static long maxGold = 999999999, maxTrophy = 999999999, maxTire = 998;
    static int driverCount = 12;
    static int raceValue;
    static string cryptoKey = "", initVector = "";
    static Hashtable pendingBill = new Hashtable();
    // 이 빌드의 System.Random 에는 Next() 밖에 없다. 나머지는 직접 만든다.
    static System.Random rnd = new System.Random();

    static int NextInt(int lo, int hi)          // [lo, hi)
    {
        if (hi <= lo) return lo;
        return lo + (rnd.Next() % (hi - lo));
    }
    static string lastSaved = "";

    // CRSystem/eItemCode 그대로. 값은 클라이언트 Generic_ShopMain/eItemCost 와
    // 같아야 화면과 어긋나지 않습니다(골드).
    static readonly int[] ITEM_CODES = { 1, 2, 3, 4, 5, 6, 7 };
    static readonly string[] ITEM_NAME = {
        "BestOil", "Nos", "FrontSensor", "ToolBox",
        "OneShot", "Emergency", "Turbo" };
    static readonly int[] ITEM_COST = { 900, 800, 700, 600, 1000, 1500, 300 };
    const int ITEM_MAX = 99;

    // 캐릭터 값은 DB 에 없고 **캐릭터 화면 카드에 박혀 있습니다.**
    // 화면 값과 실제로 깎는 값이 어긋나면 안 되므로 그대로 옮겼습니다.
    //   1 도 강현 = 기본(무료) · 2 Sarah Cha 60 · 3 빈 경유 40 · 4 나 연비 50
    //   5~12 = 120
    // 골드로도 살 수 있고, 환율은 게임 교환표대로 트로피 1 = 500 골드입니다.
    static readonly int[] DRIVER_COST = { 0, 60, 40, 50 };   // 1~4번
    const int DRIVER_COST_DEFAULT = 120;

    static int DriverCost(int no)
    {
        if (no >= 1 && no <= DRIVER_COST.Length) return DRIVER_COST[no - 1];
        return DRIVER_COST_DEFAULT;
    }

    static int ItemAt(int code)
    {
        object v = items[code];
        return v == null ? 0 : (int)Convert.ToInt64(v);
    }

    /// 겹판을 띄웁니다. 프리팹을 안 건드리는 길이라 이렇게 갑니다.
    static bool overlayUp;

    /// 겹판은 **어느 판에서든** 띄운다.
    ///
    /// 예전에는 `Boot()` 안에서만 띄웠다. 그런데 서버판은 `Boot()` 을 아예
    /// 안 부르므로 겹판이 안 나왔고, 그러면 한 번 서버로 간 뒤에는 게임
    /// 안에서 로컬로 돌아올 길이 없었다. 실기에서 그렇게 됐다.
    public static void Ensure()
    {
        if (overlayUp) return;
        overlayUp = true;
        MakeOverlay();
    }

    static void MakeOverlay()
    {
        try
        {
            GameObject go = new GameObject("ChaLocalUI");
            go.AddComponent(typeof(ChaLocalUI));
            UnityEngine.Object.DontDestroyOnLoad(go);
            Debug.Log("[ChaLocal] 겹판을 띄웠습니다");
        }
        catch (Exception e)
        {
            Debug.Log("[ChaLocal] 겹판 실패: " + e.Message);
        }
    }

    static void Boot()
    {
        if (ready) return;
        ready = true;
        Ensure();
        D = Jp.Parse(ChaLocalData.Json()) as Hashtable;
        if (D == null) D = new Hashtable();
        Skel = GetH(D, "skel");
        if (Skel == null) Skel = new Hashtable();
        maxGold = GetL(D, "maxGold");
        maxTrophy = GetL(D, "maxTrophy");
        maxTire = GetL(D, "maxTire");
        driverCount = GetI(D, "driverCount");
        if (driverCount <= 0) driverCount = 12;

        ArrayList cars = GetA(D, "cars");
        if (cars != null)
        {
            for (int k = 0; k < cars.Count; k++)
            {
                ArrayList row = cars[k] as ArrayList;
                if (row == null || row.Count < 3) continue;
                int no = (int)Convert.ToInt64(row[0]);
                string nm = Convert.ToString(row[1]);
                nameToNo[nm] = no;
                noToName[no] = nm;
                startClass[nm] = Convert.ToString(row[2]);
            }
        }

        SavePath = SaveDir() + "/chasave.json";
        Debug.Log("[ChaLocal] 세이브 자리: " + SavePath);
        LoadSave();
    }

    // ---------------------------------------------------------- 세이브 파일
    // 런처가 adb 로 넣고 빼려면 세이브가 **바깥 저장소**에 있어야 한다.
    //
    // 갓 설치한 기기에서는 Application.persistentDataPath 가
    // `/data/user/0/<pkg>/files` — 앱 내부 — 로 잡힌다. 거기는 루팅 없이
    // 손댈 수 없다. (폴더가 남아 있던 기기에서는 바깥으로 잡혀서 여태
    // 이 문제가 안 드러났다.) 그래서 바깥 자리를 먼저 만들어 보고,
    // 정말 못 쓸 때만 원래 자리로 물러선다.
    // 패키지 이름은 프리셋마다 다르다(부자판·거지판이 따로 깔린다). 그래서
    // 여기 박아 두지 않고 구워 넣은 값을 쓴다. JNI 로 받는 길이 먼저이고
    // 이건 물러설 자리라, 남의 앱 폴더를 가리키지 않게만 하면 된다.
    static string ExtDir()
    {
        string p = ChaLocalData.Pkg();
        if (p == null || p.Length == 0) p = "com.cjenm.chachacharevive";
        return "/storage/emulated/0/Android/data/" + p + "/files";
    }

    /// 바깥 저장소의 제 몫 폴더를 **시스템에게** 만들게 한다.
    ///
    /// `/storage/emulated/0/Android/data/<패키지>` 는 앱이 직접 mkdir 할 수
    /// 없다("Access to the path … is denied"). 안드로이드가
    /// getExternalCacheDir() 같은 것을 통해서만 만들어 준다. 그래서 JNI 로
    /// 캐시 폴더를 한 번 받아 그 옆에 files 를 만든다.
    /// (getExternalFilesDir 은 인자가 null String 이라 JNI 서명 해석이
    ///  까다롭다. 인자 없는 캐시 쪽이 안전하다.)
    static string ExternalFilesDir()
    {
        try
        {
            using (AndroidJavaClass up =
                   new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
            using (AndroidJavaObject act =
                   up.GetStatic<AndroidJavaObject>("currentActivity"))
            {
                if (act == null) return null;
                using (AndroidJavaObject cache =
                       act.Call<AndroidJavaObject>("getExternalCacheDir"))
                {
                    if (cache == null) return null;
                    string cp = cache.Call<string>("getAbsolutePath");
                    string pkg = Path.GetDirectoryName(cp);
                    if (pkg == null) return null;
                    string files = pkg + "/files";   // 안드로이드 경로는 늘 슬래시다
                    if (!Directory.Exists(files)) Directory.CreateDirectory(files);
                    return files;
                }
            }
        }
        catch (Exception e)
        {
            Debug.Log("[ChaLocal] 바깥 폴더 요청 실패: " + e.Message);
        }
        return null;
    }

    static bool Writable(string dir)
    {
        try
        {
            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
            string probe = dir + "/.chaprobe";
            using (FileStream fs = new FileStream(probe, FileMode.Create,
                                                  FileAccess.Write))
                fs.WriteByte(49);
            File.Delete(probe);
            return true;
        }
        catch { return false; }
    }

    // ======================================================== 어느 판인가
    //
    // 예전에는 APK 를 둘로 갈랐다 — 서버판과 로컬판. 이제 **한 벌** 안에
    // 둘 다 들어 있고, 파일 한 줄이 어느 쪽으로 돌지 정한다.
    //
    //   chamode.txt  안이 "server" 면 서버판, 그 밖(없어도)이면 로컬판.
    //
    // 세이브 옆에 두므로 런처가 adb 로 갈아 끼울 수 있고, 게임 안 겹판에서도
    // 바꾼다. 바꾼 뒤에는 앱을 껐다 켜야 한다 — 갈고리가 켤 때 한 번만
    // 읽는 자리들이 있다.
    public const string LOCAL = "local";
    public const string SERVER = "server";

    static string saveDir;
    static string mode;

    /// 세이브와 판 표시가 놓이는 자리. 한 번만 찾는다.
    public static string SaveDir()
    {
        if (saveDir == null) saveDir = PickSaveDir();
        return saveDir;
    }

    public static string ModePath { get { return SaveDir() + "/chamode.txt"; } }

    /// 지금 판. **Boot 보다 먼저** 불릴 수 있으므로 혼자 설 수 있어야 한다.
    public static string Mode
    {
        get
        {
            if (mode == null)
            {
                mode = LOCAL;
                try
                {
                    string p = ModePath;
                    if (File.Exists(p))
                    {
                        string v = ReadText(p).Trim().ToLower();
                        if (v == SERVER) mode = SERVER;
                    }
                }
                catch (Exception) { }
                Debug.Log("[ChaLocal] 판: " + mode);
            }
            return mode;
        }
    }

    /// 로컬판인가. **갈고리들이 이걸 보고 갈린다.**
    public static bool IsLocal() { return Mode == LOCAL; }

    /// 판을 바꾼다. 다음에 켤 때부터 먹는다.
    public static void SetMode(string m)
    {
        mode = (m == SERVER) ? SERVER : LOCAL;
        try { WriteText(ModePath, mode); }
        catch (Exception e) { Debug.LogError("[ChaLocal] 판 저장 실패 " + e); }
    }

    static string PickSaveDir()
    {
        string jni = ExternalFilesDir();
        if (jni != null && Writable(jni)) return jni;
        string ext = ExtDir();
        if (Writable(ext)) return ext;
        Debug.Log("[ChaLocal] 바깥 저장소를 못 쓴다. 앱 내부에 둔다"
                  + " — 런처로는 손댈 수 없다.");
        return Application.persistentDataPath;
    }

    static void Merge(Hashtable baseH, Hashtable over)
    {
        if (over == null) return;
        foreach (DictionaryEntry e in over)
        {
            Hashtable bv = Get(baseH, Convert.ToString(e.Key)) as Hashtable;
            Hashtable ov = e.Value as Hashtable;
            if (bv != null && ov != null) Merge(bv, ov);
            else baseH[e.Key] = e.Value;
        }
    }

    static void LoadSave()
    {
        Save = Copy(Get(D, "default")) as Hashtable;
        if (Save == null) Save = new Hashtable();
        string want = GetS(D, "preset");
        try
        {
            // 바깥 자리에 없으면 예전에 내부에 쓰던 것을 이어받는다.
            string from = SavePath;
            if (!File.Exists(from))
            {
                string old = Application.persistentDataPath + "/chasave.json";
                if (old != SavePath && File.Exists(old))
                {
                    from = old;
                    Debug.Log("[ChaLocal] 예전 자리에서 이어받는다: " + old);
                }
            }
            if (File.Exists(from))
            {
                string txt;
                using (StreamReader r = new StreamReader(from,
                        Encoding.UTF8, true, 4096))
                    txt = r.ReadToEnd();
                Hashtable got = Jp.Parse(txt) as Hashtable;
                // 어떤 세이브든 받아들입니다. APK 가 한 벌이 되면서 '판' 을
                // 가릴 이유가 없어졌습니다 — 시작 상태는 세이브가 정합니다.
                // (예전에는 프리셋 도장이 다르면 버렸습니다. 그 탓에 PC 에서
                //  만든 세이브를 넣으면 게임이 그냥 지워 버렸습니다.)
                if (got != null)
                {
                    string mark = GetS(got, "preset");
                    if (mark != null && mark.Length > 0 && mark != want)
                        Debug.Log("[ChaLocal] '" + mark + "' 세이브를 씁니다");
                    Merge(Save, got);
                }
            }
        }
        catch (Exception e) { Debug.Log("[ChaLocal] 세이브 읽기 실패 " + e.Message); }
        Apply();
        Persist(true);
    }

    /// 파일 -> 살아 있는 값들.
    static void Apply()
    {
        Hashtable p = GetH(Save, "player");
        nickName = GetS(p, "nickName");
        if (nickName == "") nickName = "Racer";
        gold = GetL(p, "gold");
        trophy = GetL(p, "trophy");
        tire = GetL(p, "tire");
        string carName = GetS(p, "car");
        carNo = nameToNo.ContainsKey(carName) ? (int)nameToNo[carName] : 1;
        carSeq = carNo + 1;
        characterNo = GetI(p, "driver");
        if (characterNo <= 0) characterNo = 1;

        Hashtable r = GetH(Save, "records");
        bestScore = GetL(r, "bestScore");
        bestScoreHurdle = GetL(r, "bestScoreHurdle");
        prevScore = GetL(r, "prevScore");
        maxDistance = GetL(r, "maxDistance");
        playCount = GetL(r, "playCount");
        inviteCnt = GetI(GetH(Save, "invite"), "count");

        // 등급: 시작 등급 위에 파일 값을 덮는다
        carClass.Clear();
        foreach (DictionaryEntry e in startClass)
        {
            string nm = Convert.ToString(e.Key);
            if (nameToNo.ContainsKey(nm))
                carClass[(int)nameToNo[nm]] = Convert.ToString(e.Value);
        }
        Hashtable cc = GetH(Save, "carClass");
        if (cc != null)
        {
            foreach (DictionaryEntry e in cc)
            {
                string nm = Convert.ToString(e.Key);
                string cl = Convert.ToString(e.Value);
                if (nameToNo.ContainsKey(nm) && IsClass(cl))
                    carClass[(int)nameToNo[nm]] = cl;
            }
        }

        owned.Clear();
        ArrayList oc = GetA(Save, "carsOwned");
        if (oc != null)
            for (int k = 0; k < oc.Count; k++)
            {
                string nm = Convert.ToString(oc[k]);
                if (nameToNo.ContainsKey(nm)) owned[(int)nameToNo[nm]] = true;
            }
        if (owned.Count == 0) owned[1] = true;

        tune.Clear();
        Hashtable ct = GetH(Save, "carTune");
        if (ct != null)
        {
            foreach (DictionaryEntry e in ct)
            {
                string nm = Convert.ToString(e.Key);
                if (!nameToNo.ContainsKey(nm)) continue;
                int no = (int)nameToNo[nm];
                Hashtable t = e.Value as Hashtable;
                if (t == null) continue;
                SetTune(no, "carAccel", GetI(t, "accel"));
                SetTune(no, "carSpeed", GetI(t, "speed"));
                SetTune(no, "carFuleCost", GetI(t, "oil"));
            }
        }

        items.Clear();
        Hashtable it = GetH(Save, "items");
        if (it != null)
            for (int k = 0; k < ITEM_CODES.Length; k++)
            {
                long v = GetL(it, ITEM_NAME[k]);
                if (v < 0) v = 0;
                if (v > ITEM_MAX) v = ITEM_MAX;
                items[ITEM_CODES[k]] = v;
            }

        skills.Clear();
        ArrayList sk = GetA(Save, "skills");
        if (sk != null)
            for (int k = 0; k < sk.Count; k++)
            {
                Hashtable sr = sk[k] as Hashtable;
                if (sr == null) continue;
                long car = GetL(sr, "car"), no = GetL(sr, "no");
                if (car <= 0 || no <= 0) continue;
                Hashtable one = new Hashtable();
                one["lv"] = GetL(sr, "lv") > 0 ? GetL(sr, "lv") : 1L;
                one["eq"] = GetB(sr, "eq");
                skills[SkillKey(car, no)] = one;
            }

        drivers.Clear();
        ArrayList dv = GetA(Save, "driversOwned");
        if (dv != null)
            for (int k = 0; k < dv.Count; k++)
            {
                int n = (int)Convert.ToInt64(dv[k]);
                if (n >= 1 && n <= driverCount) drivers[n] = true;
            }
        if (drivers.Count == 0) drivers[1] = true;

        presents.Clear();
        ArrayList pr = GetA(Save, "presents");
        if (pr != null)
            for (int k = 0; k < pr.Count; k++)
            {
                Hashtable one = pr[k] as Hashtable;
                if (one == null) continue;
                string kind = GetS(one, "type");
                Hashtable q = new Hashtable();
                q["presentSeq"] = (long)(k + 1);
                q["accountSeq"] = 0L;
                q["presentType"] = kind == "trophy" ? "002"
                                 : (kind == "gold" ? "003" : "001");
                q["presentQty"] = GetL(one, "count");
                q["sender"] = GetS(one, "from");
                presents.Add(q);
            }
    }

    /// 살아 있는 값들 -> 파일. 바뀐 게 없으면 쓰지 않는다.
    /// 겹판이 쓰는 창구들. `Jp` 가 안쪽 클래스라 요약도 여기서 만든다.
    /// 파일 읽기·쓰기도 이 빌드에 있는 길(스트림)로만 한다 —
    /// `File.ReadAllText` · `File.WriteAllText` 는 깎인 mscorlib 에 없다.
    public static string ReadText(string path)
    {
        using (StreamReader r = new StreamReader(path, Encoding.UTF8, true,
                                                 4096))
            return r.ReadToEnd();
    }

    public static void WriteText(string path, string txt)
    {
        using (FileStream fs = new FileStream(path, FileMode.Create,
                                              FileAccess.Write))
        using (StreamWriter w = new StreamWriter(fs, new UTF8Encoding(false)))
            w.Write(txt);
    }

    /// 칸 하나를 한 줄로 요약한다. **이름이 아니라 숫자**다 —
    /// 이 빌드의 글꼴에 한글이 없어서 이름을 써 봐야 안 보인다.
    public static string SlotSummary(string path)
    {
        try
        {
            if (!File.Exists(path)) return "(empty)";
            Hashtable h = Jp.Parse(ReadText(path)) as Hashtable;
            if (h == null) return "(bad file)";
            Hashtable pl = Get(h, "player") as Hashtable;
            ArrayList cars = Get(h, "carsOwned") as ArrayList;
            ArrayList drv = Get(h, "driversOwned") as ArrayList;
            long g = pl == null ? 0 : GetL(pl, "gold");
            long t = pl == null ? 0 : GetL(pl, "trophy");
            return "G " + Comma(g) + "  T " + Comma(t)
                   + "  CAR " + (cars == null ? 0 : cars.Count)
                   + "  DRV " + (drv == null ? 0 : drv.Count);
        }
        catch (Exception) { return "(unreadable)"; }
    }

    static string Comma(long v)
    {
        string s = v.ToString(CultureInfo.InvariantCulture);
        string o = "";
        int c = 0;
        for (int i = s.Length - 1; i >= 0; i--)
        {
            o = s[i] + o;
            if (++c % 3 == 0 && i > 0) o = "," + o;
        }
        return o;
    }

    /// 겹판이 쓰는 두 창구. 세이브 파일 자리와 '지금 바로 써 두기'.
    public static string SaveFile()
    {
        Boot();
        return SavePath;
    }

    public static void FlushSave()
    {
        Boot();
        Persist(true);
    }

    static void Persist() { Persist(false); }

    static void Persist(bool force)
    {
        Hashtable p = GetH(Save, "player");
        if (p == null) { p = new Hashtable(); Save["player"] = p; }
        p["nickName"] = nickName;
        p["gold"] = gold;
        p["trophy"] = trophy;
        p["tire"] = tire;
        p["car"] = noToName.ContainsKey(carNo) ? noToName[carNo] : "AVEO";
        p["driver"] = (long)characterNo;

        Hashtable r = GetH(Save, "records");
        if (r == null) { r = new Hashtable(); Save["records"] = r; }
        r["bestScore"] = bestScore;
        r["bestScoreHurdle"] = bestScoreHurdle;
        r["prevScore"] = prevScore;
        r["maxDistance"] = maxDistance;
        r["playCount"] = playCount;

        Hashtable iv = GetH(Save, "invite");
        if (iv == null) { iv = new Hashtable(); Save["invite"] = iv; }
        iv["count"] = (long)inviteCnt;

        ArrayList oc = new ArrayList();
        for (int no = 1; no <= 40; no++)
            if (owned.ContainsKey(no) && noToName.ContainsKey(no))
                oc.Add(noToName[no]);
        Save["carsOwned"] = oc;

        Hashtable cc = new Hashtable();
        foreach (DictionaryEntry e in carClass)
        {
            int no = (int)e.Key;
            if (!noToName.ContainsKey(no)) continue;
            string nm = Convert.ToString(noToName[no]);
            string cl = Convert.ToString(e.Value);
            if (Convert.ToString(startClass[nm]) != cl) cc[nm] = cl;
        }
        Save["carClass"] = cc;

        Hashtable ct = new Hashtable();
        foreach (DictionaryEntry e in tune)
        {
            string key = Convert.ToString(e.Key);
            int bar = key.IndexOf('|');
            if (bar < 0) continue;
            int no = int.Parse(key.Substring(0, bar));
            string fld = key.Substring(bar + 1);
            if (!noToName.ContainsKey(no)) continue;
            string nm = Convert.ToString(noToName[no]);
            Hashtable one = ct[nm] as Hashtable;
            if (one == null) { one = new Hashtable(); ct[nm] = one; }
            one[fld == "carAccel" ? "accel"
                : (fld == "carSpeed" ? "speed" : "oil")] = Convert.ToInt64(e.Value);
        }
        Save["carTune"] = ct;

        ArrayList dv = new ArrayList();
        for (int k = 1; k <= driverCount; k++)
            if (drivers.ContainsKey(k)) dv.Add((long)k);
        Save["driversOwned"] = dv;

        ArrayList sk2 = new ArrayList();
        foreach (DictionaryEntry e in skills)
        {
            long kk = Convert.ToInt64(e.Key);
            Hashtable v = e.Value as Hashtable;
            Hashtable sr = new Hashtable();
            sr["car"] = kk / 1000L;
            sr["no"] = kk % 1000L;
            sr["lv"] = v == null ? 1L : Convert.ToInt64(v["lv"]);
            sr["eq"] = v != null && Convert.ToBoolean(v["eq"]);
            sk2.Add(sr);
        }
        Save["skills"] = sk2;

        Hashtable it2 = new Hashtable();
        for (int k = 0; k < ITEM_CODES.Length; k++)
            it2[ITEM_NAME[k]] = (long)ItemAt(ITEM_CODES[k]);
        Save["items"] = it2;

        ArrayList pr = new ArrayList();
        for (int k = 0; k < presents.Count; k++)
        {
            Hashtable one = presents[k] as Hashtable;
            string ty = GetS(one, "presentType");
            Hashtable q = new Hashtable();
            q["type"] = ty == "002" ? "trophy" : (ty == "003" ? "gold" : "tire");
            q["count"] = GetL(one, "presentQty");
            q["from"] = GetS(one, "sender");
            pr.Add(q);
        }
        Save["presents"] = pr;

        Save["preset"] = GetS(D, "preset");
        string blob = Write(Save);
        if (!force && blob == lastSaved) return;
        lastSaved = blob;
        // File.WriteAllText 도 File.Move 도 이 빌드의 mscorlib 에는 없다.
        // 스트림으로 곧바로 쓴다.
        try
        {
            using (FileStream fs = new FileStream(SavePath, FileMode.Create,
                                                  FileAccess.Write))
            using (StreamWriter w = new StreamWriter(fs, new UTF8Encoding(false)))
                w.Write(blob);
        }
        catch (Exception e) { Debug.Log("[ChaLocal] 세이브 쓰기 실패 " + e.Message); }
    }

    // ---------------------------------------------------------- 자잘한 도구
    static bool IsClass(string c)
    {
        return c == "C" || c == "B" || c == "A" || c == "S" || c == "R";
    }

    static string ClassOf(int no)
    {
        return carClass.ContainsKey(no) ? Convert.ToString(carClass[no]) : "C";
    }

    static int GetTune(int no, string fld)
    {
        string k = no + "|" + fld;
        return tune.ContainsKey(k) ? (int)Convert.ToInt64(tune[k]) : 0;
    }

    static void SetTune(int no, string fld, int lv)
    {
        string k = no + "|" + fld;
        if (lv <= 0) { tune.Remove(k); return; }
        tune[k] = (long)(lv > 3 ? 3 : lv);
    }

    static void AddGold(long n)
    {
        gold += n;
        if (gold < 0) gold = 0;
        if (gold > maxGold) gold = maxGold;
    }

    static void AddTrophy(long n)
    {
        trophy += n;
        if (trophy < 0) trophy = 0;
        if (trophy > maxTrophy) trophy = maxTrophy;
    }

    static void AddTire(long n)
    {
        tire += n;
        if (tire < 0) tire = 0;
        if (tire > maxTire) tire = maxTire;
    }

    static int Pick(Hashtable req, string a) { return Pick(req, a, null, null); }
    static int Pick(Hashtable req, string a, string b) { return Pick(req, a, b, null); }

    static int Pick(Hashtable req, string a, string b, string c)
    {
        string[] ks = { a, b, c };
        for (int k = 0; k < ks.Length; k++)
        {
            if (ks[k] == null) continue;
            long v = GetL(req, ks[k]);
            if (v > 0) return (int)v;
        }
        return 0;
    }

    static Hashtable Auto(string path)
    {
        object s = Get(Skel, path);
        Hashtable h = s == null ? null : Copy(s) as Hashtable;
        if (h == null)
        {
            h = new Hashtable();
            h["success"] = true;
            h["errorCode"] = null;
            h["token"] = 1000001L;
        }
        return h;
    }

    static void SetIf(Hashtable h, string k, object v)
    {
        if (h.ContainsKey(k)) h[k] = v;
    }

    static string Stamp() { return DateTime.Now.ToString("yyyyMMdd", CultureInfo.InvariantCulture); }

    static string Now()
    {
        return DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss",
                                     CultureInfo.InvariantCulture);
    }

    // ================================================================ 처리기
    // 문자열 switch 는 컴파일러가 Dictionary 표를 만든다. 깎여 나간
    // mscorlib 위에서는 그 길을 안 밟는 게 안전해 if 사슬로 둔다.
    static Hashtable Route(string path, Hashtable q)
    {
        if (path == "/user/auth/login") return EpLogin(q);
        else if (path == "/user/info/get") return EpUserInfo(q);
        else if (path == "/user/info/update") return EpUpdateUserInfo(q);
        else if (path == "/user/tire/check") return EpTire(q);
        else if (path == "/user/car/list") return EpCarList(q);
        else if (path == "/user/car/select") return EpSelectCar(q);
        else if (path == "/user/car/tune") return EpTuneCar(q);
        else if (path == "/user/car/upgrade") return EpUpgradeCar(q);
        else if (path == "/user/car/compensate") return EpTradeList(q);
        else if (path == "/user/character/list") return EpCharList(q);
        else if (path == "/skill/get/list") return EpSkillList(q);
        else if (path == "/skill/buy") return EpSkillBuy(q);
        else if (path == "/skill/equip") return EpSkillEquip(q);
        else if (path == "/skill/upgrade") return EpSkillUpgrade(q);
        else if (path == "/shop/item/list") return EpItemList(q);
        else if (path == "/shop/item/buy") return EpBuyItem(q);
        else if (path == "/play/item/use") return EpUseItem(q);
        else if (path == "/shop/character/buy") return EpBuyCharacter(q);
        else if (path == "/user/character/select") return EpSelectChar(q);
        else if (path == "/service/resource/messagelist") return EpMessageList(q);
        else if (path == "/service/notice/get") return EpNotice(q);
        else if (path == "/shop/car/buy") return EpBuyCar(q);
        else if (path == "/shop/car/unlock") return GetCar(q, "/shop/car/unlock");
        else if (path == "/shop/car/unlockbuy") return GetCar(q, "/shop/car/unlockbuy");
        else if (path == "/shop/car/gacha") return EpGacha(q);
        else if (path == "/shop/car/compensate") return EpTradeBuy(q);
        else if (path == "/shop/gold/exchange") return EpExchangeGold(q);
        else if (path == "/shop/tire/exchange") return EpExchangeTire(q);
        else if (path == "/shop/billing/raven/register") return EpBillRegister(q);
        else if (path == "/shop/billing/raven/confirm") return EpBillConfirm(q);
        else if (path == "/play/game/start") return EpGameStart(q);
        else if (path == "/play/game/finish") return EpGameFinish(q);
        else if (path == "/ranking/current/list") return EpRankList(q);
        else if (path == "/ranking/previous/list") return EpPrevRankList(q);
        else if (path == "/tire/present/list") return EpPresentList(q);
        else if (path == "/tire/present/recv") return EpPresentRecv(q);
        else if (path == "/tire/present/recvAll") return EpPresentRecv(q);
        else if (path == "/invitation/list") return EpInviteList(q);
        else if (path == "/invitation/invite") return EpInvite(q);
        return Auto(path);
    }

    static Hashtable EpLogin(Hashtable q)
    {
        byte[] k = new byte[16], v = new byte[16];
        for (int n = 0; n < 16; n++)
        {
            k[n] = (byte)NextInt(0, 256);
            v[n] = (byte)NextInt(0, 256);
        }
        cryptoKey = Convert.ToBase64String(k);
        initVector = Convert.ToBase64String(v);
        Hashtable b = Auto("/user/auth/login");
        b["cryptoKey"] = cryptoKey;
        b["initialVector"] = initVector;
        b["accountSeq"] = 1L;
        b["registered"] = true;
        b["takeTrophy"] = false;
        bool newWeek = GetB(GetH(Save, "flags"), "newWeek");
        b["newWeek"] = newWeek;
        b["newPresent"] = false;
        b["newWeekStart"] = Stamp();
        Hashtable r = new Hashtable();
        r["accountSeq"] = 1L;
        r["registered"] = true;
        r["takeTrophy"] = false;
        r["newWeek"] = newWeek;
        r["newWeekStart"] = Stamp();
        r["newPresent"] = false;
        b["result"] = r;
        return b;
    }

    static Hashtable EpUserInfo(Hashtable q)
    {
        Hashtable b = Auto("/user/info/get");
        Hashtable t = GetH(b, "info");
        if (t == null) t = b;
        t["nickName"] = nickName;
        t["gold"] = gold;
        t["goldAmt"] = gold;
        t["trophyCnt"] = trophy;
        t["tireCnt"] = tire;
        t["tireRemainSecs"] = 0L;
        t["canPresent"] = true;
        t["carNo"] = (long)carNo;
        t["carSeq"] = (long)carSeq;
        t["carClass"] = ClassOf(carNo);
        t["characterNo"] = (long)characterNo;
        t["maxScore"] = bestScore;
        t["maxPoint"] = bestScore;
        t["maxDistance"] = maxDistance;
        t["playCount"] = playCount;
        t["friendInviteCnt"] = (long)inviteCnt;
        t["carAccel"] = (long)(GetTune(carNo, "carAccel") + 1);
        t["carSpeed"] = (long)(GetTune(carNo, "carSpeed") + 1);
        t["carFuleCost"] = (long)(GetTune(carNo, "carFuleCost") + 1);
        b["missions"] = new ArrayList();
        t.Remove("missions");
        string st = Stamp();
        if (t.ContainsKey("newWeekStart")) t["newWeekStart"] = st;
        if (t.ContainsKey("totalRankRewardInit")) t["totalRankRewardInit"] = st;
        return b;
    }

    /// 이름 바꾸기. 게임 안에 바꾸는 화면은 없지만, 무엇이 오든 세이브에
    /// 남겨 두어야 다음에 켰을 때 유지됩니다.
    static Hashtable EpUpdateUserInfo(Hashtable q)
    {
        string nm = GetS(q, "nickName").Trim();
        if (nm.Length > 0)
        {
            if (nm.Length > 16) nm = nm.Substring(0, 16);
            if (nm != nickName)
                Debug.Log("[ChaLocal] 이름 바꿈: " + nickName + " -> " + nm);
            nickName = nm;
        }
        Hashtable b = Auto("/user/info/update");
        b["nickName"] = nickName;
        return b;
    }

    static Hashtable EpTire(Hashtable q)
    {
        Hashtable b = Auto("/user/tire/check");
        b["tireCnt"] = tire;
        b["remainTime"] = 0L;
        if (b.ContainsKey("result"))
        {
            Hashtable r = new Hashtable();
            r["tireCnt"] = tire;
            r["remainTime"] = 0L;
            b["result"] = r;
        }
        return b;
    }

    static Hashtable EpCarList(Hashtable q)
    {
        Hashtable b = Auto("/user/car/list");
        ArrayList proto = GetA(b, "cars");
        Hashtable one = (proto != null && proto.Count > 0)
                        ? proto[0] as Hashtable : null;
        ArrayList list = new ArrayList();
        for (int no = 1; no <= 40; no++)
        {
            if (!owned.ContainsKey(no)) continue;
            Hashtable c = one == null ? new Hashtable()
                                      : Copy(one) as Hashtable;
            SetIf(c, "carNo", (long)no);
            SetIf(c, "carSeq", (long)(no + 1));
            SetIf(c, "carClass", ClassOf(no));
            SetIf(c, "isSelected", no == carNo);
            SetIf(c, "carAccel", (long)(GetTune(no, "carAccel") + 1));
            SetIf(c, "carSpeed", (long)(GetTune(no, "carSpeed") + 1));
            SetIf(c, "carFuleCost", (long)(GetTune(no, "carFuleCost") + 1));
            list.Add(c);
        }
        b["cars"] = list;
        return b;
    }

    static Hashtable EpCharList(Hashtable q)
    {
        Hashtable b = Auto("/user/character/list");
        ArrayList proto = GetA(b, "characters");
        Hashtable one = (proto != null && proto.Count > 0)
                        ? proto[0] as Hashtable : null;
        ArrayList list = new ArrayList();
        for (int no = 1; no <= driverCount; no++)
        {
            if (!drivers.ContainsKey(no)) continue;
            Hashtable c = one == null ? new Hashtable()
                                      : Copy(one) as Hashtable;
            SetIf(c, "characterNo", (long)no);
            SetIf(c, "isSelected", no == characterNo);
            list.Add(c);
        }
        if (b.ContainsKey("characters")) b["characters"] = list;
        return b;
    }

    static Hashtable EpSelectCar(Hashtable q)
    {
        int no = Pick(q, "carNo");
        if (owned.ContainsKey(no))
        {
            carNo = no;
            int seq = Pick(q, "carSeq");
            carSeq = seq > 0 ? seq : no + 1;
        }
        return Auto("/user/car/select");
    }

    static Hashtable EpSelectChar(Hashtable q)
    {
        int no = Pick(q, "characterNo");
        if (no >= 1 && no <= driverCount) characterNo = no;
        return Auto("/user/character/select");
    }

    static int CarNoOf(Hashtable q)
    {
        int no = Pick(q, "carNo");
        if (owned.ContainsKey(no)) return no;
        int seq = Pick(q, "carSeq");
        if (owned.ContainsKey(seq - 1)) return seq - 1;
        return carNo;
    }

    static Hashtable EpTuneCar(Hashtable q)
    {
        int no = CarNoOf(q);
        Hashtable keys = GetH(D, "tuneKey");
        string fld = "carAccel";
        int ty = Pick(q, "tuneType");
        if (keys != null && keys.ContainsKey(ty.ToString()))
            fld = Convert.ToString(keys[ty.ToString()]);
        int lv = GetTune(no, fld);
        if (lv < 3)
        {
            ArrayList costs = Get(GetH(D, "tuneCost"), ClassOf(no)) as ArrayList;
            long cost = (costs != null && lv < costs.Count)
                        ? Convert.ToInt64(costs[lv]) : 0;
            if (gold >= cost)
            {
                gold -= cost;
                SetTune(no, fld, lv + 1);
            }
        }
        Hashtable b = Auto("/user/car/tune");
        b["remainGoldAmt"] = gold;
        b["missions"] = new ArrayList();
        SetIf(b, "carAccel", (long)GetTune(no, "carAccel"));
        SetIf(b, "carSpeed", (long)GetTune(no, "carSpeed"));
        SetIf(b, "carFuleCost", (long)GetTune(no, "carFuleCost"));
        return b;
    }

    static Hashtable EpUpgradeCar(Hashtable q)
    {
        int no = CarNoOf(q);
        ArrayList up = Get(GetH(D, "classUp"), ClassOf(no)) as ArrayList;
        if (up != null && up.Count >= 2)
        {
            string nxt = Convert.ToString(up[0]);
            long cost = Convert.ToInt64(up[1]);
            if (gold >= cost)
            {
                gold -= cost;
                carClass[no] = nxt;
                SetTune(no, "carAccel", 0);
                SetTune(no, "carSpeed", 0);
                SetTune(no, "carFuleCost", 0);
            }
        }
        Hashtable b = Auto("/user/car/upgrade");
        b["remainGoldAmt"] = gold;
        b["missions"] = new ArrayList();
        return b;
    }

    /// 차 구매 · 해금. 골드로 사는 길과 트로피로 여는 길이 따로 있다.
    static Hashtable GetCar(Hashtable q, string path)
    {
        int no = Pick(q, "carNo");
        if (!carClass.ContainsKey(no)) no = Pick(q, "carSeq") - 1;
        ArrayList cost = Get(GetH(D, "carCost"), no.ToString()) as ArrayList;
        long gv = (cost != null && cost.Count > 0) ? Convert.ToInt64(cost[0]) : 0;
        long tv = (cost != null && cost.Count > 1) ? Convert.ToInt64(cost[1]) : 0;
        bool byGold = path.EndsWith("/buy");
        if (carClass.ContainsKey(no) && !owned.ContainsKey(no))
        {
            if (byGold && gv > 0 && gold >= gv) { gold -= gv; owned[no] = true; }
            else if (!byGold && trophy >= tv) { trophy -= tv; owned[no] = true; }
            else if (gv > 0 && gold >= gv) { gold -= gv; owned[no] = true; }
        }
        Hashtable b = Auto(path);
        b["missions"] = new ArrayList();
        b["remainGoldAmt"] = gold;
        b["goldAmt"] = gold;
        b["gold"] = gold;
        b["remainTrophyCnt"] = trophy;
        b["trophyCnt"] = trophy;
        b["carSeq"] = (long)(no + 1);
        b["carNo"] = (long)no;
        b["carClass"] = ClassOf(no);
        return b;
    }

    static Hashtable EpBuyCar(Hashtable q)
    {
        int no = Pick(q, "carNo", "carSeq", "productNo");
        long price = GetL(q, "price");
        if (no > 0)
        {
            owned[no] = true;
            gold -= price;
            if (gold < 0) gold = 0;
        }
        Hashtable b = Auto("/shop/car/buy");
        b["remainGoldAmt"] = gold;
        b["goldAmt"] = gold;
        b["carSeq"] = (long)no;
        b["carNo"] = (long)no;
        return b;
    }

    static Hashtable EpGameStart(Hashtable q)
    {
        raceValue++;
        int no = GetI(q, "carNo");
        if (owned.ContainsKey(no))
        {
            carNo = no;
            int seq = Pick(q, "carSeq");
            if (seq > 0) carSeq = seq;
        }
        Hashtable b = Auto("/play/game/start");
        SetIf(b, "raceValue", (long)raceValue);
        return b;
    }

    static Hashtable EpGameFinish(Hashtable q)
    {
        Hashtable r = GetH(q, "gameFinishReq");
        if (r == null) r = q;
        AddGold(GetL(r, "gold"));
        long sc = GetL(r, "score");
        if (GetS(r, "gameMode") == "002")
        {
            if (sc > bestScoreHurdle) bestScoreHurdle = sc;
        }
        else if (sc > bestScore) bestScore = sc;
        long dist = GetL(r, "distance");
        if (dist > maxDistance) maxDistance = dist;
        playCount++;
        Hashtable b = Auto("/play/game/finish");
        SetIf(b, "remainGoldAmt", gold);
        SetIf(b, "goldAmt", gold);
        SetIf(b, "gold", gold);
        SetIf(b, "remainTireCnt", tire);
        return b;
    }

    /// 교환표에서 한 줄을 고른다. exchangeNo(자리 번호)가 먼저다.
    static long[] Amount(Hashtable q, string tableKey)
    {
        int no = GetI(q, "exchangeNo");
        Hashtable ex = GetH(D, "exchangeNo");
        if (no > 0 && ex != null && ex.ContainsKey(no.ToString()))
        {
            ArrayList row = ex[no.ToString()] as ArrayList;
            if (row != null && row.Count >= 2)
                return new long[] { Convert.ToInt64(row[0]),
                                    Convert.ToInt64(row[1]) };
        }
        ArrayList tbl = GetA(D, tableKey);
        long want = 0;
        string[] ks = { "trophyCnt", "count", "itemCount", "amount", "productNo" };
        for (int k = 0; k < ks.Length; k++)
        {
            long v = GetL(q, ks[k]);
            if (v > 0) { want = v; break; }
        }
        if (tbl != null)
        {
            for (int k = 0; k < tbl.Count; k++)
            {
                ArrayList row = tbl[k] as ArrayList;
                if (row != null && Convert.ToInt64(row[0]) == want)
                    return new long[] { Convert.ToInt64(row[0]),
                                        Convert.ToInt64(row[1]) };
            }
            ArrayList f = tbl.Count > 0 ? tbl[0] as ArrayList : null;
            if (f != null)
                return new long[] { Convert.ToInt64(f[0]), Convert.ToInt64(f[1]) };
        }
        return new long[] { 0, 0 };
    }

    static Hashtable EpExchangeGold(Hashtable q)
    {
        long[] a = Amount(q, "goldExchange");
        if (trophy >= a[0]) { trophy -= a[0]; AddGold(a[1]); }
        Hashtable b = Auto("/shop/gold/exchange");
        b["remainGoldAmt"] = gold;
        b["goldAmt"] = gold;
        b["remainTrophyCnt"] = trophy;
        b["trophyCnt"] = trophy;
        return b;
    }

    static Hashtable EpExchangeTire(Hashtable q)
    {
        long[] a = Amount(q, "tireExchange");
        if (trophy >= a[0]) { trophy -= a[0]; AddTire(a[1]); }
        Hashtable b = Auto("/shop/tire/exchange");
        b["remainTrophyCnt"] = trophy;
        b["trophyCnt"] = trophy;
        b["remainTireCnt"] = tire;
        b["tireCnt"] = tire;
        return b;
    }

    static Hashtable EpItemList(Hashtable q)
    {
        Hashtable b = Auto("/shop/item/list");
        ArrayList a = new ArrayList();
        for (int k = 0; k < ITEM_CODES.Length; k++)
        {
            Hashtable one = new Hashtable();
            one["itemCode"] = (long)ITEM_CODES[k];
            one["itemCount"] = (long)ItemAt(ITEM_CODES[k]);
            a.Add(one);
        }
        b["items"] = a;
        b["toolboxRetryCount"] = 0L;
        b["toolboxRebuyGoldAmt"] = 0L;
        return b;
    }

    /// 아이템 한 개 구매. 값은 클라이언트 표와 같습니다.
    static Hashtable EpBuyItem(Hashtable q)
    {
        int code = Pick(q, "itemCode");
        for (int k = 0; k < ITEM_CODES.Length; k++)
        {
            if (ITEM_CODES[k] != code) continue;
            long cost = ITEM_COST[k];
            if (gold >= cost)
            {
                gold -= cost;
                int have = ItemAt(code) + 1;
                items[code] = (long)(have > ITEM_MAX ? ITEM_MAX : have);
            }
            break;
        }
        Hashtable b = Auto("/shop/item/buy");
        b["remainGoldAmt"] = gold;
        b["toolboxItemNo"] = 0L;
        return b;
    }

    static Hashtable EpUseItem(Hashtable q)
    {
        int code = Pick(q, "itemCode");
        int have = ItemAt(code);
        if (have > 0) items[code] = (long)(have - 1);
        Hashtable b = Auto("/play/item/use");
        b["remainGoldAmt"] = gold;
        return b;
    }

    /// 캐릭터 구매. **트로피로만** 받습니다.
    ///
    /// 값을 못 치르면 실패로 돌려줍니다. 성공을 돌려주면 클라이언트가 그
    /// 말을 믿고 카드를 '장착중'으로 바꿔 버립니다. 클라이언트는 실패의
    /// `errorCode` 를 **그대로 문구 열쇠로 삼아** 팝업을 띄우는데,
    /// `SVC_3003` 은 정품 서버가 쓰던 코드라 문자열표에 그대로 있습니다 —
    /// "보유하신 트로피가 부족합니다. 트로피는 상점에서 구입이 가능합니다^^".
    static Hashtable EpBuyCharacter(Hashtable q)
    {
        int no = Pick(q, "characterNo");
        long cost = DriverCost(no);
        bool ok = false;
        if (no >= 1 && no <= driverCount && drivers.ContainsKey(no))
        {
            ok = true;                       // 이미 가진 것
        }
        else if (no >= 1 && no <= driverCount && trophy >= cost)
        {
            trophy -= cost;
            drivers[no] = true;
            ok = true;
        }
        Hashtable b = Auto("/shop/character/buy");
        b["remainTrophyCnt"] = trophy;
        b["missions"] = new ArrayList();
        if (!ok)
        {
            b["success"] = false;
            b["errorCode"] = "SVC_3003";
        }
        return b;
    }

    // --- 스킬 -------------------------------------------------------
    // 스킬은 차마다 붙는다. 응답 칸 이름이 차·아이템 쪽과 다르다 —
    // 여기는 remainGoldAmount / remainTrophyCount 다(Amt/Cnt 가 아니다).
    static Hashtable SkillRow(int no)
    {
        ArrayList tab = Get(D, "skillTab") as ArrayList;
        if (tab == null) return null;
        for (int i = 0; i < tab.Count; i++)
        {
            Hashtable r = tab[i] as Hashtable;
            if (r != null && GetL(r, "no") == no) return r;
        }
        return null;
    }

    static Hashtable EpSkillList(Hashtable q)
    {
        Hashtable b = Auto("/skill/get/list");
        ArrayList a = new ArrayList();
        foreach (DictionaryEntry e in skills)
        {
            long kk = Convert.ToInt64(e.Key);
            int no = (int)(kk % 1000L);
            Hashtable info = SkillRow(no);
            Hashtable v = e.Value as Hashtable;
            Hashtable one = new Hashtable();
            one["skillNo"] = kk % 1000L;
            one["carNo"] = kk / 1000L;
            one["skillLevel"] = v == null ? 1L : Convert.ToInt64(v["lv"]);
            one["equipFlag"] = (v != null && Convert.ToBoolean(v["eq"]))
                               ? "Y" : "N";
            one["skillType"] = info == null ? "002" : GetS(info, "slotCode");
            a.Add(one);
        }
        b["skillList"] = a;
        return b;
    }

    static Hashtable EpSkillBuy(Hashtable q)
    {
        int no = Pick(q, "skillNo");
        int car = Pick(q, "carNo");
        Hashtable info = SkillRow(no);
        long key = SkillKey(car, no);
        if (info != null && car > 0 && !skills.ContainsKey(key))
        {
            long cost = GetL(info, "cost");
            bool byTrophy = GetS(info, "costType") == "Trophy";
            bool ok = byTrophy ? (trophy >= cost) : (gold >= cost);
            if (ok)
            {
                if (byTrophy) trophy -= cost; else gold -= cost;
                Hashtable one = new Hashtable();
                one["lv"] = 1L;
                one["eq"] = false;
                skills[key] = one;
            }
        }
        Hashtable b = Auto("/skill/buy");
        b["remainGoldAmount"] = gold;
        b["remainTrophyCount"] = trophy;
        return b;
    }

    static Hashtable EpSkillEquip(Hashtable q)
    {
        int no = Pick(q, "skillNo");
        int car = Pick(q, "carNo");
        string flag = GetS(q, "equipFlag");
        Hashtable v = skills[SkillKey(car, no)] as Hashtable;
        if (v != null)
            v["eq"] = (flag == null || flag.Length == 0
                       || flag.ToUpper().StartsWith("Y"));
        return Auto("/skill/equip");
    }

    static Hashtable EpSkillUpgrade(Hashtable q)
    {
        int no = Pick(q, "skillNo");
        int car = Pick(q, "carNo");
        Hashtable info = SkillRow(no);
        Hashtable v = skills[SkillKey(car, no)] as Hashtable;
        long lv = 1;
        if (info != null && v != null)
        {
            lv = Convert.ToInt64(v["lv"]);
            long max = GetL(info, "max");
            ArrayList up = Get(info, "upgrade") as ArrayList;
            long cost = (up != null && lv - 1 < up.Count)
                        ? Convert.ToInt64(up[(int)(lv - 1)]) : 0;
            if (lv + 1 <= max && gold >= cost)
            {
                gold -= cost;
                lv += 1;
                v["lv"] = lv;
            }
        }
        Hashtable b = Auto("/skill/upgrade");
        b["skillLevel"] = lv;
        b["remainGoldAmount"] = gold;
        return b;
    }

    static Hashtable EpMessageList(Hashtable q)
    {
        // 빈 배열을 주면 클라이언트 파서가 널을 돌려줘 길이를 재다 죽는다.
        Hashtable b = Auto("/service/resource/messagelist");
        ArrayList a = new ArrayList();
        Hashtable m = new Hashtable();
        m["code"] = "999";
        m["message"] = "";
        a.Add(m);
        b["messages"] = a;
        return b;
    }

    static Hashtable EpNotice(Hashtable q)
    {
        Hashtable b = Auto("/service/notice/get");
        Hashtable n = GetH(Save, "notice");
        string body = GetS(n, "body"), title = GetS(n, "title"), url = GetS(n, "url");
        string[] bk = { "notice", "noticeMessage", "message", "content" };
        for (int k = 0; k < bk.Length; k++) b[bk[k]] = body;
        b["noticeTitle"] = title;
        b["title"] = title;
        b["noticeUrl"] = url;
        b["url"] = url;
        return b;
    }

    static Hashtable EpPresentList(Hashtable q)
    {
        Hashtable b = Auto("/tire/present/list");
        ArrayList a = new ArrayList();
        for (int k = 0; k < presents.Count; k++)
        {
            Hashtable one = Copy(presents[k]) as Hashtable;
            one["recvDate"] = Now();       // 빈 문자열이면 중국어 기본값이 남는다
            a.Add(one);
        }
        b["presents"] = a;
        return b;
    }

    static Hashtable EpPresentRecv(Hashtable q)
    {
        int seq = Pick(q, "presentSeq");
        long got = 0;
        for (int k = presents.Count - 1; k >= 0; k--)
        {
            Hashtable one = presents[k] as Hashtable;
            if (seq > 0 && GetI(one, "presentSeq") != seq) continue;
            got += GetL(one, "presentQty");
            presents.RemoveAt(k);
        }
        AddTire(got);
        Hashtable b = Auto("/tire/present/recv");
        b["recvType"] = "001";
        b["recvQty"] = got;
        b["tireCnt"] = tire;
        return b;
    }

    // --- 주간순위 ---------------------------------------------------

    static Hashtable RankRow(string uid, long seq, long score, int cno,
                             string ccls, string mode)
    {
        Hashtable h = new Hashtable();
        h["userId"] = uid;
        h["gameMode"] = mode;
        h["accountSeq"] = seq;
        h["score"] = score;
        h["carNo"] = (long)cno;
        h["carClass"] = ccls;
        h["canPresent"] = false;
        h["sentPresent"] = false;
        h["boastReject"] = false;
        h["carX"] = 0L;
        h["carY"] = 0L;
        h["matchRejectFlag"] = false;
        h["grade"] = "";
        h["isDormancy"] = false;
        h["ladderClassNo"] = 1L;
        return h;
    }

    static ArrayList RankList(string[] modes, long[] scores)
    {
        ArrayList rows = new ArrayList();
        ArrayList rivals = GetA(D, "rivals");
        for (int m = 0; m < modes.Length; m++)
        {
            rows.Add(RankRow("__me__", 1, scores[m], carNo, ClassOf(carNo),
                             modes[m]));
            if (rivals == null) continue;
            for (int k = 0; k < rivals.Count; k++)
            {
                ArrayList r = rivals[k] as ArrayList;
                if (r == null || r.Count < 4) continue;
                rows.Add(RankRow(Convert.ToString(r[0]), 100 + k,
                                 Convert.ToInt64(r[1]),
                                 (int)Convert.ToInt64(r[2]),
                                 Convert.ToString(r[3]), modes[m]));
            }
        }
        return rows;
    }

    static Hashtable EpRankList(Hashtable q)
    {
        Hashtable b = Auto("/ranking/current/list");
        b["friends"] = RankList(new string[] { "001", "002" },
                                new long[] { bestScore, bestScoreHurdle });
        return b;
    }

    static Hashtable EpPrevRankList(Hashtable q)
    {
        Hashtable b = Auto("/ranking/previous/list");
        ArrayList rows = RankList(new string[] { "001" }, new long[] { prevScore });
        b[b.ContainsKey("friends") ? "friends" : "ranks"] = rows;
        return b;
    }

    // --- 초대 -------------------------------------------------------
    static Hashtable EpInviteList(Hashtable q)
    {
        // 늘 비워 둔다. 쌓아 두면 그 사람들이 초대 대상에서 빠진다.
        Hashtable b = Auto("/invitation/list");
        b["invitations"] = new ArrayList();
        return b;
    }

    static Hashtable EpInvite(Hashtable q)
    {
        inviteCnt++;
        ArrayList missions = new ArrayList();
        ArrayList got = Get(GetH(D, "inviteReward"), inviteCnt.ToString())
                        as ArrayList;
        int gotCar = 0;
        if (got != null && got.Count >= 3)
        {
            string kind = Convert.ToString(got[0]);
            long amt = Convert.ToInt64(got[1]);
            long mission = Convert.ToInt64(got[2]);
            if (kind == "tire") AddTire(amt);
            else if (kind == "gold") AddGold(amt);
            else if (kind == "trophy") AddTrophy(amt);
            else if (kind == "car") { owned[(int)amt] = true; gotCar = (int)amt; }
            if (mission > 0) missions.Add(mission);
        }
        Hashtable b = Auto("/invitation/invite");
        b["inviteCnt"] = (long)inviteCnt;
        b["missions"] = missions;
        if (gotCar > 0)
        {
            b["carNo"] = (long)gotCar;
            b["carSeq"] = (long)(gotCar + 1);
        }
        return b;
    }

    // --- 결제 -------------------------------------------------------
    static Hashtable EpBillRegister(Hashtable q)
    {
        string item = GetS(q, "marketItemId");
        // nonce 는 반드시 **숫자**여야 한다. 문자열이면 클라이언트가 0 을 되보낸다.
        long nonce = (DateTime.Now.Ticks / 10000L) % 100000000L;
        pendingBill[nonce] = item;
        Hashtable b = Auto("/shop/billing/raven/register");
        b["nonce"] = nonce;
        b["resCode"] = "0000";
        b["transactionId"] = nonce.ToString(CultureInfo.InvariantCulture);
        b["rate"] = 1L;
        b["applicationId"] = "cha";
        b["applicationKey"] = "cha";
        b["privateKey"] = "cha";
        b["notifyUrl"] = "";
        b["applicationName"] = "cha";
        Hashtable rr = new Hashtable();
        rr["resCode"] = "0000";
        rr["nonce"] = nonce;
        b["billRegistResult"] = rr;
        return b;
    }

    static Hashtable EpBillConfirm(Hashtable q)
    {
        long nonce = GetL(q, "nonce");
        string item = pendingBill.ContainsKey(nonce)
                      ? Convert.ToString(pendingBill[nonce]) : GetS(q, "marketItemId");
        pendingBill.Remove(nonce);
        object v = Get(GetH(D, "billingItems"), item);
        if (v != null) AddTrophy(Convert.ToInt64(v));
        Hashtable b = Auto("/shop/billing/raven/confirm");
        b["resCode"] = "0000";
        b["trophyCnt"] = trophy;
        b["remainTrophyCnt"] = trophy;
        return b;
    }

    // --- 자동차 가챠 -------------------------------------------------
    static Hashtable EpGacha(Hashtable q)
    {
        int no = Pick(q, "carNo");
        bool retry = GetB(q, "retry");
        long cost = GetL(D, retry ? "gachaRetryCost" : "gachaCost");
        Hashtable gc = GetH(D, "gachaCars");
        Hashtable b = Auto("/shop/car/gacha");
        b["missions"] = new ArrayList();
        bool okCar = gc != null && gc.ContainsKey(no.ToString());
        if (!okCar || trophy < cost)
        {
            b["remainTrophyCnt"] = trophy;
            b["carSeq"] = (long)(no + 1);
            b["carClass"] = ClassOf(no);
            return b;
        }
        trophy -= cost;
        ArrayList odds = GetA(D, "gachaOdds");
        long total = 0;
        for (int k = 0; k < odds.Count; k++)
            total += Convert.ToInt64((odds[k] as ArrayList)[1]);
        long roll = NextInt(1, (int)total + 1);
        string cls = "C";
        for (int k = 0; k < odds.Count; k++)
        {
            ArrayList row = odds[k] as ArrayList;
            roll -= Convert.ToInt64(row[1]);
            if (roll <= 0) { cls = Convert.ToString(row[0]); break; }
        }
        carClass[no] = cls;
        owned[no] = true;
        long[] bonusTable = { 0, 0, 500, 1000, 2000 };
        long bonus = bonusTable[NextInt(0, bonusTable.Length)];
        if (bonus > 0) AddGold(bonus);
        b["remainTrophyCnt"] = trophy;
        b["carSeq"] = (long)(no + 1);
        b["carClass"] = cls;
        b["itemNo"] = 0L;
        b["goldAmt"] = bonus;
        return b;
    }

    // --- 되팔기(보상 판매) -------------------------------------------
    static Hashtable EpTradeList(Hashtable q)
    {
        Hashtable b = Auto("/user/car/compensate");
        Hashtable cv = GetH(D, "tradeClassValue");
        Hashtable lv = GetH(D, "tradeLevelValue");
        ArrayList rows = new ArrayList();
        foreach (DictionaryEntry e in cv)
        {
            for (int l = 1; l <= 4; l++)
            {
                long lvv = lv != null && lv.ContainsKey(l.ToString())
                           ? Convert.ToInt64(lv[l.ToString()]) : 0;
                Hashtable r = new Hashtable();
                r["carClass"] = Convert.ToString(e.Key);
                r["carClassTrophy"] = Convert.ToInt64(e.Value);
                r["carAccel"] = (long)l;
                r["carAccelTrophy"] = lvv;
                r["carSpeed"] = (long)l;
                r["carSpeedTrophy"] = lvv;
                r["carSkill"] = (long)l;
                r["carSkillTrophy"] = lvv;
                r["carFuleCost"] = (long)l;
                r["carFuleCostTrophy"] = lvv;
                rows.Add(r);
            }
        }
        b["compensateCars"] = rows;
        return b;
    }

    static long TradeValue(int no)
    {
        Hashtable cv = GetH(D, "tradeClassValue");
        Hashtable lv = GetH(D, "tradeLevelValue");
        long v = (cv != null && cv.ContainsKey(ClassOf(no)))
                 ? Convert.ToInt64(cv[ClassOf(no)]) : 0;
        string[] flds = { "carAccel", "carSpeed", "carFuleCost" };
        for (int k = 0; k < flds.Length; k++)
        {
            string key = (GetTune(no, flds[k]) + 1).ToString();
            if (lv != null && lv.ContainsKey(key)) v += Convert.ToInt64(lv[key]);
        }
        return v;
    }

    static Hashtable EpTradeBuy(Hashtable q)
    {
        int no = Pick(q, "carNo");
        int junk = Pick(q, "junkCarNo");
        string cls = GetS(q, "compensateClass");
        if (cls == "") cls = ClassOf(no);
        Hashtable b = Auto("/shop/car/compensate");
        b["missions"] = new ArrayList();
        if (carClass.ContainsKey(no) && owned.ContainsKey(junk) && junk != no)
        {
            // 값은 **화면과 같은 셈법**으로 매깁니다. 화면은 우리가 준
            // 등급표로 정가를 잡고 헌 차 값을 뺍니다. 차값으로 매기면
            // 화면에 106 이 떠 놓고 46 만 깎여 어긋납니다.
            Hashtable cv = GetH(D, "tradeClassValue");
            long full;
            if (cv != null && cv.ContainsKey(cls))
            {
                full = Convert.ToInt64(cv[cls]);
            }
            else
            {
                ArrayList cost = Get(GetH(D, "carCost"), no.ToString()) as ArrayList;
                full = (cost != null && cost.Count > 1)
                       ? Convert.ToInt64(cost[1]) : 0;
            }
            long price = full - TradeValue(junk);
            if (price < 0) price = 0;
            if (trophy >= price)
            {
                trophy -= price;
                owned.Remove(junk);
                SetTune(junk, "carAccel", 0);
                SetTune(junk, "carSpeed", 0);
                SetTune(junk, "carFuleCost", 0);
                owned[no] = true;
                if (IsClass(cls)) carClass[no] = cls;
            }
        }
        b["remainTrophyCnt"] = trophy;
        b["carSeq"] = (long)(no + 1);
        return b;
    }

    // ================================================================ 관문
    static string Normalize(string url)
    {
        if (url == null) return "/";
        int qm = url.IndexOf('?');
        if (qm >= 0) url = url.Substring(0, qm);
        ArrayList roots = GetA(D, "knownRoots");
        if (roots != null)
        {
            for (int k = 0; k < roots.Count; k++)
            {
                string r = Convert.ToString(roots[k]);
                int i = url.IndexOf(r);
                if (i > 0) { url = url.Substring(i); break; }
            }
        }
        while (url.Length > 1 && url.EndsWith("/"))
            url = url.Substring(0, url.Length - 1);
        return url;
    }

    /// {"xxxReq": {...}} 한 겹을 벗긴다.
    static Hashtable Unwrap(Hashtable req)
    {
        if (req != null && req.Count == 1)
        {
            foreach (DictionaryEntry e in req)
            {
                Hashtable inner = e.Value as Hashtable;
                if (inner != null) return inner;
            }
        }
        return req == null ? new Hashtable() : req;
    }

    /// 로그를 남긴다. logcat 에서 [ChaLocal] 로 걸러 보면 오간 것이 다 보인다.
    public static bool Trace = true;

    static string lastUrl = "", lastBody = "";
    static readonly Hashtable answers = new Hashtable();
    static readonly ArrayList order = new ArrayList();
    static string dummyPath;

    /// SendPacket 이 들어오자마자 부른다. 여기서는 받아 두기만 한다.
    public static void Note(string url, string body)
    {
        Ensure();                       // 겹판은 어느 판에서든 띄운다
        if (!IsLocal()) return;         // 그 밖에는 서버판이면 손 안 댄다
        lastUrl = url;
        lastBody = body;
    }

    /// SendPacket 안의 `new WWW(...)` 자리. 통신하지 않고 답을 미리 만들어 둔다.
    public static WWW MakeWWW(string url, byte[] data, Hashtable headers)
    {
        // 서버판이면 원래 하던 대로 진짜 통신을 한다. 이 WWW 는 우리 표에
        // 없으므로 아래 Text · Err 도 진짜 값을 그대로 돌려준다.
        if (!IsLocal()) return new WWW(url, data, headers);

        string answer;
        try
        {
            Boot();
            string path = Normalize(lastUrl.Length > 0 ? lastUrl : url);
            Hashtable req = Unwrap(Jp.Parse(lastBody) as Hashtable);
            Hashtable res = Route(path, req);
            Persist();
            answer = Write(res);
            if (Trace)
                Debug.Log("[ChaLocal] " + path + "  ->  "
                          + (answer.Length > 1200 ? answer.Substring(0, 1200) : answer));
        }
        catch (Exception e)
        {
            Debug.LogError("[ChaLocal] " + e);
            answer = "{\"success\":false,\"errorCode\":\"LOCAL\"}";
        }
        WWW w = Dummy();
        answers[w] = answer;
        order.Add(w);
        while (order.Count > 24)
        {
            answers.Remove(order[0]);
            order.RemoveAt(0);
        }
        return w;
    }

    /// 곧바로 끝나는 가짜 요청. 폰 안의 파일을 읽게 해 한두 프레임에 끝난다.
    static WWW Dummy()
    {
        if (dummyPath == null)
        {
            dummyPath = Application.persistentDataPath + "/cha.dummy";
            try
            {
                if (!File.Exists(dummyPath))
                {
                    using (FileStream fs = new FileStream(dummyPath,
                            FileMode.Create, FileAccess.Write))
                        fs.WriteByte((byte)'1');
                }
            }
            catch (Exception e) { Debug.Log("[ChaLocal] " + e.Message); }
        }
        return new WWW("file://" + dummyPath);
    }

    /// www.text 자리. 우리가 만든 것이면 우리 답을, 아니면 진짜 내용을 준다.
    public static string Text(WWW w)
    {
        if (w != null && answers.ContainsKey(w))
            return Convert.ToString(answers[w]);
        return w == null ? "" : w.text;
    }

    /// www.error 자리. 우리가 만든 것은 늘 성공이다.
    public static string Err(WWW w)
    {
        if (w != null && answers.ContainsKey(w)) return null;
        return w == null ? null : w.error;
    }

    /// 복원 자산 번들(pack.unity3d) 자리.
    ///
    /// 서버판은 PC 에서 받아 왔다. 로컬판은 APK 안(StreamingAssets)에 넣어
    /// 두고 거기서 읽는다. 안드로이드에서는 streamingAssetsPath 가
    /// `jar:file://…apk!/assets` 라서 WWW 로 그대로 열린다.
    public static WWW BundleWWW(string url)
    {
        // 서버판은 PC 에서 받아 온다(주소는 자산에 박혀 있다).
        // 로컬판은 APK 안 StreamingAssets 에서 읽는다. 안드로이드에서는
        // streamingAssetsPath 가 `jar:file://…apk!/assets` 라 WWW 로 열린다.
        if (!IsLocal()) return new WWW(url);
        return new WWW(Application.streamingAssetsPath + "/pack.unity3d");
    }

    /// Aes.Decrypt 자리. 로컬판의 답은 처음부터 평문이다.
    public static string Dec(object aes, string s) { return s; }
}


/// 게임 위에 그리는 **세이브 칸 관리 겹판**.
///
/// NGUI 프리팹을 하나도 안 건드립니다. Unity 의 구식 `OnGUI` 로만 그리므로
/// 자산 쪽 위험이 없습니다.
///
/// 두 가지가 이 화면의 모양을 정했습니다(둘 다 실측입니다).
///
///  · **한글이 안 나옵니다.** 이 빌드의 글꼴은 `Arial` 하나인데 한글
///    글리프가 없고 시스템 글꼴로 대체되지도 않습니다. 그래서 이름 대신
///    **숫자로** 보여 줍니다 — 골드 · 트로피 · 차 수 · 드라이버 수.
///    오히려 어느 판인지 알아보기 쉽습니다.
///  · **글자 크기를 못 키웁니다.** `UnityEngine.dll` 이 깎여 있어
///    `GUIStyle.fontSize` 가 아예 없습니다. 대신 `GUI.matrix` 로 화면
///    전체를 키웁니다.
///
/// 칸은 세이브 파일 옆에 `slotNN.json` 으로 둡니다. 살아 있는 판은 늘
/// `chasave.json` 이고, 불러오기는 그 위에 덮어쓰는 것입니다.
public class ChaLocalUI : MonoBehaviour
{
    const float SCALE = 2.6f;
    const int SLOTS = 6;
    const float PW = 470, PH = 278;

    bool open;
    string[] info = new string[SLOTS + 1];
    string note = "";

    // 누른 자리는 **직접** 받습니다. `GUI.Button` 의 반환값은 이 빌드에서
    // 손가락 입력에 반응하지 않았습니다(그림은 나오는데 눌리지 않습니다).
    // 그래서 그리기와 누르기를 갈라, 자리 비교는 우리가 합니다.
    Rect rTab, rClose, rMode;
    Rect[] rSave = new Rect[SLOTS + 1];
    Rect[] rLoad = new Rect[SLOTS + 1];
    Rect[] rDel = new Rect[SLOTS + 1];

    void Start() { Rescan(); Layout(); }

    string Dir()
    {
        string p = ChaLocal.SaveFile();
        int i = p.LastIndexOf('/');
        return i < 0 ? "." : p.Substring(0, i);
    }

    string SlotPath(int n)
    {
        return Dir() + "/slot" + (n < 10 ? "0" : "") + n + ".json";
    }

    void Rescan()
    {
        info[0] = ChaLocal.SlotSummary(ChaLocal.SaveFile());
        for (int i = 1; i <= SLOTS; i++)
            info[i] = ChaLocal.SlotSummary(SlotPath(i));
    }

    void Copy(string from, string to)
    {
        ChaLocal.WriteText(to, ChaLocal.ReadText(from));
    }

    float SW { get { return Screen.width / SCALE; } }
    float SH { get { return Screen.height / SCALE; } }

    void Layout()
    {
        rTab = new Rect(4, SH - 26, 52, 22);
        float w = PW, h = PH;
        float x = (SW - w) / 2, y = (SH - h) / 2;
        rClose = new Rect(x + w - 58, y + 4, 50, 20);
        rMode = new Rect(x + w - 160, y + h - 50, 150, 20);
        float row = y + 48;
        for (int i = 1; i <= SLOTS; i++)
        {
            rSave[i] = new Rect(x + w - 160, row - 2, 46, 20);
            rLoad[i] = new Rect(x + w - 110, row - 2, 46, 20);
            rDel[i] = new Rect(x + w - 60, row - 2, 46, 20);
            row += 26;
        }
    }

    /// 누른 자리를 받습니다. **손가락 입력을 먼저** 봅니다 — 이 빌드에서
    /// `GUI.Button` 도 `GetMouseButtonDown` 도 손가락에 반응하지 않았습니다.
    bool Pressed(out Vector2 pos)
    {
        pos = Vector2.zero;
        if (Input.touchCount > 0)
        {
            Touch t = Input.GetTouch(0);
            if (t.phase != TouchPhase.Began) return false;
            pos = t.position;
            return true;
        }
        if (Input.GetMouseButtonDown(0))
        {
            Vector3 m = Input.mousePosition;
            pos = new Vector2(m.x, m.y);
            return true;
        }
        return false;
    }


    void Update()
    {
        Vector2 hit;
        if (!Pressed(out hit)) return;
        Layout();
        // 입력은 왼쪽 **아래**가 원점, GUI 는 왼쪽 **위**가 원점입니다.
        float gx = hit.x / SCALE, gy = (Screen.height - hit.y) / SCALE;
        if (!open)
        {
            if (rTab.Contains(new Vector2(gx, gy))) { Rescan(); open = true; }
            return;
        }
        Vector2 p = new Vector2(gx, gy);
        if (rClose.Contains(p)) { open = false; return; }
        for (int i = 1; i <= SLOTS; i++)
        {
            if (rSave[i].Contains(p))
            {
                ChaLocal.FlushSave();
                Copy(ChaLocal.SaveFile(), SlotPath(i));
                note = "slot " + i + " saved";
                Rescan();
                return;
            }
            if (rLoad[i].Contains(p) && File.Exists(SlotPath(i)))
            {
                Copy(SlotPath(i), ChaLocal.SaveFile());
                note = "loaded slot " + i;
                Rescan();
                Application.Quit();
                return;
            }
            if (rDel[i].Contains(p) && File.Exists(SlotPath(i)))
            {
                File.Delete(SlotPath(i));
                note = "slot " + i + " deleted";
                Rescan();
                return;
            }
        }
        if (rMode.Contains(p))
        {
            // 서버판 <-> 로컬판. 갈고리들이 켤 때 한 번만 읽는 자리가 있어
            // 바로는 안 바뀐다 — 앱을 껐다 켜야 한다. LOAD 와 같은 사정이다.
            ChaLocal.SetMode(ChaLocal.IsLocal() ? ChaLocal.SERVER
                                                : ChaLocal.LOCAL);
            note = "mode -> " + ChaLocal.Mode + " (restart)";
            return;
        }
    }

    void OnGUI()
    {
        Matrix4x4 keep = GUI.matrix;
        GUI.matrix = Matrix4x4.TRS(Vector3.zero, Quaternion.identity,
                                   new Vector3(SCALE, SCALE, 1f));
        if (!open)
        {
            GUI.Box(rTab, "SAVE");
            GUI.matrix = keep;
            return;
        }
        float w = PW, h = PH;
        float x = (SW - w) / 2, y = (SH - h) / 2;
        // 판을 **불투명하게**. 이 빌드의 Texture2D 에는 SetPixel 도 생성자도
        // 없어서 단색 판을 못 만듭니다. 대신 반투명 상자를 여러 겹 포갭니다.
        Rect box = new Rect(x, y, w, h);
        for (int k = 0; k < 7; k++) GUI.Box(box, "");
        GUI.Label(new Rect(x + 10, y + 6, w - 90, 18), "SAVE SLOTS");
        GUI.Box(rClose, "CLOSE");
        GUI.Label(new Rect(x + 10, y + 26, w - 20, 18), "NOW  " + info[0]);
        float row = y + 48;
        for (int i = 1; i <= SLOTS; i++)
        {
            GUI.Label(new Rect(x + 10, row, 300, 18), i + "  " + info[i]);
            GUI.Box(rSave[i], "SAVE");
            bool has = File.Exists(SlotPath(i));
            GUI.Box(rLoad[i], has ? "LOAD" : "-");
            GUI.Box(rDel[i], has ? "DEL" : "-");
            row += 26;
        }
        GUI.Label(new Rect(x + 10, y + h - 50, w - 170, 18),
                  "MODE  " + ChaLocal.Mode.ToUpper());
        GUI.Box(rMode, ChaLocal.IsLocal() ? "USE SERVER" : "USE LOCAL");
        GUI.Label(new Rect(x + 10, y + h - 30, w - 20, 18), note);
        GUI.Label(new Rect(x + 10, y + h - 16, w - 20, 18),
                  "LOAD and MODE close/need a restart to take effect.");
        GUI.matrix = keep;
    }
}
