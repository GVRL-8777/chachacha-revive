# APK 서명(MANIFEST.MF · CERT.SF)의 해시가 맞는지 검산한다.
from _here import apk as _apk
import zipfile, hashlib, base64, re, sys, struct

apk = _apk('kr')
z = zipfile.ZipFile(apk)

mf = z.read('META-INF/MANIFEST.MF').decode('utf-8','replace')
sf = z.read('META-INF/CERT.SF').decode('utf-8','replace')

def parse_sections(text):
    # unfold continuation lines (leading space)
    text = text.replace('\r\n','\n').replace('\r','\n')
    text = re.sub(r'\n ', '', text)
    secs = [s for s in text.split('\n\n') if s.strip()]
    out=[]
    for s in secs:
        d={}
        for line in s.split('\n'):
            if ':' in line:
                k,v=line.split(':',1); d[k.strip()]=v.strip()
        out.append(d)
    return out

mfsecs = parse_sections(mf)
print("MANIFEST.MF main attrs:", mfsecs[0])
mfentries = {s['Name']: s for s in mfsecs[1:] if 'Name' in s}
print("MANIFEST.MF entry count:", len(mfentries))

sfsecs = parse_sections(sf)
print("CERT.SF main attrs:", {k:v for k,v in sfsecs[0].items()})
sfentries = {s['Name']: s for s in sfsecs[1:] if 'Name' in s}
print("CERT.SF entry count:", len(sfentries))

zipnames = [n for n in z.namelist() if not n.startswith('META-INF/')]
zipset = set(zipnames)
print("APK entries (non-META-INF):", len(zipnames))

missing = sorted(set(mfentries) - zipset)      # signed but not present
extra   = sorted(zipset - set(mfentries))      # present but not signed
print("\n### SIGNED-BUT-MISSING FROM APK: %d" % len(missing))
for n in missing[:40]: print("   ", n)
if len(missing)>40: print("    ...")
print("\n### PRESENT-BUT-NOT-SIGNED (would be tampering): %d" % len(extra))
for n in extra: print("   ", n)

# digest check
bad=[]; ok=0
for name in zipnames:
    if name not in mfentries: continue
    ent = mfentries[name]
    dk = [k for k in ent if k.endswith('-Digest')]
    if not dk: continue
    alg = dk[0].replace('-Digest','').upper().replace('-','')
    data = z.read(name)
    h = hashlib.new({'SHA1':'sha1','SHA256':'sha256','MD5':'md5'}[alg], data).digest()
    if base64.b64encode(h).decode() != ent[dk[0]]:
        bad.append(name)
    else:
        ok+=1
print("\n### CONTENT DIGEST: %d verified OK, %d MISMATCH" % (ok, len(bad)))
for n in bad[:40]: print("    MISMATCH:", n)

# CERT.SF -> MANIFEST.MF digest
raw_mf = z.read('META-INF/MANIFEST.MF')
for k,v in sfsecs[0].items():
    if k.endswith('-Digest-Manifest') and 'Main' not in k:
        alg = k.split('-')[0].lower().replace('sha','sha')
        alg = {'sha1':'sha1','sha-256':'sha256','sha256':'sha256'}.get(alg,'sha1')
        calc = base64.b64encode(hashlib.new(alg, raw_mf).digest()).decode()
        print("\n### CERT.SF %s: %s" % (k, "MATCH" if calc==v else "MISMATCH (calc=%s expect=%s)"%(calc,v)))

# per-entry SF digests over manifest sections
raw = raw_mf.replace(b'\r\n',b'\n').replace(b'\r',b'\n')
secs_raw = raw.split(b'\n\n')
secmap={}
for s in secs_raw[1:]:
    m = re.search(rb'Name: (.+)', s.replace(b'\n ',b''))
    if m: secmap[m.group(1).decode()] = s + b'\n\n'
sfbad=0; sfok=0
for name, ent in sfentries.items():
    dk=[k for k in ent if k.endswith('-Digest')]
    if not dk or name not in secmap: continue
    calc = base64.b64encode(hashlib.sha1(secmap[name]).digest()).decode()
    if calc==ent[dk[0]]: sfok+=1
    else: sfbad+=1
print("### CERT.SF per-entry section digests: %d ok, %d mismatch" % (sfok, sfbad))

# APK Signing Block (v2/v3)
raw_apk = open(apk,'rb').read()
idx = raw_apk.rfind(b'APK Sig Block 42')
print("\n### APK Signing Block v2/v3 magic present:", idx != -1)
print("### 'Android' zip comment / v2 scheme:", b'APK Sig Block 42' in raw_apk)
