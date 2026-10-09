"""Check generated melody against the auditioned frame sequence and divider model."""
import json, os, shlex, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_melody import generate,START,END
rtl=(ROOT/'src/tt_um_mario_levels.v').read_text()
assert rtl[rtl.index(START):rtl.index(END)+len(END)]==generate(),'Regenerate melody RTL'
asset=json.loads((ROOT/'assets/melody.json').read_text())
slots=asset['frame_divisors']
(ROOT/'build/melody-pitches.hex').write_text(''.join(f"{max(0,n-1):02x}\n" for n in slots))
(ROOT/'build/melody-expected.hex').write_text(''.join(f'{x:02x}\n' for x in slots))
subprocess.run(shlex.split(os.environ.get('IVERILOG','iverilog'))+['-g2012','-s','melody_test','-o','build/melody-test','test/melody.v','src/tt_um_mario_levels.v','src/controls.v'],cwd=ROOT,check=True)
subprocess.run(shlex.split(os.environ.get('VVP','vvp'))+['build/melody-test'],cwd=ROOT,check=True)
