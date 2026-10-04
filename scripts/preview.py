"""Animate the tested button route using the exact compiled flash pixels."""
import json,sys
from PIL import Image,ImageDraw
from world import ROOT,decode_word,camera,spawn,render_word,LEVELS,ENEMY_BANKS

RAW=(ROOT/"build/graphics.bin").read_bytes()
ENEMY_WORLDS={(level,bank):Image.open(ROOT/f'build/world-{level}-enemy-{phase}.png').convert('RGB') for level,banks in ENEMY_BANKS.items() for phase,bank in enumerate(banks)}
WORLDS=[Image.open(ROOT/f"build/world-{level}.png").convert("RGB") for level in range(8)]

def frame(state,facing=True,render_x=None,render_y=None):
    level,node,x,feet,phase=decode_word(state)
    render_x=x*8 if render_x is None else render_x
    render_y=feet*8 if render_y is None else render_y
    offset=max(0,render_x-96)
    world=ENEMY_WORLDS.get((level,(state>>4)&63),WORLDS[level])
    im=world.crop((offset,0,offset+320,240))
    raw=RAW
    colors=(None,(255,0,0),(255,170,85),(0,0,255))
    for y in range(16):
        pos=0x200000+(x%2)*64+y*4;row=int.from_bytes(raw[pos:pos+4],'big')
        for sx in range(16):
            ink=(row>>((sx if facing else 15-sx)*2))&3
            yy=render_y-16+y;xx=min(render_x,96)+sx
            if ink and 0<=yy<240:im.putpixel((xx,yy),colors[ink])
    if phase in (1,2):ImageDraw.Draw(im).rectangle((0,0,319,239),outline=(0,255,0) if phase==2 else (255,0,0),width=2)
    return im

def main():
    frames=[frame(render_word(0,0,spawn(0)))];facing=True
    for buttons,action,state in json.loads((ROOT/'build/route.json').read_text()):
        if action&3 in (1,2):facing=bool(action&2)
        frames.append(frame(state,facing))
    durations=[67]*len(frames);durations[0]=750;durations[-1]=1500
    frames[0].save(ROOT/'build/playthrough.gif',save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True)
    sheet=Image.new('RGB',(1024,8*144),(16,16,24))
    for level,world in enumerate(LEVELS):
        ImageDraw.Draw(sheet).text((4,level*144+3),f'{level+1}. {world["name"]}: {world["lesson"]}',fill='white')
        sheet.paste(Image.open(ROOT/f'build/world-{level}.png').resize((1024,120)),(0,level*144+20))
    sheet.save(ROOT/'build/levels.png')
    print('Saved preview of',len(frames)-1,'tested gameplay updates')
def smooth_video():
    import subprocess
    target=ROOT/'build/motion-comparison.mp4'
    with (ROOT/'build/preview-video.log').open('w') as log:
        encoder=subprocess.Popen(['ffmpeg','-y','-f','rawvideo','-pix_fmt','rgb24',
            '-s','640x264','-r','60','-i','-','-an','-c:v','libx264','-preset','fast',
            '-crf','18','-pix_fmt','yuv420p',str(target)],stdin=subprocess.PIPE,stderr=log)
        previous=render_word(0,0,spawn(0));facing=True
        for buttons,action,state in json.loads((ROOT/'build/route.json').read_text())[:120]:
            if action&3 in (1,2):facing=bool(action&2)
            level,node,x,y,status=decode_word(state)
            old_level,_,old_x,old_y,_=decode_word(previous)
            snap=level!=old_level or abs(x-old_x)>1 or abs(y-old_y)>2
            before=frame(state,facing)
            for phase in range(1,5):
                rx=x*8 if snap else old_x*8+(x-old_x)*2*phase
                ry=y*8 if snap else old_y*8+(y-old_y)*2*phase
                image=Image.new('RGB',(640,264),(12,12,20))
                text=ImageDraw.Draw(image)
                text.text((8,6),'BEFORE: 15 motion updates/sec',fill='white')
                text.text((328,6),'AFTER: 60 motion updates/sec',fill='white')
                image.paste(before,(0,24));image.paste(frame(state,facing,rx,ry),(320,24))
                encoder.stdin.write(image.tobytes())
            previous=state
        encoder.stdin.close()
        if encoder.wait():raise RuntimeError('Video encoding failed')
    print('Saved 60 fps motion comparison:',target)

if __name__=='__main__':
    smooth_video() if '--smooth-video' in sys.argv else main()
