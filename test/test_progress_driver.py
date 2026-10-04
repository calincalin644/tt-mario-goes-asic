"""Check the integrated status protocol, byte counts, transfer cleanup and bus release."""
import importlib.util,sys,tempfile,types,base64
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
levels={n:0 for n in range(25,33)};modes={};nibbles=[];packets=[];calls=[]
class Pin:
    IN=0;OUT=1
    def __init__(self,n,mode=None,value=None):
        self.n=n
        if mode is not None:self.init(mode,value=value)
    def init(self,mode,value=None):
        modes[self.n]=mode
        if value is not None:self(value)
    def __call__(self,value=None):
        if value is None:return levels.get(self.n,0)
        before=levels.get(self.n,0);levels[self.n]=value
        if self.n==25 and not value:assert levels[28]==0;nibbles.clear()
        if self.n==28 and value and not before:
            assert levels[25]==levels[31]==levels[32]==1
            nibbles.append(levels[26]|(levels[27]<<1)|(levels[29]<<2)|(levels[30]<<3))
            if len(nibbles)==2:packets.append((nibbles[0]<<4)|nibbles[1])
class SPI:
    def __init__(self,**kw):pass
    def deinit(self):pass
sys.modules['machine']=types.SimpleNamespace(Pin=Pin,SoftSPI=SPI)
def reset(value):
    if not value:assert all(modes[n]==Pin.IN for n in range(25,33))
    calls.append(('reset',value))
tt=types.SimpleNamespace(shuttle=types.SimpleNamespace(run='FPGA'),uio_oe_pico=types.SimpleNamespace(value=0),reset_project=reset,clock_project_stop=lambda:calls.append(('stop',)))
sys.modules['ttboard.demoboard']=types.SimpleNamespace(DemoBoard=types.SimpleNamespace(get=lambda:tt))
spec=importlib.util.spec_from_file_location('driver',ROOT/'scripts/flash_progress.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
driver.time=types.SimpleNamespace(sleep_us=lambda us:None,sleep_ms=lambda ms:None)
driver._pins=[Pin(n) for n in range(25,33)];driver.active=True

driver.update(2,50,100,1);assert packets[-1]==0x50
assert modes[27]==Pin.IN and levels[29]==levels[30]==1
count=len(packets);driver.update(2,50,100,1);assert len(packets)==count
driver.update(3,100,100,0);assert packets[-1]==0x9f # never show full until validated
driver.update(3,100,100,0,complete=True);assert packets[-1]==0xa0
driver.update(3,37,100,1);driver.fail();assert packets[-1]==0xcb
with tempfile.TemporaryDirectory() as tmp:
    target=Path(tmp)/'transfer.zlib'
    def mapped_open(path,mode):
        assert path=='/mario-stream-asset.zlib';return target.open(mode)
    driver.open=mapped_open
    driver.begin_receive(10,1);assert packets[-1]==0
    handle=driver._receive
    driver.receive(base64.b64encode(b'12345'));assert packets[-1]==16
    driver.receive(base64.b64encode(b'67890'));assert packets[-1]==31
    driver.end_receive();assert packets[-1]==32 and handle.closed
    assert target.read_bytes()==b'1234567890'
    driver.begin_receive(10,0);handle=driver._receive
    driver.receive(base64.b64encode(b'123'))
    try:driver.end_receive()
    except RuntimeError:pass
    else:raise AssertionError('truncation accepted')
    assert handle.closed and packets[-1]==0xc9
    driver.begin_receive(2,0);handle=driver._receive
    try:driver.receive(base64.b64encode(b'123'))
    except RuntimeError:pass
    else:raise AssertionError('oversized input accepted')
    assert handle.closed and packets[-1]==0xc0
driver.finish();assert packets[-1]==32 and not driver.active
assert calls==[('reset',False)] # no clock stop or bitstream reload
print('PASS: idle-bus quad packets, deselected memories, byte progress, completion guard, errors, transfer cleanup and release-before-game-resume')

# Existing programmer behavior remains the default; maintenance must preserve VGA.
calls.clear()
spec=importlib.util.spec_from_file_location('flash_driver',ROOT/'scripts/flash_pmod.py')
flash=importlib.util.module_from_spec(spec);spec.loader.exec_module(flash)
flash.time=driver.time
flash.Flash.cmd=lambda self,header,*args,**kwargs:b'\xef\x70\x18' if header==b'\x9f' else b'\x02'
f=flash.Flash(keep_display=True);f.close();assert calls==[]
f=flash.Flash();f.close();assert calls==[('reset',True),('stop',)]
print('PASS: maintenance keeps clock/reset; ordinary programming retains previous reset behavior')
