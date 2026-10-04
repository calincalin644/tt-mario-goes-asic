"""Compare every VGA pixel with an independent crop of the full flash artwork."""
from pathlib import Path
import sys
from PIL import Image,ImageChops
ROOT=Path(__file__).resolve().parents[1]
x=int(sys.argv[1]) if len(sys.argv)>1 else 3
level=int(sys.argv[2]) if len(sys.argv)>2 else 0
fraction_x=int(sys.argv[3]) if len(sys.argv)>3 else 0
fraction_y=int(sys.argv[4]) if len(sys.argv)>4 else 0
enemy_phase=int(sys.argv[5]) if len(sys.argv)>5 else -1
render_x=x*8+fraction_x*2
render_feet=208+fraction_y*2
camera=max(0,render_x-96)
source=f'world-{level}-enemy-{enemy_phase}.png' if enemy_phase>=0 else f'world-{level}.png'
expected=Image.open(ROOT/'build'/source).convert('RGB').crop((camera,0,camera+320,240)).resize((640,480),Image.Resampling.NEAREST)
actual=Image.open(ROOT/f'build/frame-{x}.ppm').convert('RGB')
data=(ROOT/'build/graphics.bin').read_bytes()
colours=[None,(255,0,0),(255,170,85),(0,0,255)]
for y in range(16):
    offset=0x200000+(x%2)*64+y*4
    row=int.from_bytes(data[offset:offset+4],'big')
    for sx in range(16):
        ink=(row>>(sx*2))&3
        if ink:
            for dy in range(2):
                for dx in range(2):expected.putpixel((min(render_x,96)*2+sx*2+dx,(render_feet-16)*2+y*2+dy),colours[ink])
difference=ImageChops.difference(actual,expected)
assert difference.getbbox() is None,('pixel mismatch',x,difference.getbbox())
suffix=f'-fraction-{fraction_x}-{fraction_y}' if fraction_x or fraction_y else ''
if enemy_phase>=0:suffix+=f'-enemy-{enemy_phase}'
actual.save(ROOT/f'build/view-{level}-{x}{suffix}.png')
print('PASS: all 307200 pixels match world crop and sprite at world x',x)
