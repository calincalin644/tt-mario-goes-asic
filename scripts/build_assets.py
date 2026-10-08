"""Compile room pictures and a complete movement lookup into external flash assets."""
import hashlib,json,zlib
from pathlib import Path
from PIL import Image,ImageDraw
from world import ROOT,LEVELS,ground,ENEMY_OFFSETS,ENEMY_BANKS,RULE_BASES
from compile_rules import build_rules
PALETTE=[0b011011,0b100100,0b001100,0b111111,0b111000,0b110100,0b000001,0b101010,
         0b100110,0b000010,0b010101,0b101011,0b010000,0b001000,0b111001,0b000011]
def rgb(c):return ((c>>4)*85,((c>>2)&3)*85,(c&3)*85)

def enemy_sprite(kind,phase=0):
    rows=json.loads((ROOT/'assets/enemies.json').read_text())[kind]
    assert len(rows)==16 and all(len(row)==16 for row in rows)
    im=Image.new('P',(16,16),255)
    im.putpalette([v for c in PALETTE for v in rgb(c)]+[0]*(768-48))
    for y,row in enumerate(rows):
        for x,char in enumerate(row):
            if char!='.':im.putpixel((x,y),int(char,16))
    if phase&1:
        # Alternate the two feet without moving the body or collision box.
        feet=im.crop((0,14,16,16));im.paste(255,(0,14,16,16));im.paste(feet,(1,14))
    if phase>=4:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return im

def draw_enemies(im,world,phase):
    for enemy in world.get('enemies',[]):
        sprite=enemy_sprite(enemy['kind'],phase)
        mask=Image.frombytes('L',sprite.size,bytes(0 if pixel==255 else 255 for pixel in sprite.tobytes()))
        im.paste(sprite,(enemy['x']*8+ENEMY_OFFSETS[phase],enemy['feet']*8-16),mask)

def pack_picture(im):
    pixels=im.tobytes()
    return bytes((hi<<4)|lo for hi,lo in zip(pixels[::2],pixels[1::2]))+b'\xff'*0x4000

