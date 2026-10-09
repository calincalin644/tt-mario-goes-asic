"""Exercise erase/rewrite and preservation against an emulated NOR flash."""
import hashlib,importlib.util,io,sys,tempfile,types,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
memory=bytearray(b'\xff'*(1<<24));writes=[]
class Flash:
    def __init__(self):self.spi=types.SimpleNamespace(init=lambda **kw:None);self.wel=False
    def read(self,address,length):return bytes(memory[address:address+length])
    def ready(self):pass
    def close(self):pass
    def cmd(self,header,length=0,data=None):
        op=header[0]
        if op==6:self.wel=True
        elif op==5:return bytes([2 if self.wel else 0])
        elif op in (2,0x20):
            assert self.wel;self.wel=False
            address=int.from_bytes(header[1:],'big')
            if op==0x20:
                assert address%4096==0
                memory[address:address+4096]=b'\xff'*4096
                writes.append(('erase',address))
            else:
                assert len(data)<=256 and address//256==(address+len(data)-1)//256
                for i,v in enumerate(data):memory[address+i]&=v
                writes.append(('program',address))
        else:raise AssertionError(op)
events=[]
progress=types.SimpleNamespace(open_flash=Flash,update=lambda *args,**kw:events.append((args,kw)),fail=lambda:events.append(('error',{})))
sys.modules['flash_progress']=progress
sys.modules['flash_pmod']=types.SimpleNamespace(Flash=Flash,digest=lambda data:hashlib.sha256(data).hexdigest())
sys.modules['deflate']=types.SimpleNamespace(ZLIB=0,DeflateIO=lambda f,mode:io.BytesIO(zlib.decompress(f.read())))
spec=importlib.util.spec_from_file_location('updater',ROOT/'scripts/levels_flash.py');updater=importlib.util.module_from_spec(spec);spec.loader.exec_module(updater)
def reject(call):
    try:call()
    except RuntimeError:return
    raise AssertionError('must reject')
with tempfile.TemporaryDirectory() as temp:
    path=Path(temp)/'asset.zlib'
    for logical,length in ((0xc00000,8192),(0xe00000,256),(0x090000,4096),(0x800000,4096),(0x830000,4096),(0x940000,4096),(0xf80000,4096)):
        physical=updater.physical(logical)
        old=b'\x00'*length;new=bytes((n*7+11)%256 for n in range(length))
        memory[physical:physical+length]=old
        # Match the owned old asset before allowing any erase.
        reject(lambda:updater.verify_region(logical,length,'wrong'))
        updater.verify_region(logical,length,hashlib.sha256(old).hexdigest())
        if length==256:
            memory[physical+256]=0
            reject(lambda:updater.verify_region(logical,length,hashlib.sha256(old).hexdigest()))
            memory[physical+256]=255
        compressed=zlib.compress(new);path.write_bytes(compressed)
        updater.program_zlib(str(path),hashlib.sha256(compressed).hexdigest(),logical,length,hashlib.sha256(new).hexdigest())
        assert memory[physical:physical+length]==new
        assert memory[physical+length]==255
        assert events[-1][0]==(3,length,length,0x800000<=logical<0xc00000) and events[-1][1].get('complete')
        count=len(writes)
        updater.program_zlib(str(path),hashlib.sha256(compressed).hexdigest(),logical,length,hashlib.sha256(new).hexdigest())
        assert len(writes)==count # safe resume skips already complete sectors
    for address in (0x400000,0x080000,0x110000,0x1b0000,0x200000,0x2e0000,0x5f0000,0x820000,0xad0000,0xb10000,0xff0000):
        assert not updater.allowed(address,4096,writing=True)
        reject(lambda:updater.program_zlib(str(path),hashlib.sha256(compressed).hexdigest(),address,4096,'wrong'))
    memory[0]=0
    count=len(writes)
    reject(lambda:updater.program_zlib(str(path),hashlib.sha256(compressed).hexdigest(),0,4096,'wrong',require_blank=True))
    assert len(writes)==count and memory[0]==0
    memory[0]=255
    updater.program_zlib(str(path),hashlib.sha256(compressed).hexdigest(),0,4096,hashlib.sha256(new).hexdigest(),require_blank=True)
    count=len(writes)
    updater.program_zlib(str(path),hashlib.sha256(compressed).hexdigest(),0,4096,hashlib.sha256(new).hexdigest(),require_blank=True)
    assert len(writes)==count
    assert any(event[0]=='error' for event in events)
    assert all(address>>16 not in (0x08,0x11,0x1b,0x20,0x2e,0x5f,0x82,0xad,0xb1,0xff) for _,address in writes)
print('PASS: old-hash guard, unowned-tail guard, NOR erase/rewrite, readback, physical addressing and idempotent resume')
