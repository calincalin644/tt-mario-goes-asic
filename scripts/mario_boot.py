"""MicroPython BOOT-button launcher for the verified FabricFox Mario build.

Install from main.py with mario_boot.install(tt). No gamepad/DIP pins are driven.
The button callback queues loading outside the polling callback and stops polling
during configuration. A held button launches only once.
"""
import machine
import micropython
import rp2
import sys

BITSTREAM_SHA256 = 'e3ce456c824bb8fb5c41ba6256f89db6a23b690bd7439a1470682ebe8407b12c'
_controller = None


class BootMario:
    def __init__(self, board):
        self.board = board
        self.timer = machine.Timer(-1)
        self.read_button = rp2.bootsel_button
        self.previous = 0
        self.stable = 0
        self.busy = False
        self.running = True
        self.presses = 0
        self._launch_callback = self._launch
        self._start_timer()

    def _start_timer(self):
        self.timer.init(period=20, mode=machine.Timer.PERIODIC, callback=self.poll)

    def press(self):
        if self.busy or not self.running:
            return
        self.busy = True
        self.timer.deinit()
        try:
            micropython.schedule(self._launch_callback, 0)
        except Exception:
            self.busy = False
            if self.running:
                self._start_timer()
            raise

    def _launch(self, _arg):
        try:
            if self.running:
                from levels_board import load
                self.board = load(BITSTREAM_SHA256)
                self.presses += 1
                print('Mario BOOT: loaded at 25.2 MHz; press count', self.presses)
        except Exception as exc:
            print('Mario BOOT load failed:', exc)
        finally:
            self.busy = False
            if self.running:
                self._start_timer()

    def poll(self, _timer):
        if self.busy or not self.running:
            return
        sample = int(bool(self.read_button()))
        if sample == self.previous and sample != self.stable:
            self.stable = sample
            if sample:
                self.press()
        self.previous = sample

    def stop(self):
        self.running = False
        self.timer.deinit()


def install(board):
    global _controller
    # Also works when replacing the old launcher without rebooting.
    old_module = sys.modules.get('arcade_boot')
    old = getattr(old_module, '_controller', None) if old_module else None
    if old is not None:
        old.stop()
    if _controller is not None:
        _controller.stop()
    _controller = BootMario(board)
    print('Mario BOOT launcher installed: press BOOT to load/restart Mario.')
    return _controller
