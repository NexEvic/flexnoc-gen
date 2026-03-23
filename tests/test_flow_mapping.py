"""Tests for Flow, Mapping, interleaving, and address handling."""

import pytest
from flexnoc_dsl import NocProject, AXI
from flexnoc_dsl.socket import Flow, Mapping, create_interleaved_mappings, compute_interleave_mask
from conftest import parse_pdd, assert_pdd_valid


class TestMapping:
    """Mapping address calculation."""

    def test_mapping_effective_mask(self):
        m = Mapping(name="m0", global_address=0x0, mask=0x0FFFFFFF, access="ReadWrite")
        assert m.effective_mask() == 0x0FFFFFFF

    def test_mapping_with_comment(self):
        m = Mapping(name="m0", global_address=0x0, mask=0x0FFFFFFF,
                    access="ReadWrite", comment="test mapping")
        assert m.comment == "test mapping"


class TestInterleave:
    """create_interleaved_mappings utility."""

    def test_two_way_interleave(self):
        mappings = create_interleaved_mappings(
            num_targets=2, stripe_size=4096,
            total_size=2 * 1024 * 1024 * 1024,
            base_address=0, access="ReadWrite",
        )
        assert len(mappings) == 2
        # Each target should get one mapping
        assert len(mappings[0]) >= 1
        assert len(mappings[1]) >= 1

    def test_four_way_interleave(self):
        mappings = create_interleaved_mappings(
            num_targets=4, stripe_size=4096,
            total_size=4 * 1024 * 1024 * 1024,
            base_address=0, access="ReadWrite",
        )
        assert len(mappings) == 4

    def test_compute_mask(self):
        mask = compute_interleave_mask(1024*1024*1024, 4096, 2)
        assert mask > 0


class TestInterleavedTargets:
    """add_interleaved_targets PDD generation."""

    def test_two_way_ddr(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_interleaved_targets(
            ["DDR0", "DDR1"], protocol=axi, clock=clk,
            total_base=0x0, total_size="2G", stripe_size="4K",
        )
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        with open(path) as f:
            content = f.read()
        assert "DDR0" in content
        assert "DDR1" in content
        # Interleaved targets use matching flow/mapping structure
        assert "globalAddress" in content

    def test_interleaved_min_size(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_interleaved_targets(
            ["DDR0", "DDR1"], protocol=axi, clock=clk,
            total_base=0x0, total_size="2G", stripe_size="4K",
            min_interleave_size=64,
        )
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)


class TestFlowMapping:
    """Flow and mapping in PDD output."""

    def test_two_targets_two_flows(self, pdd_dir):
        """Each target should have proper flow and mapping entries."""
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t0", protocol=axi, clock=clk, base=0x0, size="256M")
        noc.add_target("t1", protocol=axi, clock=clk, base=0x10000000, size="256M")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        # Both targets should appear in mapping
        assert "t0" in content
        assert "t1" in content
        assert "globalAddress" in content
