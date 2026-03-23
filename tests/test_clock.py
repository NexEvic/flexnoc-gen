"""Tests for clock domain creation and PDD output."""

import pytest
from flexnoc_dsl import NocProject, AXI
from conftest import parse_pdd, find_objects, find_entry, get_entry_value, assert_pdd_valid


class TestClockBasic:
    """Basic clock domain creation."""

    def test_single_clock(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk_domain", freq="500MHz", port="clk", reset="rst_n")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        # Check clock regime in specification
        with open(path) as f:
            content = f.read()
        assert "clk_domain" in content
        assert "500000000" in content  # 500MHz in Hz

    @pytest.mark.parametrize("freq,expected_hz", [
        ("100MHz", "100000000"),
        ("1GHz", "1000000000"),
        ("250MHz", "250000000"),
        ("33MHz", "33000000"),
    ])
    def test_frequency_parsing(self, pdd_dir, freq, expected_hz):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk", freq=freq)
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert expected_hz in content


class TestMultiClock:
    """Multi-clock domain support."""

    def test_two_clocks(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk1 = noc.add_clock("clk_fast", freq="1GHz", port="clk_fast", reset="rst_n")
        clk2 = noc.add_clock("clk_slow", freq="100MHz", port="clk_slow", reset="rst_n2")
        noc.add_initiator("i0", protocol=axi, clock=clk1)
        noc.add_target("t0", protocol=axi, clock=clk2, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        with open(path) as f:
            content = f.read()
        assert "clk_fast" in content
        assert "clk_slow" in content

    def test_gated_clock(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk_root", freq="500MHz", clock_type="Root")
        gated = noc.add_clock("clk_gated", freq="500MHz", port="gclk",
                              reset="rst_n", clock_type="Gated")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=gated, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "Gated" in content


class TestClockReferences:
    """Clock with voltage_ref and power_ref."""

    def test_voltage_ref(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_voltage("VDD", value="0.81")
        clk = noc.add_clock("clk", freq="500MHz", voltage_ref="VDD")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "VDD" in content

    def test_power_ref(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_power_domain("MAIN_dom", kind="ALWAYS_ON")
        clk = noc.add_clock("clk", freq="500MHz", power_ref="MAIN_dom")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "MAIN_dom" in content
        assert "clockManager" in content

    def test_clock_comment(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk", freq="500MHz", comment="Main clock")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "Main clock" in content
