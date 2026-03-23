"""Tests for mixed protocol scenarios and auto nReassemblyBuffer."""

import pytest
from flexnoc_dsl import NocProject, AXI, APB, AHB, AXI_Lite, ACE_Lite
from conftest import parse_pdd, assert_pdd_valid


class TestMixedAXIAPB:
    """AXI + APB mixed protocol."""

    def test_axi_apb_reassembly(self, pdd_dir):
        """Mixed AXI+APB should auto-add nReassemblyBuffer=2."""
        noc = NocProject("t")
        axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64))
        apb = noc.add_protocol("APB_p", APB(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="256M")
        noc.add_target("io", protocol=apb, clock=clk, base=0x10000000, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        with open(path) as f:
            content = f.read()
        assert "nReassemblyBuffer" in content


class TestMixedAXIAHB:
    """AXI + AHB mixed protocol."""

    def test_axi_ahb_reassembly(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64))
        ahb = noc.add_protocol("AHB_p", AHB(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="256M")
        noc.add_target("periph", protocol=ahb, clock=clk, base=0x10000000, size="64K",
                       pending_trans=1)
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        with open(path) as f:
            content = f.read()
        assert "nReassemblyBuffer" in content
        assert "AHB" in content

    def test_ahb_pending_trans_one(self, pdd_dir):
        """AHB target with pending_trans=1 should work."""
        noc = NocProject("t")
        ahb = noc.add_protocol("AHB_p", AHB(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=ahb, clock=clk)
        noc.add_target("t", protocol=ahb, clock=clk, base=0, size="64K",
                       pending_trans=1)
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)


class TestMixedAXILite:
    """AXI + AXI_Lite mixed scenario."""

    def test_axi_axilite_mix(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64, id=4))
        axil = noc.add_protocol("AXIL_p", AXI_Lite(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="256M")
        noc.add_target("cfg", protocol=axil, clock=clk, base=0x10000000, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)


class TestMixedACELite:
    """ACE_Lite in mixed configuration."""

    def test_ace_lite_with_axi(self, pdd_dir):
        noc = NocProject("t")
        ace = noc.add_protocol("ACE_p", ACE_Lite(addr=32, data=64))
        axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=ace, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)


class TestPureProtocol:
    """Pure single-protocol configs should NOT add nReassemblyBuffer."""

    def test_pure_axi_no_reassembly(self, pdd_dir):
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
        assert "nReassemblyBuffer" not in content

    def test_pure_apb_no_reassembly(self, pdd_dir):
        noc = NocProject("t")
        apb = noc.add_protocol("p", APB(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=apb, clock=clk)
        noc.add_target("t", protocol=apb, clock=clk, base=0, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "nReassemblyBuffer" not in content


class TestThreeProtocols:
    """Three different protocols in one NoC."""

    def test_axi_apb_ahb(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64))
        apb = noc.add_protocol("APB_p", APB(addr=32, data=32))
        ahb = noc.add_protocol("AHB_p", AHB(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="256M")
        noc.add_target("io", protocol=apb, clock=clk, base=0x10000000, size="64K")
        noc.add_target("periph", protocol=ahb, clock=clk,
                       base=0x20000000, size="64K", pending_trans=1)
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        with open(path) as f:
            content = f.read()
        assert "AXI" in content
        assert "APB" in content
        assert "AHB" in content
