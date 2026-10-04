"""FabricFox MicroPython SPI transport; requires preconfigured Quad Enable.

Campaign programming and address guards are in levels_flash.py.
"""
from machine import Pin, SoftSPI
import time
import hashlib
import binascii

def digest(data):
    return binascii.hexlify(hashlib.sha256(data).digest()).decode()

class Flash:
    def __init__(self, keep_display=False):
        from ttboard.demoboard import DemoBoard
        import sys
        self.tt=DemoBoard.get()
        if self.tt.shuttle.run!='FPGA':
            raise RuntimeError('Expected FabricFox')
        helper=sys.modules.get('arcade_boot')
        controller=getattr(helper,'_controller',None) if helper else None
        if controller is not None: controller.stop()
        # Opt in only while the selected design keeps BIDIR high-impedance and VGA alive.
        if not keep_display:
            self.tt.reset_project(True)
            time.sleep_ms(2)
            self.tt.clock_project_stop()
        self.tt.uio_oe_pico.value=0
        self.cs=Pin(25,Pin.OUT,value=1)
        for n in (29,30,31,32): Pin(n,Pin.OUT,value=1)
        self.spi=SoftSPI(baudrate=1000000,polarity=0,phase=0,sck=Pin(28),mosi=Pin(26),miso=Pin(27))
        ident=self.cmd(b'\x9f',3)
        if ident not in (b'\xef\x70\x18',b'\xef\x40\x18'):
            self.close()
            raise RuntimeError('Unsupported flash JEDEC '+binascii.hexlify(ident).decode())
        if not self.cmd(b'\x35',1)[0]&2:
            self.close()
            raise RuntimeError('Quad Enable is not set')
        print('FLASH_JEDEC',binascii.hexlify(ident).decode())
    def cmd(self,header,length=0,data=None):
        self.cs(0)
        try:
            self.spi.write(header)
            if data is not None: self.spi.write(data)
            return self.spi.read(length) if length else b''
        finally: self.cs(1)
    def read(self,address,length):
        return self.cmd(bytes((3,address>>16,(address>>8)&255,address&255)),length)
    def ready(self):
        deadline=time.ticks_add(time.ticks_ms(),1000)
        while self.cmd(b'\x05',1)[0]&1:
            if time.ticks_diff(deadline,time.ticks_ms())<=0: raise RuntimeError('Flash busy timeout')
            time.sleep_ms(1)
    def close(self):
        self.cs(1)
        self.spi.deinit()
        for n in range(25,33): Pin(n,Pin.IN)
        self.tt.uio_oe_pico.value=0
