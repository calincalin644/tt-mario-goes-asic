# Mario goes ASIC

An eight-level scrolling VGA platformer for one Tiny Tapeout tile, backed by a
16 MiB QSPI flash PMOD. Each world is 2,048 × 240 logical pixels (6.4 screen widths).
The ASIC streams VGA and reads precomputed gameplay transitions; it has no CPU
or framebuffer. Mario and camera movement interpolate at 60 Hz, with gameplay
and enemy animation at 15 Hz. PSRAM is unused.

![Eight level layouts](docs/levels-overview.png)

See [the datasheet](docs/info.md) for wiring, controls, level selection and operation,
and [flash preparation](docs/flash.md) for the required external memory contents.

## Build and test

Use Python 3.11+, GNU Make and Icarus Verilog with `vvp` on PATH:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r test/requirements.txt
make check flash-image smoke
```

`make check` builds assets, validates the gameplay tables, simulates a complete
campaign over QSPI, checks controllers/DIP selection and maintenance operation,
compares base, interpolated and enemy VGA frames pixel by pixel, and checks
audio PWM, held-jump repeat and the BOOT launcher.
`make smoke` runs the public-pin Cocotb test also used by gate-level CI.
`make flash-image` exports a physical flash image with address relocation applied.
Generated outputs go in ignored `build/`; they do not belong in synthesis inputs.

Edit `assets/levels.json` for geometry and enemies, `assets/sprites.json` and
`assets/enemies.json` for sprites, `scripts/build_assets.py` for background
scenery, and `scripts/world.py` for gameplay rules.
`make assets` regenerates the flash content; `make images` exports PNGs into
ignored `images/`. Changing rules or geometry may exceed the allocated state
banks; the compiler checks this. The flash data format must match this RTL.

## Shoreline artwork

Mountains, stone arches, trees and castle masonry are placed within contiguous
spans of dry land from the level geometry. Mountains shrink to fit short banks;
stonework ends at the shoreline, and the finish gate requires a dry foundation.
The water gaps and playable platforms are unchanged. Scenery is decorative and
has no collision effect.

The renderer applies this to all eight base pictures and all 24 enemy-animation
pictures. The latest artwork update replaced `graphics.bin` and the 24 enemy
files, with readback verification; all eight gameplay tables stayed byte-identical.
Flash allocation and ASIC area are unchanged. See the [flash artwork workflow](docs/flash.md#updating-background-artwork).

## ASIC submission

Only `src/tt_um_mario_levels.v` and `src/controls.v` are synthesis sources.
`info.yaml` requests `1x1`, at 25.2 MHz; the template clock constraint is 39.68 ns.
The cloned SKY130 shuttle's GDS, precheck, gate-level and documentation workflows
are retained. Push the prepared repository to run those workflows.

The MIDI flash melody maps locally to **11,561.09 µm²** and **244 flip-flops**,
788.26 µm² above the no-coin MIDI flash implementation. This is a pre-placement
estimate. The preceding melody failed CI placement at 13,701.89 µm²; the
revised RTL still requires hosted synthesis and hardening. Local mapping does
not establish compliance with the 11,200 µm² target in the shuttle flow.

## Optional FPGA build

`make fpga` uses Yosys, nextpnr-ice40 and IceStorm with the FabricFox wrapper and
pin constraints in `fpga/`. This wrapper is not an ASIC source. The previous MIDI melody build
uses 703/5,280 FPGA logic cells, one block RAM for the hardwired melody table,
and no DSP or PLL; the build routes at 36.86 MHz (25.2 MHz required). These are historical FPGA results; the fixed-step version has not been rebuilt for the board.

For a local mapped-area estimate, run `make area LIBERTY=/path/to/sky130.lib`.
No workstation-specific paths or tools are included.

## View the FPGA on the computer monitor

Connect VGA PMOD -> powered VGA-input/HDMI-output converter -> HDMI USB capture
adapter -> computer. A converter intended for HDMI input and VGA output does
not work in that direction. Connect the FPGA board's USB cable, then run:

```sh
./scripts/watch_fpga.sh
```

The script loads the verified eight-level Mario bitstream already installed on
the board, sets the pixel clock to 25.2 MHz and then opens the viewer. It needs
`mpremote` on PATH or in a nearby `.venv/bin` directory (or set `MPREMOTE` to
its executable path). The board must already contain `levels_board.py` and
`/bitstreams/tt_um_mario_levels.bin`; the expected bitstream checksum is pinned
in the script. No external-flash assets are rewritten. Set `FPGA_PORT` to a
serial device path or `id:SERIAL` when multiple MicroPython boards are attached.
Use `./scripts/watch_fpga.sh --view-only` to avoid restarting a running game.
This restores Mario when the viewer is launched after reconnecting; it does
not change the board's autonomous power-on configuration.

The development board also has a persistent BOOT-button launcher installed:
after power-up, **press BOOT to load Mario at 25.2 MHz**. Another press reloads
and restarts the game. The handler is `scripts/mario_boot.py`, installed on the
board as `/mario_boot.py`, with `import mario_boot; mario_boot.install(tt)` at
the end of `/main.py`. It replaces the previous arcade button handler and does
not drive gamepad or DIP inputs. BOOT is a runtime button here; holding it while
connecting power can instead enter the board's USB firmware bootloader.

The previous board startup file is preserved as `/main-before-mario-boot.py`.
Restoring that file to `/main.py` and rebooting restores the older launcher.
The factory-test default remains until BOOT is pressed; this is not automatic
Mario loading at power-on. The BOOT handler loads the installed bitstream without rewriting game assets.

The script finds the USB device named `USB Video: USB Video`, excluding its
metadata node and the laptop webcam. Alternatively specify `/dev/video2` or a
stable `/dev/v4l/by-id/...` device path. `--list` lists devices; `--formats`
lists the selected device's modes. It requires `ffplay` (the `ffmpeg` package);
device inspection uses `v4l2-ctl` (the `v4l-utils` package).

The default is MJPEG 640x480 at 60 fps in a 960x720 window with reduced software
buffering. Press **F** for fullscreen and **Q** or **Escape** to quit. Continue
using the gamepad attached to the FPGA; this script only displays captured video.
The capture hardware may add latency or repeat frames even when it advertises
60 fps. Close other capture applications if the device reports that it is busy.

If colour bars or a no-signal screen appear, check the running FPGA design,
converter direction/power and connections. A successfully opened USB device
alone does not establish that a valid VGA signal is reaching the converter.

## Repository contents and limitations

The flash assets occupy 13,369,600 bytes; the dedicated-chip image is 16 MiB
including erased space. Keep binaries, manifests/checksums and any bitstreams as
release artifacts rather than committing the generated `build/` directory.

`scripts/levels_flash.py`, `flash_progress.py`, `levels_board.py` and
`flash_pmod.py` are FabricFox MicroPython reference helpers, included with their
host-side tests. They are not a generic ASIC-board uploader. The previous
workstation-specific migration uploader and its backups are intentionally omitted.

Enemies can be stomped; tortoises have no shell mechanic. Enemy state is retained
only within the current checkpoint section. One-hit shields are not implemented.
The repository retains the template Apache-2.0 license. Mario and related names
and characters belong to their respective owners; this is an independent project.

## Melody and jump beep

The approved MIDI-derived opening ten bars loop in 661 VGA frames (11.017 s).
There is one flash byte per frame, preserving the approved pitches, note
lengths and rests. Repeated bytes sustain a note; zero bytes are silence.
`assets/melody.json` and `scripts/build_melody.py` regenerate RTL with
`make melody`; `make assets` packs the data into existing graphics padding.
The 661 pitch-reload bytes reside at 0xC3C000–0xC3C294. No decay envelope is used.

Render two loops with:
`python3 scripts/render_melody.py build/mario-approved-midi.wav` (requires NumPy).
The WAV models divider pitch and frame timing, excluding the ultrasonic PWM
carrier, startup delay, and the PMOD/speaker analog response.

A fresh jump press overrides the melody with the existing 66.7 ms beep. The
melody keeps advancing underneath and resumes at its current position. Held
jump repeats jumps without repeated beeps. Reset restarts the tune; disabled
gameplay and DIP level loading mute and pause it. No bass or accompaniment
is implemented. Connect BIDIR → Audio PMOD → QSPI PMOD; the Audio PMOD
isolates UIO7 from downstream PSRAM B select. See [audio wiring](docs/info.md#jump-audio).

`test/test_melody.py` checks every frame slot, two loops, pitch-divider timing,
pause and reset. `test/audio.v` checks PWM and jump priority. The prior jump-only
bitstream is retained locally under `build/before-melody/` for rollback.

### Flash melody scheduling

The shared score occupies 661 formerly erased padding bytes; allocated flash
size and every picture/sprite pixel are unchanged. Each byte holds N-1 for
pitch frequency 31500/(2*N) Hz; zero denotes silence (bits 7:6 are unused).
`make assets` packs the score from `assets/melody.json` into `graphics.bin`.
This leaves 15,723 bytes unused in the first picture bank's padding.

On row 481 at h=644, the existing sprite transaction instead reads
0xC3C000 + music_position. At its second data nibble, a six-bit latch captures
the pitch. The other bytes of the ordinary four-byte read are ignored for
music, retaining the existing transaction length. Background streaming resumes
at h=708. The ten-bit sequencer increments on row 482's final clock, after
the current byte has been captured, and wraps after index 660. It advances
once per enabled frame, with no per-note duration counter. Reset starts at
index zero and keeps audio silent until the first fetch.

No game-state transaction is displaced: that uses row 480. Visible sprite
rows are fetched normally before the next visible frame. Camera, picture-bank
and level changes do not participate in the music address.

`make test-music-flash` verifies all 661 bytes through the QSPI model while
varying camera offsets and picture banks, then checks restored sprite reads
and pitch retention. The previous deployed FPGA/flash pair remains unchanged;
this RTL requires the updated graphics asset and a rebuilt FPGA image together.
Current local synthesis: 11,561.0920 um^2, 244 flip-flops; hosted hardening
has not been rerun, so the earlier placement failure is not yet resolved.

### Tortoise stomp feedback

A stomp makes the tortoise harmless immediately and bounces Mario upward.
An upside-down closed shell is shown for three gameplay updates (200 ms at
15 Hz), then disappears. Mushrooms retain immediate disappearance. Encounter
state resets on checkpoint-section changes and death/restart as before.

This adds no ASIC RTL or registers. The offline compiler reuses the dead
enemy's animation field as a three-update countdown. Two extra 256 KiB
pictures supply the shell pose: level 7 at 0x4C0000–0x4FFFFF (bank 19), and
level 8 at 0x940000–0x97FFFF (bank 37). Existing game tables retain their sizes.
The manifest now allocates 13,369,600 bytes; 3,407,616 bytes remain outside
assets, including reserved/shared areas that must not be overwritten blindly.

Regenerate with `make assets` and `make images`. Deploy the matching rule
assets and shell pictures together. The connected FPGA/flash have not been
updated by this asset change.

### Three rotating collectible coins (not yet deployed)

Each checkpoint section has coins at local cells 7, 9, and 11, spanning
logical pixel rows 192–199. They are placed on clear background outside every
enemy patrol. Mario collects each coin independently on contact; it disappears
and remains absent until death, restart, level load, or a checkpoint-section
change. Returning to a previous section resets its coins, matching the local
enemy-encounter reset policy. There is no score, sound effect, or reward.

A four-phase full/half/edge/half-width overlay rotates around a vertical axis,
advancing at 15 Hz (one cycle per 267 ms). Mario is rendered in front of coins.
The compiler supplies three contact bits in result bits 43:41, formerly unused.
The flash transfer is still 11 nibbles; records remain eight bytes and all
picture and state-bank allocations are unchanged. Hardware keeps a three-bit
collection mask, checkpoint tag, and rotation phase instead of duplicating the
offline state graph for every collection pattern.

This changes the ASIC RTL and requires matched rule tables and a rebuilt FPGA
image. Local synthesis measures 11,561.0880 um^2 and 244 flip-flops: +788.2560
um^2 versus no coins, and 361.0880 um^2 above the 11,200 um^2 target. This
experimental feature is NOT area-qualified; hosted hardening is still pending.
Tests cover independent collection/reset behavior, all 32 checkpoint routes,
flash records, enemy separation, and rendered coin pixels.
