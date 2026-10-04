"""Export a physical 16 MiB image for a dedicated W25Q128 flash.

Manifest addresses are logical; gameplay pointers already contain the matching
physical relocation. Unallocated bytes in this image are erased (0xff).
"""
import hashlib
import json
from world import ROOT, RELOCATIONS


def pack():
    image = bytearray(b'\xff' * (16 * 1024 * 1024))
    occupied = bytearray(len(image))
    manifest = json.loads((ROOT / 'build/assets.json').read_text())
    for asset in manifest:
        data = (ROOT / 'build' / asset['file']).read_bytes()
        if len(data) != asset['size'] or hashlib.sha256(data).hexdigest() != asset['sha256']:
            raise ValueError(f"Asset mismatch: {asset['file']}")
        for offset in range(0, len(data), 65536):
            logical = asset['address'] + offset
            physical = (RELOCATIONS.get(logical >> 16, logical >> 16) << 16) | (logical & 65535)
            chunk = data[offset:offset + 65536]
            end = physical + len(chunk)
            if logical % 65536 or end > len(image) or any(occupied[physical:end]):
                raise ValueError(f"Unaligned, overlapping or out-of-range asset: {asset['file']}")
            image[physical:end] = chunk
            occupied[physical:end] = b'\x01' * len(chunk)
    path = ROOT / 'build/flash-16MiB.bin'
    path.write_bytes(image)
    digest = hashlib.sha256(image).hexdigest()
    (ROOT / 'build/flash-16MiB.sha256').write_text(f'{digest}  {path.name}\n')
    print(f'{path.name}: {len(image)} bytes, SHA256 {digest}')


if __name__ == '__main__':
    pack()
