"""Export the current packed flash artwork as ordinary PNG files."""
import hashlib
import json
import re

from PIL import Image, ImageDraw, ImageOps

from build_assets import PALETTE, rgb, enemy_sprite
from world import LEVELS, ROOT


def main():
    source = ROOT / 'build/graphics.bin'
    raw = source.read_bytes()
    assets=json.loads((ROOT/'build/assets.json').read_text())
    for asset in assets:
        data=(ROOT/'build'/asset['file']).read_bytes()
        assert len(data)==asset['size'] and hashlib.sha256(data).hexdigest()==asset['sha256']
    expected = next(a for a in assets
                    if a['file'] == 'graphics.bin')
    assert len(raw) == expected['size']
    assert hashlib.sha256(raw).hexdigest() == expected['sha256']

    output = ROOT / 'images'
    for directory in ('sprites', 'levels', 'theme-preview'):
        (output / directory).mkdir(parents=True, exist_ok=True)

    overview = Image.new('RGB', (1024, 8 * 144), (16, 16, 24))
    for level, description in enumerate(LEVELS):
        has_enemies=bool(description.get('enemies'))
        packed = ((ROOT/f'build/enemy-{level}-0.bin').read_bytes()[:240*1024] if has_enemies
                  else raw[level * 0x40000:level * 0x40000 + 240 * 1024])
        pixels = bytearray(2048 * 240)
        pixels[0::2] = bytes(value >> 4 for value in packed)
        pixels[1::2] = bytes(value & 15 for value in packed)
        picture = Image.frombytes('P', (2048, 240), bytes(pixels))
        picture.putpalette([channel for colour in PALETTE for channel in rgb(colour)]
                           + [0] * (768 - 48))
        picture = picture.convert('RGB')
        name = re.sub(r'[^a-z0-9]+', '-', description['name'].lower()).strip('-')
        path = output / 'levels' / f'{level + 1:02d}-{name}.png'
        picture.save(path)
        picture.save(output/'theme-preview'/f'world-{level}.png')
        assert Image.open(path).convert('RGB').tobytes() == picture.tobytes()
        reference = ROOT / (f'build/world-{level}-enemy-0.png' if has_enemies else f'build/world-{level}.png')
        if reference.exists():
            assert Image.open(reference).convert('RGB').tobytes() == picture.tobytes()
        ImageDraw.Draw(overview).text((4, level * 144 + 3),
                                     f'{level + 1}. {description["name"]}', fill='white')
        overview.paste(picture.resize((1024, 120), Image.Resampling.NEAREST),
                       (0, level * 144 + 20))
    overview.save(output / 'levels-overview.png')
    overview.save(ROOT / 'build/levels.png')
    themes=Image.new('RGB',(1024,536),(16,16,24))
    draw=ImageDraw.Draw(themes)
    for index,label in enumerate(('Green meadow / brown bricks','Darker blue sky / stone bridges',
                                   'Moonlit blue forest','Gray stone castle')):
        x=(index%2)*512;y=(index//2)*268
        draw.text((x+8,y+7),label,fill='white')
        themes.paste(picture.crop((index*512,0,(index+1)*512,240)),(x,y+28))
    themes.save(output/'theme-preview/four-themes.png')
    (output/'theme-preview/INFO.txt').write_text('Current compiled artwork with the first enemy animation phase.\nOne-hit shields remain pending.\n')

    colours = ((0, 0, 0, 0), (255, 0, 0, 255),
               (255, 170, 85, 255), (0, 0, 255, 255))
    sheet = Image.new('RGBA', (32, 16))
    for pose in range(2):
        sprite = Image.new('RGBA', (16, 16))
        for y in range(16):
            offset = 0x200000 + (pose * 16 + y) * 4
            row = int.from_bytes(raw[offset:offset + 4], 'big')
            for x in range(16):
                sprite.putpixel((x, y), colours[(row >> (x * 2)) & 3])
        sheet.paste(sprite, (pose * 16, 0))
        for direction, picture in (('right', sprite), ('left', ImageOps.mirror(sprite))):
            path = output / 'sprites' / f'mario-pose-{pose + 1}-{direction}.png'
            picture.save(path)
            assert Image.open(path).convert('RGBA').tobytes() == picture.tobytes()
    sheet.save(output / 'sprites/mario-spritesheet.png')
    sheet.resize((256, 128), Image.Resampling.NEAREST).save(
        output / 'sprites/mario-spritesheet-8x.png')

    for kind in ('mushroom','tortoise'):
        sheet=Image.new('RGBA',(64,16))
        for index,phase in enumerate((0,1,4,5)):
            sprite=enemy_sprite(kind,phase)
            rgba=sprite.convert('RGBA')
            rgba.putalpha(Image.frombytes('L',(16,16),bytes(0 if p==255 else 255 for p in sprite.tobytes())))
            direction='left' if phase>=4 else 'right'
            rgba.save(output/'sprites'/f'{kind}-pose-{phase%2+1}-{direction}.png')
            sheet.paste(rgba,(index*16,0))
        sheet.save(output/'sprites'/f'{kind}-spritesheet.png')
        sheet.resize((512,128),Image.Resampling.NEAREST).save(output/'sprites'/f'{kind}-spritesheet-8x.png')

    (output / 'INFO.txt').write_text(
        'Current eight-level Mario artwork, decoded from build/graphics.bin.\n'
        'Source SHA-256: ' + expected['sha256'] + '\n\n'
        'levels/: eight full-size 2048 x 240 RGB PNGs, without Mario.\n'
        'sprites/: two 16 x 16 RGBA poses, plus their mirrored left-facing versions.\n'
        'mario-spritesheet.png: both right-facing poses, side by side (32 x 16).\n'
        'mario-spritesheet-8x.png: enlarged preview, with nearest-neighbour scaling.\n'
        'levels-overview.png: reduced overview of all eight levels.\n\n'
        'The current spikes are part of the level pictures, not separate sprites.\n'
        'Enemy levels show the first active animation phase; enemies move and can\n'
        'be stomped in the game. Mushroom/tortoise sprite PNGs are also exported.\n'
        'One-hit shields are still pending.\n'
        'These are exports. Editing a PNG does not automatically update the game\n'
        'or its collision rules, which come from assets/levels.json and world.py.\n'
        'Regenerate with: make images\n'
    )
    print(f'Exported and checked 8 level images, Mario and enemy sprites, '
          f'and an overview in {output}')


if __name__ == '__main__':
    main()
