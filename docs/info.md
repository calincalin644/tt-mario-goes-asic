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
11,093.14 µm² (232 flip-flops) locally for the fixed-step melody build. The preceding
melody failed CI placement at 13,701.89 µm²; the revised RTL needs new CI validation.

Mountains and background masonry fit within dry-land spans rather than crossing
water gaps. Trees and the finish gate also have dry foundations. These decorations
are baked into the base and enemy-animation pictures; collision geometry,
platforms and water-gap positions are independent of the decorative outlines.

## How to test

Program the external flash with the matching assets before starting the game;
blank flash cannot run it. See `docs/flash.md` in the source repository.
Select this project, supply a 25.2 MHz clock, assert reset low and release it high.
The host must release all BIDIR drivers before releasing reset.

Connect VGA to OUTPUT, the compatible serial gamepad PMOD to INPUT connector 1,
and stack BIDIR → Audio PMOD → flash/PSRAM PMOD. Keep DIP 4, 5 and 6 OFF
so they do not interfere with gamepad signals. D-pad left/right moves; A or B
jumps. Holding jump jumps again after landing and restarts at the checkpoint
after death. It does not permit mid-air jumps. Reaching a flag advances to the
next level; jumping after the final victory restarts.

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
| 110 | 7: Tortoise Trail | Four moving tortoises |
| 111 | 8: Water and Wildlife | Water, raised platforms and enemies |

Jump onto enemies to defeat them and bounce. Side contact kills the player.
Enemies reset on death or when re-entering their checkpoint section. Tortoises
are defeated with one stomp and have no shell mechanic. Shields are not present.

The ASIC also displays a 32-step progress bar while reset is held low and a host
owns the flash bus. A low-high reset transition first initializes the raster.
The host must supply progress packets; flash reads/writes do not update the bar
automatically. The reference updater restarts the bar for each asset and stage;
it does not display overall update progress. Cyan means progress, green completion
and red an error. During
maintenance all ASIC BIDIR outputs are high impedance. Ordinary flash SPI traffic
cannot change the bar. See `docs/flash.md` for the packet format.

## External hardware

- VGA PMOD and monitor supporting 640 × 480 at 60 Hz.
- Psychogenic-compatible serial gamepad PMOD: latch on UI4, clock on UI5, data on
  UI6; controller 1 occupies the last 12 serial bits, active high.
- Flash/PSRAM PMOD with a 16 MiB W25Q128-compatible NOR flash. Quad Enable must be
  configured externally. The ASIC reads with opcode `0xEB`, 24-bit quad address,
  `0xFF` mode byte and four dummy clocks; it does not initialize or program flash.
- Tiny Tapeout Audio PMOD on BIDIR, with the flash PMOD in its passthrough.
- Stable 25.2 MHz clock and normal Tiny Tapeout reset/enable support.

BIDIR wiring: UIO0 = flash CS#, UIO1 = IO0, UIO2 = IO1, UIO3 = SCK,
UIO4 = IO2, UIO5 = IO3, UIO6 = PSRAM A CS# (held high), UIO7 = jump audio PWM.
The Audio PMOD intercepts UIO7 and pulls its downstream pin 7 high, keeping
PSRAM B deselected. Without it, isolate flash-PMOD pin 7 and pull it high; do
not connect the PWM directly to the PSRAM select.
The six-bit VGA output uses UO0/1/2 = R1/G1/B1, UO4/5/6 = R0/G0/B0,
UO3 = VSYNC and UO7 = HSYNC. Sync pulses are active low.

## Jump audio

A single-voice melody loops every 600 VGA frames (10 seconds), using
the user-supplied 80-step score. A 31.5 kHz line enable drives
the pitch divider; 60 Hz frame ticks drive the sequence. No external flash is
used for sound. Steps alternate seven/eight frames for 120 BPM; the final
frame of each step is silent to separate repeated notes. No decay envelope is used.

A new jump-button press produces the existing roughly 984 Hz beep for four
frames (66.7 ms), temporarily replacing the melody. The music timeline keeps
advancing, so playback returns at the current point. Holding jump repeats
jumps without repeating the beep. DIP level loading and disabled gameplay mute
and pause the music; reset restarts it and releases the BIDIR drivers.

The existing raster counter supplies the 787.5 kHz PWM carrier: 50% while
silent and 25%/75% for the tone. Use the Tiny Tapeout Audio PMOD on BIDIR,
with the QSPI PMOD in its passthrough; its downstream PSRAM B select must stay
isolated from PWM. Music is hardwired and requires a new bitstream/ASIC RTL;
it cannot be added by changing flash alone.
