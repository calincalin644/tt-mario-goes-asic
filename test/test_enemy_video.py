"""Compare every pixel of every enemy animation bank with the flash artwork."""
import os
import shlex
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from world import ENEMY_BANKS,ROOT

for level,banks in ENEMY_BANKS.items():
    x={5:27,6:155,7:30}[level]
    for phase,bank in enumerate(banks):
        subprocess.run(shlex.split(os.environ.get('IVERILOG','iverilog'))+[
            '-g2012','-s','video_test',f'-Pvideo_test.PLAYER_X={x}',
            f'-Pvideo_test.LEVEL={level}',f'-Pvideo_test.PICTURE={bank}',
            '-o','build/video-enemies','test/video.v','test/flash_model.v',
            'src/tt_um_mario_levels.v','src/controls.v'],check=True,cwd=ROOT)
        subprocess.run(['vvp','build/video-enemies',f'+FRAME=build/frame-{x}.ppm'],check=True,cwd=ROOT)
        subprocess.run([sys.executable,'test/check_frame.py',str(x),str(level),'0','0',str(phase)],check=True,cwd=ROOT)
        print(f'PASS: level {level+1}, enemy phase {phase}, physical picture bank {bank}',flush=True)
