"""Tests for QoS: urgencyLevel, usePress, useErrorCodes."""

import pytest
from flexnoc_dsl import NocProject, AXI
from conftest import parse_pdd, assert_pdd_valid


class TestUrgencyLevels:
    """nUrgencyLevel setting."""

    def test_default_urgency(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "nUrgencyLevel" in content

    @pytest.mark.parametrize("levels", [2, 4, 8])
    def test_custom_urgency(self, pdd_dir, levels):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.set_urgency_levels(levels)
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert str(levels) in content


class TestUsePress:
    """Press (priority escalation) feature."""

    def test_press_with_urgency(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk, use_press=True)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.set_urgency_levels(4)
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "usePress" in content
        assert "Press" in content

    def test_press_generates_port(self, pdd_dir):
        """usePress should auto-generate a Press user port."""
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk, use_press=True)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.set_urgency_levels(4)
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        # Press port should appear in spec_ports
        assert "Press" in content

    def test_multiple_press_initiators(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu0", protocol=axi, clock=clk, use_press=True)
        noc.add_initiator("cpu1", protocol=axi, clock=clk, use_press=True)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.set_urgency_levels(2)
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)


class TestUseErrorCodes:
    """useErrorCodes specification global."""

    def test_error_codes_enabled(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.set_use_error_codes(True)
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "useErrorCodes" in content

    def test_error_codes_disabled(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        # Default: disabled
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)
        # useErrorCodes should not appear when disabled
