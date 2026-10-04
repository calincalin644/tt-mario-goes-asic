# Simulation

From the repository root, install `test/requirements.txt` and Icarus Verilog.

- `make check`: generates assets and runs the complete gameplay, QSPI, controller,
  DIP-selection, interpolation, pixel and maintenance tests.
- `make smoke`: checks VGA timing, blanking, bus release during reset and PSRAM
  deselection through public pins using the template Cocotb harness.

The GDS workflow reuses the Cocotb test with `GATES=yes` and its generated
`test/gate_level_netlist.v`. A PDK and hardened netlist are required; RTL-only
checks do not establish gate-level success. The full gameplay tests access RTL
internals and therefore run separately from gate-level CI.

Tests produce ignored files under `build/` and `test/sim_build/`. The Cocotb
waveform is `test/tb.fst`; open it directly in your waveform viewer.
