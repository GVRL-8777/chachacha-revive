# AXML(이진 AndroidManifest.xml)을 사람이 읽을 수 있게 푼다.
import sys, struct

def u32(b,o): return struct.unpack_from('<I',b,o)[0]
def u16(b,o): return struct.unpack_from('<H',b,o)[0]

ATTRS = {
0x01010000:'theme',0x01010001:'label',0x01010002:'icon',0x01010003:'name',
0x01010004:'manageSpaceActivity',0x01010005:'allowClearUserData',
0x01010006:'permission',0x01010007:'readPermission',0x01010008:'writePermission',
0x01010009:'protectionLevel',0x0101000a:'permissionGroup',0x0101000b:'sharedUserId',
0x0101000c:'hasCode',0x0101000d:'persistent',0x0101000e:'enabled',
0x0101000f:'debuggable',0x01010010:'exported',0x01010011:'process',
0x01010012:'taskAffinity',0x01010013:'multiprocess',
0x01010018:'authorities',0x0101001e:'value',0x01010020:'value2',
0x01010024:'value3',0x01010026:'value4',
0x0101021b:'versionCode',0x0101021c:'versionName',
0x0101020c:'minSdkVersion',0x01010270:'targetSdkVersion',
0x010102b2:'installLocation',0x01010604:'usesCleartextTraffic',
0x01010280:'allowBackup',0x010102d3:'largeHeap',
0x0101027e:'screenOrientation',0x0101055f:'extractNativeLibs',
0x01010603:'networkSecurityConfig',0x01010392:'supportsRtl',
0x0101028e:'required',0x010100d0:'glEsVersion',
0x0101026f:'configChanges',0x01010207:'scheme',
}

def parse(path):
    b = open(path,'rb').read()
    assert u16(b,0)==0x0003
    # find string pool chunk at 8
    off = 8
    assert u16(b,off)==0x0001, hex(u16(b,off))
    sp_size = u32(b,off+4); sc = u32(b,off+8); styc = u32(b,off+12)
    flags = u32(b,off+16); strstart = u32(b,off+20)
    utf8 = bool(flags & (1<<8))
    offs = [u32(b,off+28+4*i) for i in range(sc)]
    strings=[]
    for o in offs:
        p = off+strstart+o
        if utf8:
            n = b[p]
            if n & 0x80: n = ((n&0x7f)<<8)|b[p+1]; p+=2
            else: p+=1
            n2 = b[p]
            if n2 & 0x80: n2=((n2&0x7f)<<8)|b[p+1]; p+=2
            else: p+=1
            strings.append(b[p:p+n2].decode('utf-8','replace'))
        else:
            n = u16(b,p); p+=2
            if n & 0x8000: n = ((n&0x7fff)<<16)|u16(b,p); p+=2
            strings.append(b[p:p+n*2].decode('utf-16-le','replace'))
    pos = off+sp_size
    resmap=[]
    out=[]
    depth=0
    ns={}
    while pos < len(b):
        t = u16(b,pos); hs=u16(b,pos+2); sz=u32(b,pos+4)
        if sz==0: break
        if t==0x0180:  # RES_XML_RESOURCE_MAP
            resmap=[u32(b,pos+8+4*i) for i in range((sz-8)//4)]
        elif t==0x0102:  # START ELEMENT
            nsi=u32(b,pos+16); nm=u32(b,pos+20)
            astart=u16(b,pos+24); asize=u16(b,pos+26); acount=u16(b,pos+28)
            name = strings[nm]
            line = '  '*depth + '<'+name
            ap = pos+hs+astart
            for i in range(acount):
                a = ap + i*asize
                a_ns=u32(b,a); a_nm=u32(b,a+4); a_raw=u32(b,a+8)
                a_type=b[a+15]; a_data=u32(b,a+16)
                an = strings[a_nm]
                if a_nm < len(resmap) and resmap[a_nm] in ATTRS:
                    an = ATTRS[resmap[a_nm]]
                elif a_nm < len(resmap):
                    an = an or ('res_0x%08x'%resmap[a_nm])
                if a_raw != 0xFFFFFFFF:
                    v = strings[a_raw]
                elif a_type==0x12: v = 'true' if a_data else 'false'
                elif a_type==0x10: v = str(struct.unpack('<i',struct.pack('<I',a_data))[0])
                elif a_type==0x11: v = hex(a_data)
                elif a_type==0x01: v = '@0x%08x'%a_data
                elif a_type==0x03: v = strings[a_data]
                else: v = '0x%08x(t%d)'%(a_data,a_type)
                pref = 'android:' if a_ns!=0xFFFFFFFF else ''
                line += '\n'+'  '*(depth+1)+pref+an+'="'+v+'"'
            out.append(line+'>')
            depth+=1
        elif t==0x0103:
            depth-=1
            nm=u32(b,pos+20)
            out.append('  '*depth+'</'+strings[nm]+'>')
        elif t==0x0104:  # RES_XML_CDATA
            di=u32(b,pos+16)
            if di < len(strings) and strings[di].strip():
                out.append('  '*depth+'>>> '+strings[di].strip())
        pos += sz
    return '\n'.join(out)

print(parse(sys.argv[1]))
