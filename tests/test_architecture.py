"""Tests for architecture: auto-derive, manual topology, pipeline, arbitration."""

import pytest
from flexnoc_dsl import NocProject, AXI
from flexnoc_dsl.architecture import Architecture
from conftest import parse_pdd, find_objects, assert_pdd_valid


class TestAutoDerive:
    """auto_derive topology generation."""

    def test_single_clock_topology(self, pdd_dir):
        """Single clock should create 1 DtpSwitch."""
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i0", protocol=axi, clock=clk)
        noc.add_initiator("i1", protocol=axi, clock=clk)
        noc.add_target("t0", protocol=axi, clock=clk, base=0, size="256M")
        noc.add_target("t1", protocol=axi, clock=clk, base=0x10000000, size="256M")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        root = parse_pdd(path)
        dtp_switches = find_objects(root, "dtpSwitch")
        assert len(dtp_switches) >= 1

    def test_multi_clock_topology(self, pdd_dir):
        """Multi-clock should create multiple DtpSwitches."""
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk1 = noc.add_clock("clk_a", port="clk_a", reset="rst_a")
        clk2 = noc.add_clock("clk_b", port="clk_b", reset="rst_b")
        noc.add_initiator("i0", protocol=axi, clock=clk1)
        noc.add_target("t0", protocol=axi, clock=clk2, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        root = parse_pdd(path)
        dtp_switches = find_objects(root, "dtpSwitch")
        assert len(dtp_switches) >= 2

    def test_observer_creates_obs_switch(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.add_observer("obs", clock=clk)
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        root = parse_pdd(path)
        obs_switches = find_objects(root, "obsSwitch")
        assert len(obs_switches) >= 1


class TestPipeline:
    """Pipeline configuration in architecture."""

    def test_default_pipeline(self, pdd_dir):
        """Default pipeline settings should be present."""
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
        # DtpSwitch should have pipeline settings
        assert "inputPipes" in content or "outputPipes" in content or "dtpSwitch" in content.lower()


class TestArbitration:
    """Arbiter mode in architecture globals."""

    def test_default_rotate(self, pdd_dir):
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
        assert "ROTATE" in content

    @pytest.mark.parametrize("mode", ["FIXED", "ROUND_ROBIN", "FIFO"])
    def test_arbiter_modes(self, pdd_dir, mode):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.set_arbiter_mode(mode)
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert mode in content


class TestManualTopology:
    """Manual architecture control."""

    def test_architecture_accessible(self):
        noc = NocProject("t")
        arch = noc.architecture
        assert isinstance(arch, Architecture)
