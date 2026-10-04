## How it works

This design implements an eight-level scrolling platform game using a small ASIC
and external QSPI NOR flash. VGA is 640 × 480 at 60 Hz with a 25.2 MHz clock,
800 pixel clocks per line and 525 lines per frame. Artwork has 320 × 240 logical
pixels per screen, doubled horizontally and vertically. Each level spans 2,048
logical pixels, or 6.4 screens.

The ASIC generates VGA timing, decodes the serial gamepad, streams background and
player pixels, selects camera position, interpolates player movement, and reads
precomputed gameplay transitions from flash. There is no processor, instruction
execution, framebuffer, or on-chip level ROM. Game updates and enemy animation
run at 15 Hz; player and camera positions interpolate at 60 Hz.

Flash stores eight base images, 24 enemy-animation images, two player poses and
reachable-state action tables: 12,845,312 bytes in total. At each update, three
button bits select an eight-byte record containing the next state address,
position, picture bank and motion/status information. The compiler resolves
physics, collisions, checkpoints and enemies offline. PSRAM is not used.

The design requests one tile. The measured mapped SKY130 cell area is
9,634.24 µm²; physical fit and timing require the shuttle's GDS/precheck results.

## How to test

Program the external flash with the matching assets before starting the game;
blank flash cannot run it. See `docs/flash.md` in the source repository.
Select this project, supply a 25.2 MHz clock, assert reset low and release it high.
The host must release all BIDIR drivers before releasing reset.

Connect VGA to OUTPUT, the compatible serial gamepad PMOD to INPUT connector 1,
and the flash/PSRAM PMOD to BIDIR. Keep DIP 4, 5 and 6 OFF so they do not interfere
with gamepad signals. D-pad left/right moves; A or B jumps. Release jump between
jumps. After death, release and press jump to return to the checkpoint. Reaching
a flag advances to the next level; jumping after the final victory restarts.

DIP 0–2 select a level, with DIP 0 as the least significant bit. Turn DIP 3 ON,
wait for the selected level to appear, then turn DIP 3 OFF to play. Holding DIP 3
ON holds the character at that level's entry.

| DIP 2/1/0 | Level | Main challenge |
| --- | --- | --- |
| 000 | 1: First Steps | Low horizontal blocks |
| 001 | 2: Metal Meadow | Spikes |
| 010 | 3: Mind the Gaps | Holes |
| 011 | 4: Watch Your Landing | Spikes and holes |
| 100 | 5: High Water | Raised platforms across wide water |
| 101 | 6: Mushroom Meadow | Four moving mushrooms |
| 110 | 7: Lone Tortoise | One moving tortoise |
| 111 | 8: Water and Wildlife | Water, raised platforms and enemies |

Jump onto enemies to defeat them and bounce. Side contact kills the player.
Enemies reset on death or when re-entering their checkpoint section. Tortoises
are defeated with one stomp and have no shell mechanic. Shields are not present.

The ASIC also displays a 32-step progress bar while reset is held low and a host
owns the flash bus. A low-high reset transition first initializes the raster.
The host must supply progress packets; flash reads/writes do not update the bar
automatically. Cyan means progress, green completion and red an error. During
maintenance all ASIC BIDIR outputs are high impedance. Ordinary flash SPI traffic
cannot change the bar. See `docs/flash.md` for the packet format.

## External hardware

- VGA PMOD and monitor supporting 640 × 480 at 60 Hz.
- Psychogenic-compatible serial gamepad PMOD: latch on UI4, clock on UI5, data on
  UI6; controller 1 occupies the last 12 serial bits, active high.
- Flash/PSRAM PMOD with a 16 MiB W25Q128-compatible NOR flash. Quad Enable must be
  configured externally. The ASIC reads with opcode `0xEB`, 24-bit quad address,
  `0xFF` mode byte and four dummy clocks; it does not initialize or program flash.
- Stable 25.2 MHz clock and normal Tiny Tapeout reset/enable support.

BIDIR wiring: UIO0 = flash CS#, UIO1 = IO0, UIO2 = IO1, UIO3 = SCK,
UIO4 = IO2, UIO5 = IO3, UIO6/7 = PSRAM chip selects (held high during play).
The six-bit VGA output uses UO0/1/2 = R1/G1/B1, UO4/5/6 = R0/G0/B0,
UO3 = VSYNC and UO7 = HSYNC. Sync pulses are active low.
