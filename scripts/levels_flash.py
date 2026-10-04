"""MicroPython updater for owned Mario assets; unrelated relocated blocks stay intact."""
import gc,hashlib,binascii,deflate
import flash_progress as progress
ENEMY_BANKS=(0,1,3,5,7,9,10,12,13,14,15,24,25,26,27,28,29,30,31,57,58,59,60,61)
REGIONS=((0xc00000,0xe00100),(0x800000,0x940000),(0xa00000,0xc00000),(0x500000,0x600000))+tuple((bank<<18,(bank+1)<<18) for bank in ENEMY_BANKS)
READ_REGIONS=REGIONS+((0x400000,0x440100),(0x800000,0xc00000))
RELOCATIONS={0x82:0x45,0xad:0x46,0xb1:0x47,0x5f:0x48}
def physical(address):
    return (RELOCATIONS.get(address>>16,address>>16)<<16)|(address&65535)
def allowed(address,length,writing=False):
    return length>0 and any(lo<=address and address+length<=hi for lo,hi in (REGIONS if writing else READ_REGIONS))
def hash_file(path,asset=0):
    import os
    size=os.stat(path)[6];done=0
    progress.update(4,0,size,asset)
    d=hashlib.sha256()
    with open(path,'rb') as f:
        while True:
            data=f.read(8192)
            if not data:break
            d.update(data);done+=len(data)
            progress.update(4,done,size,asset)
    return binascii.hexlify(d.digest()).decode()
def scan(address,length):
    if not allowed(address,length):raise RuntimeError('Region not allowed')
    gc.collect();f=progress.open_flash();f.spi.init(baudrate=10000000)
    try:
        total=0;d=hashlib.sha256()
        progress.update(2,0,length,0x800000<=address<0xc00000)
        for off in range(0,length,16384):
            data=f.read(physical(address+off),min(16384,length-off))
            d.update(data);total+=sum(v!=255 for v in data)
            progress.update(2,off+len(data),length,0x800000<=address<0xc00000)
            if (off+16384)%1048576==0:print('SCAN_PROGRESS',hex(address),off+16384,length)
        print('SCAN',hex(address),length,'NON_FF',total,'SHA256',binascii.hexlify(d.digest()).decode())
        progress.update(2,length,length,0x800000<=address<0xc00000,complete=True)
        return total
    except Exception:
        progress.fail();raise
    finally:f.close();gc.collect()
def verify_region(address,length,expected):
    if not allowed(address,length):raise RuntimeError('Region not allowed')
    gc.collect();f=progress.open_flash();f.spi.init(baudrate=10000000)
    try:
        d=hashlib.sha256()
        progress.update(2,0,length,0x800000<=address<0xc00000)
        for off in range(0,length,16384):
            size=min(16384,length-off)
            d.update(f.read(physical(address+off),size))
            progress.update(2,off+size,length,0x800000<=address<0xc00000)
        if binascii.hexlify(d.digest()).decode()!=expected:
            raise RuntimeError('Existing flash hash mismatch')
        # The partial graphics sector may be erased only if its unowned tail is blank.
        end=address+length
        if end%4096 and any(v!=255 for v in f.read(physical(end),4096-end%4096)):
            raise RuntimeError('Unowned data in final sector; refusing erase')
        progress.update(2,length,length,0x800000<=address<0xc00000,complete=True)
        print('PREVIOUS_REGION_VERIFIED',hex(address),length,expected)
    except Exception:
        progress.fail();raise
    finally:f.close();gc.collect()

def program_zlib(path,compressed_hash,address,length,expected,require_blank=False):
    if not allowed(address,length,writing=True) or hash_file(path,0x800000<=address<0xc00000)!=compressed_hash:raise RuntimeError('Invalid asset')
    if address%4096:raise RuntimeError('Unaligned region')
    progress.update(4,1,1,0x800000<=address<0xc00000,complete=True)
    gc.collect();f=progress.open_flash();f.spi.init(baudrate=10000000)
    try:
        digest_out=hashlib.sha256();erased=0;changed=0
        progress.update(3,0,length,0x800000<=address<0xc00000)
        with open(path,'rb') as source:
            with deflate.DeflateIO(source,deflate.ZLIB) as stream:
                for off in range(0,length,4096):
                    size=min(4096,length-off);data=stream.read(size)
                    if len(data)!=size:raise RuntimeError('Truncated asset')
                    target=physical(address+off)
                    before=f.read(target,4096)
                    if size<4096 and any(v!=255 for v in before[size:]):
                        raise RuntimeError('Unowned final-sector data')
                    desired=data+b'\xff'*(4096-size)
                    if before!=desired:
                        # New banks may contain only erased bytes or bytes
                        # already matching this asset (safe interrupted resume).
                        if require_blank and any(old!=255 and old!=new for old,new in zip(before,desired)):
                            raise RuntimeError('Unowned nonblank data at '+hex(target))
                        changed+=1
                        if any((old & new)!=new for old,new in zip(before,desired)):
                            f.ready();f.cmd(b'\x06')
                            if not f.cmd(b'\x05',1)[0]&2:raise RuntimeError('Write enable failed')
                            f.cmd(bytes((0x20,target>>16,(target>>8)&255,target&255)));f.ready()
                            before=b'\xff'*4096;erased+=1
                        for pos in range(0,4096,256):
                            page=desired[pos:pos+256]
                            if page==before[pos:pos+256]:continue
                            a=target+pos;f.ready();f.cmd(b'\x06')
                            if not f.cmd(b'\x05',1)[0]&2:raise RuntimeError('Write enable failed')
                            f.cmd(bytes((2,a>>16,(a>>8)&255,a&255)),data=page);f.ready()
                    actual=f.read(target,4096)
                    if actual!=desired:raise RuntimeError('Flash readback mismatch at '+hex(target))
                    digest_out.update(actual[:size])
                    progress.update(3,off+size,length,0x800000<=address<0xc00000)
                    if (off+size)%65536==0 or off+size==length:
                        print('PROGRAM_VERIFIED',hex(address),off+size,length,'ERASED',erased,'CHANGED',changed)
                    gc.collect()
                if stream.read(1):raise RuntimeError('Oversized asset')
        actual=binascii.hexlify(digest_out.digest()).decode()
        if actual!=expected:raise RuntimeError('Region hash mismatch')
        progress.update(3,length,length,0x800000<=address<0xc00000,complete=True)
        print('REGION_VERIFIED',hex(address),length,actual)
    except Exception:
        progress.fail();raise
    finally:f.close();gc.collect()
