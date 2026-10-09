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

Flash stores eight base images, 36 encounter-animation images, two player poses and
reachable-state action tables: 15,532,288 bytes in total. At each update, three
button bits select an eight-byte record containing the next state address,
position, picture bank and motion/status information. The compiler resolves
physics, collisions, checkpoints and enemies offline. PSRAM is not used.

The design requests one tile. The measured mapped SKY130 cell area is
10,637.70 µm² (230 flip-flops) locally for the MIDI flash melody build. The preceding
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

The approved MIDI-derived single voice loops every 661 VGA frames (11.017 s).
A 31.5 kHz line enable drives the pitch divider. Flash stores one pitch-reload
byte per frame at 0xC3C000–0xC3C294, inside existing picture padding. Repeated
bytes sustain notes; zero bytes reproduce rests. The original approved frame
sequence is preserved, without the fixed-step score's artificial articulation
or a decay envelope. One shared copy serves every level and camera position.

A new jump-button press produces the existing roughly 984 Hz beep for four
frames (66.7 ms), temporarily replacing the melody. The music timeline keeps
advancing, so playback returns at the current point. Holding jump repeats
jumps without repeating the beep. DIP level loading and disabled gameplay mute
and pause the music; reset restarts it and releases the BIDIR drivers.

The existing raster counter supplies the 787.5 kHz PWM carrier: 50% while
silent and 25%/75% for the tone. Use the Tiny Tapeout Audio PMOD on BIDIR,
with the QSPI PMOD in its passthrough; its downstream PSRAM B select must stay
isolated from PWM. The 661-frame melody is flash-backed; new notes need asset regeneration, while
the loop length remains a hardware constant. A different 661-frame score can
be installed by changing flash alone; a longer loop requires new RTL.

### Tortoise stomp feedback

A stomp makes the tortoise harmless immediately and bounces Mario upward.
An upside-down closed shell is shown for three gameplay updates (200 ms at
15 Hz), then disappears. Mushrooms retain immediate disappearance. Encounter
state resets on checkpoint-section changes and death/restart as before.

This adds no ASIC RTL or registers. The offline compiler reuses the dead
enemy's animation field as a three-update countdown. Two extra 256 KiB
pictures supply the shell pose: level 7 at 0x4C0000–0x4FFFFF (bank 19), and
level 8 at 0x940000–0x97FFFF (bank 37). Existing game tables retain their sizes.
The manifest now allocates 15,532,288 bytes; 1,244,928 bytes remain outside
assets, including reserved/shared areas that must not be overwritten blindly.

Regenerate with `make assets` and `make images`. Deploy the matching rule
assets and shell pictures together. The connected FPGA/flash have not been
updated by this asset change.


### Coin encounters without new ASIC logic

One rotating coin is present in levels 1–5 and 8; levels 6 and 7 retain all
four mushrooms and all four tortoises respectively. Coins use otherwise empty
checkpoint encounters. Coins in levels 1–4 are at cell 7, feet 25; level 5's
coin is above a late platform at cell 219, feet 22; level 8's is at cell 71,
feet 25. They do not overlap enemy patrols.

Coins alternate a face and an edge picture while Mario is within three cells,
using the existing 15 Hz encounter animation. Contact marks the encounter
completed immediately, selecting the clean background with no damage, bounce,
score, or collection beep. The coin stays absent within that encounter;
death/restart or leaving and re-entering its checkpoint section resets it,
just like the enemy mechanism. There is no separate collection register,
coin overlay, checkpoint tag, or rotation circuit in the ASIC.

The previous three-coin overlay experiment has been removed. Current RTL is
identical to the pre-coin MIDI-flash implementation: 10,772.8320 um^2 in local
mapping, 232 flip-flops. Hosted hardening remains unverified.

Ten new 256 KiB coin pictures serve levels 1–5. Level 8 uses its existing
animation pictures. Rule allocations are trimmed to 64 KiB page boundaries;
physical rule pointers are rebuilt to fit pages around the pictures. Startup
0x800000 and the selector at 0x83FFC0 remain fixed. All reserved blocks and
the legacy graphics region 0x400000–0x4400FF remain untouched in the image.

The complete asset allocation is 15,532,288 bytes, leaving 1,244,928 bytes
outside assets, including reserved/shared regions. The manifest has 98 assets
and explicitly physical addresses, including 61 rule-page files. The physical
allocation is listed in `docs/flash-assets.csv`. The updated uploader uses
those physical regions without applying a second relocation. Do not mix this
manifest with the old uploader or old rule tables. Full asset-image and updater
changes are required together; the board has not been programmed by this work.

### Eight-step maintenance bar

The progress rectangle spans VGA x=256..511 and y=224..255. Eight 32-pixel
steps use h[7:5] directly, with h[9:8]==01 selecting the rectangle. The fill
comparison uses only progress bits 4:2; bit 5 forces full green on completion.
Progress below 4/32 remains empty, and 31/32 displays seven of eight steps.
Errors still turn the whole rectangle red. Packet format and host reporting
are unchanged; two unused low progress bits disappear during synthesis.

Current local mapping is 10,637.7024 um^2 with 230 flip-flops. This saves
120.1152 um^2 versus the aligned 32-step version, or 135.1296 um^2 versus
the original bar. Physical hardening has not been rerun for this change.