def render_level(level,WORLD,graphics,output_dir=None):
    im=Image.new('P',(2048,240),0)
    im.putpalette([v for c in PALETTE for v in rgb(c)]+[0]*(768-48))
    d=ImageDraw.Draw(im)
    # One continuous, hand-designed landscape, with four distinct visual regions.
    for section,theme in enumerate(WORLD["themes"]):
        left=section*512
        # Reuse the ASIC's fixed palette: colour changes cost only flash bytes.
        # Meadow, deep-blue stone bridges, moonlit forest, gray stone castle.
        sky=(0,9,9,10)[theme]
        d.rectangle((left,0,left+511,239),fill=sky)
        if theme<2:
            for cx,cy in ((36,35),(215,20),(390,57)):
                x=left+cx
                d.rectangle((x,cy,x+39,cy+8),fill=3)
                d.rectangle((x+9,cy-6,x+28,cy+8),fill=3)
        elif theme==2:
            for n in range(32):
                x=left+(n*83)%512;y=10+(n*29)%116
                d.point((x,y),fill=3)
            d.ellipse((left+365,24,left+390,49),fill=14)
            d.ellipse((left+357,20,left+380,44),fill=9)
        # Anchor scenery to dry land. Each object fits wholly inside one
        # shoreline span, rather than letting a fixed repeat cross a water gap.
        spans=[]
        for col in range(section*64,(section+1)*64):
            if ground(level,col)<30:
                if spans and spans[-1][1]==col*8:
                    spans[-1]=(spans[-1][0],(col+1)*8)
                else:spans.append((col*8,(col+1)*8))
        for shore_left,shore_right in spans:
            if theme==0:
                for x in range(shore_left+4,shore_right-19,110):
                    width=min(84,shore_right-4-x)
                    peak=x+width*45//100
                    height=min(63,width*3//4)
                    d.polygon(((x,207),(peak,207-height),(x+width-1,207)),fill=13)
                    d.polygon(((x+width//4,207),(x+width*56//100,207-height*2//3),
                               (x+width*92//100,207)),fill=2)
                    if height>30:d.line((peak,215-height,peak,227-height),fill=2,width=2)
            elif theme==1:
                for x in range(shore_left,shore_right,64):
                    width=min(64,shore_right-x)
                    d.rectangle((x,139,x+width-1,150),fill=10)
                    pier=min(12,width)
                    d.rectangle((x,150,x+pier-1,207),fill=10)
                    d.rectangle((x+width-pier,150,x+width-1,207),fill=10)
                    if width>28:d.arc((x+11,150,x+width-12,186),180,360,fill=7,width=3)
                    for y in range(140,207,12):d.line((x,y,x+pier-2,y),fill=7)
            elif theme==2:
                for x in range(shore_left+4,shore_right-41,51):
                    d.rectangle((x+15,129,x+21,207),fill=10)
                    d.polygon(((x-4,168),(x+18,91),(x+42,168)),fill=13)
                    d.polygon(((x,143),(x+18,75),(x+37,143)),fill=6)
            else:
                d.rectangle((shore_left,115,shore_right-1,207),fill=6)
                for x in range(shore_left+4,shore_right-31,96):
                    width=min(36,shore_right-4-x)
                    d.rectangle((x,69,x+width-1,207),fill=7)
                    for bx in range(x,x+width-6,12):d.rectangle((bx,61,bx+6,72),fill=7)
                    for y in range(77,208,16):d.line((x,y,x+width-1,y),fill=10)
                    for y in (91,123,155):d.rectangle((x+width//2-4,y,x+width//2+4,y+12),fill=4)
                # The finish gate also needs a complete dry foundation.
                if shore_left<=1828 and shore_right>=1902:
                    d.rectangle((1828,112,1901,207),fill=10)
                    d.rectangle((1846,153,1883,207),fill=6)
                    d.arc((1846,139,1883,175),180,360,fill=7,width=3)
    # Physical terrain exactly follows the offline collision description.
    for col in range(256):
        theme=WORLD["themes"][col//64];top=ground(level,col)
        for row in range(top,30):
            x,y=col*8,row*8
            fill=(1,10,6,10)[theme];edge=(5,7,10,7)[theme]
            d.rectangle((x,y,x+7,y+7),fill=fill)
            d.line((x,y,x+7,y),fill=edge)
            d.line((x,y,x,y+7),fill=edge)
            if row==top:d.line((x,y,x+7,y),fill=(2,3,13,7)[theme])
        if top==30:
            # Blue water lies below the fall threshold in every theme.
            d.rectangle((col*8,235,col*8+7,239),fill=9)
            d.line((col*8,235,col*8+7,235),fill=0)
    for a,b,top in WORLD['platforms']:
        for col in range(a,b):
            x,y=col*8,top*8;theme=WORLD["themes"][col//64]
            d.rectangle((x,y,x+7,y+7),fill=(1,10,10,10)[theme])
            d.rectangle((x+1,y+1,x+6,y+6),outline=(5,3,7,7)[theme])
            d.point((x+3,y+3),fill=(5,7,7,7)[theme])
    for a,b in WORLD['spikes']:
        for col in range(a,b):
            x=col*8;d.polygon(((x,207),(x+3,200),(x+7,207)),fill=7)
            d.line((x+3,200,x+5,205),fill=3)
    # Small checkpoint signs, not repeated finish flags.
    for index,col in enumerate(WORLD['checkpoints'][1:],2):
        x=col*8
        d.rectangle((x+1,187,x+2,207),fill=1)
        d.rectangle((x-3,177,x+9,189),fill=14)
        d.text((x,178),str(index),fill=6)
    x=WORLD['finish']*8+12
    d.line((x,111,x,207),fill=3,width=2)
    d.polygon(((x-2,113),(x-27,113),(x-18,121),(x-27,128),(x-2,128)),fill=2)
    for checkpoint in WORLD["checkpoints"]:
        x=checkpoint*8
        d.rectangle((x,67,x+246,94),fill=6)
        d.text((x+4,70),f"LEVEL {level+1}: {WORLD['name'].upper()}",fill=3)
        d.text((x+4,82),WORLD["lesson"],fill=14)
    for y in range(240):
        row=bytes((im.getpixel((x,y))<<4)|im.getpixel((x+1,y)) for x in range(0,2048,2))
        graphics[(level<<18)+y*1024:(level<<18)+y*1024+1024]=row
    im.convert('RGB').save((output_dir or ROOT/'build')/f'world-{level}.png')
    return im

def build():
    graphics=bytearray(b'\xff'*0x200100)
    variants=[]
    for level,world in enumerate(LEVELS):
        background=render_level(level,world,graphics)
        if level in ENEMY_BANKS:
            for phase in range(8):
                picture=background.copy();draw_enemies(picture,world,phase)
                name=f'enemy-{level}-{phase}.bin'
                (ROOT/'build'/name).write_bytes(pack_picture(picture))
                variants.append((name,ENEMY_BANKS[level][phase]<<18))
                picture.convert('RGB').save(ROOT/f'build/world-{level}-enemy-{phase}.png')
    # Four-colour player: transparent, red, skin, blue. Animation remains external.
    sprites=json.loads((ROOT/'assets/sprites.json').read_text())
    remap=(0,1,3,2,3,2,3,2)
    for pose in range(2):
        for row,packed in enumerate(sprites['player_walk' if pose else 'player']):
            reduced=sum(remap[(packed>>(3*x))&7]<<(2*x) for x in range(16))
            at=0x200000+(pose*16+row)*4
            graphics[at:at+4]=reduced.to_bytes(4,'big')
    (ROOT/'build/graphics.bin').write_bytes(graphics)
    build_rules()
    manifest=[]
    for name,base in [('graphics.bin',0xc00000)]+variants+[(f'rules-{level}.bin',base) for level,base in enumerate(RULE_BASES)]:
        data=(ROOT/'build'/name).read_bytes()
        compressed=zlib.compress(data,9)
        (ROOT/'build'/(name+'.zlib')).write_bytes(compressed)
        manifest.append(dict(file=name,address=base,size=len(data),sha256=hashlib.sha256(data).hexdigest(),
                             compressed_sha256=hashlib.sha256(compressed).hexdigest()))
    (ROOT/'build/assets.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'build/flash-load.vh').write_text(''.join(
        f'  load_asset("build/{a["file"]}",24\'h{a["address"]:06x},{a["size"]});\n' for a in manifest))
    print('Compiled',sum(a['size'] for a in manifest),'bytes of pictures and gameplay tables')
if __name__=='__main__':build()
