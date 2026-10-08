"""Public-pin checks for RTL and gate-level CI; make check tests gameplay."""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, Timer


@cocotb.test()
async def test_vga_and_bus_release(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0xF7
    # A reset transition initializes the raster, including at power-on.
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 8)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 8)
    await FallingEdge(dut.clk)
    assert int(dut.uio_oe.value) == 0, "Maintenance must release BIDIR"
    for _ in range(800):
        if not (int(dut.uo_out.value) & 0x80):
            break
        await Timer(40, unit="ns")
    else:
        assert False, "No HSYNC"
    # Check all 525 lines, 96-pixel HSYNC, blanking and two VSYNC lines.
    vsync_lines = 0
    for _ in range(525):
        video = int(dut.uo_out.value)
        assert video & 0x80 == 0
        assert video & 0x77 == 0, "RGB must be black during horizontal blanking"
        vsync_lines += not bool(video & 0x08)
        assert int(dut.uio_oe.value) == 0
        await Timer(95 * 40, unit="ns")
        assert int(dut.uo_out.value) & 0x80 == 0
        await Timer(40, unit="ns")
        assert int(dut.uo_out.value) & 0x80
        await Timer(703 * 40, unit="ns")
        assert int(dut.uo_out.value) & 0x80
        await Timer(40, unit="ns")
    assert vsync_lines == 2
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 1000)
    await FallingEdge(dut.clk)
    assert int(dut.uio_oe.value) & 0xC9 == 0xC9
    assert int(dut.uio_out.value) & 0x40 == 0x40, "PSRAM A must stay deselected"
