"""Verify the exported physical image reconstructs every logical asset."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
raw = (root / 'build/flash-16MiB.bin').read_bytes()
assert len(raw) == 16 * 1024 * 1024
mapping = {0x82: 0x45, 0xAD: 0x46, 0xB1: 0x47, 0x5F: 0x48}
manifest = json.loads((root / 'build/assets.json').read_text())
for asset in manifest:
    restored = bytearray()
    for offset in range(0, asset['size'], 65536):
        logical = asset['address'] + offset
        physical = mapping.get(logical >> 16, logical >> 16) * 65536
        restored.extend(raw[physical:physical + min(65536, asset['size'] - offset)])
    assert hashlib.sha256(restored).hexdigest() == asset['sha256'], asset['file']
for block in (0x08, 0x11, 0x1B, 0x20, 0x2E, 0x5F, 0x82, 0xAD, 0xB1, 0xFF):
    assert raw[block * 65536:(block + 1) * 65536] == b'\xff' * 65536
expected = (root / 'build/flash-16MiB.sha256').read_text().split()[0]
assert hashlib.sha256(raw).hexdigest() == expected
print(f'PASS: physical image reconstructs all {len(manifest)} assets; reserved blocks erased; checksum matches')
