try:
    import ustruct as struct
    import uio
    import hpprime
except ImportError:
    import struct
    import io as uio

from primec import compile_c, CompileError

APP_DIR = "C:\\DATA\\PRIMEC.hpappdir"
SOURCE_FILE = "ccode.py"
OUTPUT_ELF = "ccode.elf"

BASE = 0x307FBCAC
def get_addr(int_id):
    return BASE + 0xC * (int_id - 0x10000)
ADDR_MALLOC = get_addr(0x10037)
ADDR_FREE   = get_addr(0x1003A)

class PrimeDebug:
    def __init__(self, filename='debug'):
        try: self.f=uio.FileIO('debug')
        except: self.f=open(filename,'rb')
        print('[+] Debug interface opened.')
    def close(self):
        if self.f: self.f.close()
    def write_mem(self,addr,val): self.f.write(struct.pack('<III',1,addr,val))
    def read_mem(self,addr,size):
        self.f.write(struct.pack('<III',0,addr,0)); return self.f.read(size)
    def call(self,func_addr,*args):
        n=len(args); fmt='<III'+'I'*n; buf=bytearray(struct.calcsize(fmt)); struct.pack_into(fmt,buf,0,2,func_addr,n,*args); self.f.write(buf); return struct.unpack_from('<I',buf,0)[0]
    def write_mem_bytes(self,addr,data):
        pad=(4-len(data)%4)%4; data=data+b'\0'*pad
        for i in range(0,len(data),4): self.write_mem(addr+i,struct.unpack('<I',data[i:i+4])[0])

class ElfTools:
    @staticmethod
    def read_ccode(path):
        with uio.FileIO(path,'rb') as f: b=f.read()
        try: s=b.decode('utf-8')
        except: s=''.join(chr(x) for x in b)
        a=s.find('/* PRIME-C-CODE-BEGIN */'); z=s.find('/* PRIME-C-CODE-END */')
        if a<0 or z<0 or z<=a: raise CompileError('ccode.py needs PRIME-C-CODE-BEGIN/END markers')
        return s[a+len('/* PRIME-C-CODE-BEGIN */'):z]
    @staticmethod
    def write_file(path,data):
        with uio.FileIO(path,'wb') as f: f.write(data)
    @staticmethod
    def memory_size(path):
        with uio.FileIO(path,'rb') as f:
            h=f.read(52)
            if len(h)<52 or h[:4]!=b'\x7fELF': return 0
            phoff=struct.unpack_from('<I',h,28)[0]; ents=struct.unpack_from('<H',h,42)[0]; num=struct.unpack_from('<H',h,44)[0]
            f.seek(phoff); m=0
            for i in range(num):
                p=f.read(ents); typ=struct.unpack_from('<I',p,0)[0]
                if typ==1:
                    v=struct.unpack_from('<I',p,8)[0]; z=struct.unpack_from('<I',p,20)[0]; m=max(m,v+z)
            return (m+3)&~3
    @staticmethod
    def utf16le(s):
        b=bytearray()
        for c in s:
            v=ord(c); b.append(v&255); b.append((v>>8)&255)
        b.extend(b'\0\0'); return bytes(b)

