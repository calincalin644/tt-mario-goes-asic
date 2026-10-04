"""MicroPython loader for scrolling Mario with integrated progress. Import has no hardware side effects."""
import time

NAME = 'tt_um_mario_levels'
BITSTREAM = '/bitstreams/' + NAME + '.bin'


def sha256(path):
    import hashlib
    import binascii
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        while True:
            block = source.read(1024)
            if not block:
                break
            digest.update(block)
    return binascii.hexlify(digest.digest()).decode()


def load(expected_hash, start=True):
    import machine
    import sys
    from ttboard.boot.demoboard_detect import DemoboardDetect, DemoboardCarrier
    from ttboard.demoboard import DemoBoard
    from ttboard.fpga.fpga_mux import BitStream
    from ttboard.mode import RPMode

    DemoboardDetect.probe()
    if DemoboardDetect.CarrierVersion != DemoboardCarrier.FPGA:
        raise RuntimeError('FabricFox carrier not detected')
    actual = sha256(BITSTREAM)
    if actual != expected_hash:
        raise RuntimeError('Scrolling Mario bitstream SHA256 mismatch')
    tt = DemoBoard.get()
    if tt.shuttle.run != 'FPGA':
        raise RuntimeError('Board SDK is not configured for FPGA')
    previous = sys.modules.get('arcade_boot')
    controller = getattr(previous, '_controller', None) if previous else None
    if controller is not None:
        controller.stop()
    tt.clock_project_stop()
    tt.mode = RPMode.ASIC_MANUAL_INPUTS
    tt.uio_oe_pico.value = 0
    tt.reset_project(True)
    configured = tt.apply_configs
    try:
        # Avoid inherited per-project pin settings and a stale directory index.
        tt.apply_configs = False
        BitStream(tt.shuttle, BITSTREAM, NAME, clock_hz=25200000).enable()
        tt.mode = RPMode.ASIC_MANUAL_INPUTS
        tt.uio_oe_pico.value = 0
        tt.reset_project(True)
        pwm = tt.clock_project_PWM(25200000)
        if pwm.freq() != 25200000:
            machine.freq(126000000)
            pwm.freq(25200000)
        if pwm.freq() != 25200000:
            raise RuntimeError('Could not generate exact 25.2 MHz pixel clock')
        time.sleep_ms(10)
        if start:
            tt.reset_project(False)
        if int(tt.uio_oe_pico.value) != 0:
            raise RuntimeError('Management BIDIR drivers must be disabled')
        print('SHA256:', actual)
        print('Pixel clock:', pwm.freq(), 'Hz; BIDIR drivers:', tt.uio_oe_pico.value)
        print('VGA: OUTPUT; gamepad: INPUT connector 1; DIP 4/5/6 OFF.')
        print('Gamepad: left/right to move; A or B to jump or restart.')
        print('DIP 0/1/2: level minus one; DIP 3 ON loads/holds, OFF plays.')
        print('MARIO_LEVELS_LOADED' if start else 'MARIO_LEVELS_READY_IN_RESET')
        return tt
    except Exception:
        tt.clock_project_stop()
        tt.uio_oe_pico.value = 0
        tt.reset_project(True)
        raise
    finally:
        tt.apply_configs = configured
