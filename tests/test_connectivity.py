"""Tests for connectivity: connect_all, connect, disconnect."""

import pytest
from flexnoc_dsl import NocProject, AXI
from conftest import parse_pdd, assert_pdd_valid


class TestConnectAll:
    """Full mesh connectivity."""

    def test_connect_all_2x2(self, pdd_dir):
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

        # All 4 connections should exist
        assert noc._connectivity[("i0", "t0")] is True
        assert noc._connectivity[("i0", "t1")] is True
        assert noc._connectivity[("i1", "t0")] is True
        assert noc._connectivity[("i1", "t1")] is True

    def test_auto_connect_all(self, pdd_dir):
        """If no connect is called, _finalize auto-connects."""
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i0", protocol=axi, clock=clk)
        noc.add_target("t0", protocol=axi, clock=clk, base=0, size="1G")
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        # Should have auto-connected
        assert noc._connectivity[("i0", "t0")] is True


class TestSelectiveConnect:
    """Selective connectivity."""

    def test_connect_specific(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i0", protocol=axi, clock=clk)
        noc.add_initiator("i1", protocol=axi, clock=clk)
        noc.add_target("t0", protocol=axi, clock=clk, base=0, size="256M")
        noc.add_target("t1", protocol=axi, clock=clk, base=0x10000000, size="256M")
        noc.connect("i0", ["t0", "t1"])
        noc.connect("i1", ["t0"])  # i1 only connects to t0
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        assert noc._connectivity[("i0", "t0")] is True
        assert noc._connectivity[("i0", "t1")] is True
        assert noc._connectivity[("i1", "t0")] is True
        assert noc._connectivity.get(("i1", "t1"), False) is False


class TestDisconnect:
    """Disconnect after connect_all."""

    def test_disconnect(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i0", protocol=axi, clock=clk)
        noc.add_initiator("i1", protocol=axi, clock=clk)
        noc.add_target("t0", protocol=axi, clock=clk, base=0, size="256M")
        noc.add_target("t1", protocol=axi, clock=clk, base=0x10000000, size="256M")
        noc.connect_all()
        noc.disconnect("i1", "t1")
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        assert noc._connectivity[("i1", "t1")] is False
        assert noc._connectivity[("i0", "t0")] is True
