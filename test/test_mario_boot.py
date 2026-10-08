"""Check BOOT debounce, deferred loading, failures and launcher replacement."""
import importlib.util
import sys
import types
from pathlib import Path

pending = []
loads = []
button = 0


class Timer:
    PERIODIC = 1

    def __init__(self, _id):
        self.active = False

    def init(self, **kwargs):
        self.active = True

    def deinit(self):
        self.active = False


sys.modules['machine'] = types.SimpleNamespace(Timer=Timer)
sys.modules['micropython'] = types.SimpleNamespace(schedule=lambda fn, arg: pending.append((fn, arg)))
sys.modules['rp2'] = types.SimpleNamespace(bootsel_button=lambda: button)
sys.modules['levels_board'] = types.SimpleNamespace(load=lambda digest: loads.append(digest) or 'board')
path = Path(__file__).resolve().parents[1] / 'scripts/mario_boot.py'
spec = importlib.util.spec_from_file_location('mario_boot', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
controller = module.install('board')


def sample(value):
    global button
    button = value
    controller.poll(None)


sample(1)
sample(0)
assert not pending, 'A bouncing edge must not launch'
sample(1)
sample(1)
assert len(pending) == 1 and not loads and not controller.timer.active
fn, arg = pending.pop()
fn(arg)
assert loads == [module.BITSTREAM_SHA256] and controller.timer.active
for _ in range(10):
    sample(1)
assert not pending, 'A held button must launch only once'
sample(0)
sample(0)
sample(1)
sample(1)
assert len(pending) == 1
controller.stop()
fn, arg = pending.pop()
fn(arg)
assert len(loads) == 1 and not controller.timer.active, 'Stopping cancels deferred loads'

controller = module.install('board')
def fail(_digest):
    raise RuntimeError('test load failure')
sys.modules['levels_board'].load = fail
controller.press()
fn, arg = pending.pop()
fn(arg)
assert not controller.busy and controller.timer.active
old = controller
controller = module.install('board')
assert not old.timer.active and controller.timer.active
print('PASS: debounce, one load per press, deferred execution, stop, failure recovery and replacement')
