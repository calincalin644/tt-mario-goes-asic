"""Plain ASIC progress bar: cyan activity, green completion, red error; idle-bus quad status."""
import time
active=False
_last=None
_pins=None
_receive=None
_received=0
_receive_size=0
_receive_asset=0

def start(expected):
    global active,_pins,_last
    import machine
    from levels_board import load
    active=False;_last=None
    # One game image contains both gameplay and the small maintenance bar.
    tt=load(expected,start=False)
    # Initialize the edge-reset raster, then enter sustained-reset maintenance.
    tt.reset_project(False);time.sleep_ms(1);tt.reset_project(True)
    _pins=[machine.Pin(n) for n in range(25,33)]
    active=True
    update(0,0,1,0)
    print('INTEGRATED_PROGRESS_READY')

def _write_status(word):
    import machine
    cs,io0,io1,sck,io2,io3,ram0,ram1=_pins
    # Flash/PSRAM stay deselected during data clocks. An empty CS pulse frames
    # each packet; it contains no command clocks and cannot program memory.
    cs.init(machine.Pin.OUT,value=1)
    ram0.init(machine.Pin.OUT,value=1);ram1.init(machine.Pin.OUT,value=1)
    sck.init(machine.Pin.OUT,value=0)
    io0.init(machine.Pin.OUT,value=1)
    io1.init(machine.Pin.IN)
    io2.init(machine.Pin.OUT,value=1);io3.init(machine.Pin.OUT,value=1)
    cs(0);time.sleep_us(5);cs(1);time.sleep_us(5)
    io1.init(machine.Pin.OUT,value=1)
    try:
        for shift in (4,0):
            nibble=(word>>shift)&15
            io0(nibble&1);io1((nibble>>1)&1);io2((nibble>>2)&1);io3((nibble>>3)&1)
            time.sleep_us(5);sck(1);time.sleep_us(5);sck(0);time.sleep_us(5)
    finally:
        io1.init(machine.Pin.IN);io0(1);io2(1);io3(1)

def update(stage,done,total,asset=0,complete=False):
    global _last
    if not active:return
    percent=min(100 if complete else 99,max(0,done*100//max(total,1)))
    state=(stage,percent,int(bool(asset)))
    if state==_last:return
    colour=3 if stage==6 else 2 if stage==3 else 1 if stage==2 else 0
    steps=32 if percent==100 else percent*32//100
    _write_status((colour<<6)|steps)
    if _last is None or state[0]!=_last[0] or state[2]!=_last[2] or percent//10!=_last[1]//10:
        print('VGA_PROGRESS',stage,'ASSET',state[2],'PERCENT',percent)
    _last=state

def fail():
    try:abort_receive()
    finally:
        if active:
            previous=_last or (0,0,0)
            update(6,previous[1],100,previous[2],complete=True)

def finish():
    global active
    if active:
        update(5,1,1,(_last or (0,0,0))[2],complete=True)
        time.sleep_ms(700)
        import machine
        from ttboard.demoboard import DemoBoard
        tt=DemoBoard.get()
        # Release every RP BIDIR driver before the ASIC takes back the bus.
        for pin in _pins:pin.init(machine.Pin.IN)
        tt.uio_oe_pico.value=0
        tt.reset_project(False)
        active=False
        print('MARIO_LEVELS_RESUMED_WITHOUT_RELOAD')

def open_flash():
    from flash_pmod import Flash
    return Flash(keep_display=active)

def begin_receive(size,asset):
    global _receive,_received,_receive_size,_receive_asset
    abort_receive()
    _received=0;_receive_size=size;_receive_asset=asset
    update(1,0,size,asset)
    # Reuse the compact uploader's scratch file rather than consuming more space.
    _receive=open('/mario-stream-asset.zlib','wb')

def receive(encoded):
    global _received
    import binascii
    try:
        data=binascii.a2b_base64(encoded)
        if _receive is None or _received+len(data)>_receive_size:raise RuntimeError('Invalid transfer size')
        if _receive.write(data)!=len(data):raise OSError('Short transfer write')
        _received+=len(data)
        update(1,_received,_receive_size,_receive_asset)
    except Exception:
        fail();raise

def end_receive():
    try:
        if _received!=_receive_size:raise RuntimeError('Truncated transfer')
        abort_receive()
        update(1,_received,_receive_size,_receive_asset,complete=True)
    except Exception:
        fail();raise

def abort_receive():
    global _receive
    if _receive is not None:
        current=_receive;_receive=None
        current.close()