class Loader:
    def __init__(self,dbg): self.dbg=dbg; self.loader_addr=0; self.elf_base=0; self.entry=0
    loader_code = b'\x0b\x00\x00\xea\x04\x00-\xe5\x04\xe0-\xe5o\x02\x01\xef\x04\x00-\xe5\x04\xe0-\xe5\xca\x00\x01\xef\x04\x00-\xe5\x04\xe0-\xe5\xd4\x00\x01\xef\x04\x00-\xe5\x04\xe0-\xe5\xcf\x00\x01\xefh2\x9f\xe5\xf0O-\xe9\x030\x8f\xe0\x00 \xa0\xe1\x01`\xa0\xe1\x03\x00\x93\xe8d\xd0M\xe2\x04\x00\x8d\xe5\xb8\x10\xcd\xe1\x02\x00\xa0\xe1\x04\x10\x8d\xe2\xe7\xff\xff\xeb\x00@P\xe2s\x00\x00\n\x040\xa0\xe1\x01 \xa0\xe34\x10\xa0\xe3,\x00\x8d\xe2\xe6\xff\xff\xeb\x01\x00P\xe3j\x00\x00\x1a\xbc"\xdd\xe1\x142\x9f\xe5\x03\x00R\xe1f\x00\x00\x1aH\x10\x9d\xe5\x00 \xa0\xe3\x04\x00\xa0\xe1\xdf\xff\xff\xeb\xb85\xdd\xe1\x00\x00S\xe3x\x00\x00\n\x00P\xa0\xe3\x05p\xa0\xe1\x0c\xa0\x8d\xe2\x04\x00\x00\xea\xb85\xdd\xe1\x02\x00[\xe3\x14p\x9d\x05\x05\x00S\xe1\x19\x00\x00\xda\x040\xa0\xe1\x01 \xa0\xe3 \x10\xa0\xe3\n\x00\xa0\xe1\xcb\xff\xff\xeb\x0c\xb0\x9d\xe5\x01P\x85\xe2\x01\x00[\xe3\xf1\xff\xff\x1a\x1c0\x9d\xe5\x14\x80\x9d\xe5H\x90\x9d\xe5\x00\x00S\xe3\x08\x80\x86\xe0\x85\x92\x89\xe0K\x00\x00\x1a  \x9d\xe5\x03\x00R\xe1U\x00\x00\x8a\t\x10\xa0\xe1\x00 \xa0\xe3\x04\x00\xa0\xe1\xbc\xff\xff\xeb\xb85\xdd\xe1\x05\x00S\xe1\xe5\xff\xff\xca\x04\x00\xa0\xe1\xb1\xff\xff\xeb\x00\x00W\xe3/\x00\x00\n\x070\x96\xe7\x07p\x86\xe0\x00\x00S\xe3+\x00\x00\n\x00 \xa0\xe3\x08\xc0\xa0\xe3\x02\x00\xa0\xe1\x02\xe0\xa0\xe1\x11\x00S\xe3\x04\xe0\x97\x05\x04\x00\x00\n\x12\x00S\xe3\x04\x00\x97\x05\x01\x00\x00\n\x13\x00S\xe3\x04\xc0\x97\x05\x080\xb7\xe5\x01 \x82\xe2\x00\x00S\xe3d\x00R\x13\x01\x10\xa0\x13\x00\x10\xa0\x03\xf0\xff\xff\x1a\x00\x00^\xe3\x00\x00P\x13\x15\x00\x00\n\x00\x00\\\xe3\x08\xc0\xa0\x03\x0c\x00P\xe1\x11\x00\x00:\x0c\x00@\xe0\x00\x00\\\xe1\x01\x10\x81\xe2\xfb\xff\xff\x9a\x00\x00Q\xe3\x0b\x00\x00\n\x81\x11\x86\xe0\x0e0\x86\xe0\x0e\x10\x81\xe0\x04 \xd3\xe5\x080\x83\xe2\x17\x00R\xe3\x08\x00\x13\x05\x00 \x96\x07\x02 \x86\x00\x00 \x86\x07\x01\x00S\xe1\xf6\xff\xff\x1a\x000\xa0\xe3~\xff\x17\xee\xfd\xff\xff\x1a\x9a?\x07\xee\x15?\x07\xeeD0\x9d\xe5\x03\x00\x86\xe0d\xd0\x8d\xe2\xf0\x8f\xbd\xe8\x04\x00\xa0\xe1t\xff\xff\xeb\x00\x00\xa0\xe3d\xd0\x8d\xe2\xf0\x8f\xbd\xe8\x10\x10\x9d\xe5\x00 \xa0\xe3\x04\x00\xa0\xe1s\xff\xff\xeb\x1c \x9d\xe5\x040\xa0\xe1\x0b\x10\xa0\xe1\x08\x00\xa0\xe1k\xff\xff\xeb\x1c0\x9d\xe5  \x9d\xe5\x03\x00R\xe1\xa9\xff\xff\x9a\x030\x88\xe0\x02\x80\x88\xe0\x00 \xa0\xe3\x01 \xc3\xe4\x08\x00S\xe1\xfc\xff\xff\x1a\xa2\xff\xff\xea\x04\x00\xa0\xe1[\xff\xff\xeb\xda\xff\xff\xeah\x02\x00\x00\x7fE\x00\x00r\x00b\x00\x00\x00'
    def upload(self):
        self.loader_addr=self.dbg.call(ADDR_MALLOC,(len(self.loader_code)+3)&~3)
        if not self.loader_addr: return False
        self.dbg.write_mem_bytes(self.loader_addr,self.loader_code); return True
    def load(self,filename):
        ms=ElfTools.memory_size(filename)
        if not ms: raise CompileError('compiled ELF has invalid program headers')
        self.elf_base=self.dbg.call(ADDR_MALLOC,ms)
        if not self.elf_base: raise CompileError('target malloc failed')
        path=APP_DIR+'\\'+filename
        pb=ElfTools.utf16le(path); pa=self.dbg.call(ADDR_MALLOC,len(pb)); self.dbg.write_mem_bytes(pa,pb)
        try:
            self.entry=self.dbg.call(self.loader_addr,pa,self.elf_base)
        finally:
            self.dbg.call(ADDR_FREE,pa)
        if self.entry<0x30000000: raise CompileError('ELF loader returned invalid entry 0x%08X'%self.entry)
        return self.entry
    def unload(self):
        if self.elf_base: self.dbg.call(ADDR_FREE,self.elf_base); self.elf_base=0
        if self.loader_addr: self.dbg.call(ADDR_FREE,self.loader_addr); self.loader_addr=0

def compile_source():
    src=ElfTools.read_ccode(SOURCE_FILE)
    print('[*] C source bytes:',len(src))
    elf=compile_c(src)
    ElfTools.write_file(OUTPUT_ELF,elf)
    print('[+] Wrote',OUTPUT_ELF,len(elf),'bytes')
    print('[+] Load image:',ElfTools.memory_size(OUTPUT_ELF),'bytes')

def run_compiled():
    dbg=None; ld=None
    try:
        dbg=PrimeDebug(); ld=Loader(dbg)
        if not ld.upload(): raise CompileError('failed to upload ELF loader')
        entry=ld.load(OUTPUT_ELF)
        print('[*] Entry = 0x%08X'%entry)
        ret=dbg.call(entry,0,0)
        print('[+] Program returned',ret)
        # printf() output: the compiler places a log ring
        # { magic[8]="PRIMELOG", count, data[4096] } in the image; scan the
        # ELF file for the magic to locate it and print what was written.
        try:
            elf_bytes=open(OUTPUT_ELF,'rb').read()
            mi=elf_bytes.find(b'PRIMELOG')
            if mi>=0:
                ring=ld.elf_base+(mi-0x1000)
                cnt=struct.unpack_from('<I',bytes(dbg.read_mem(ring+8,4)))[0]
                if cnt>0:
                    cnt=min(cnt,4096)
                    out=bytes(dbg.read_mem(ring+12,cnt)).decode('utf-8','ignore')
                    if out:
                        print('--- program output ---')
                        print(out,end='')
                        if out[-1:]!='\n': print()
        except Exception:
            pass
        # convenience: if the returned value is a pointer into the loaded
        # image, show what it points at - a string literal or a global
        # array. (Arrays decay to their first element's address in C, so
        # `return arr;` yields the address, not the contents.)
        try:
            size=ElfTools.memory_size(OUTPUT_ELF)
            if ld.elf_base and ld.elf_base <= ret < ld.elf_base+size:
                raw=bytes(dbg.read_mem(ret,64))
                s=raw.split(b'\x00')[0].decode('utf-8','ignore')
                if s and all(32<=ord(c)<127 for c in s):
                    print('[+] returned string: "%s"'%s)
                else:
                    words=[]
                    for i in range(0, min(len(raw),64)//4):
                        words.append(struct.unpack_from('<I',raw,i*4)[0])
                    print('[+] returned array/pointer: first words',words)
            elif ret >= 0x30000000:
                print('[+] (value looks like an address outside the image - e.g. a local array; its frame is gone)')
        except Exception:
            pass
    finally:
        if ld: ld.unload()
        if dbg: dbg.close()

def main():
    print('--- PrimeC ---')
    try: compile_source()
    except Exception as e:
        print('[C ERROR]',e); return
    try: run_compiled()
    except Exception as e:
        print('[RUN ERROR]',e)

main()
