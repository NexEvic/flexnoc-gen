"""Tests for initiator/target socket creation and PDD output."""

import pytest
from flexnoc_dsl import NocProject, AXI, APB
from conftest import parse_pdd, find_objects, find_entry, get_entry_value, assert_pdd_valid


class TestInitiatorBasic:
    """Initiator socket creation."""

    def test_default_params(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        init = noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        with open(path) as f:
            content = f.read()
        assert "cpu" in content
        # nPendingTrans default 4
        assert "nPendingTrans" in content

    def test_custom_pending(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk,
                          pending_trans=8, pending_ids=2)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "8" in content  # pending_trans

    def test_initiator_comment(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk, comment="CPU port")
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "CPU port" in content

    def test_clock_gating(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk, clock_gating="AutoGating")
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "AutoGating" in content


class TestTargetBasic:
    """Target socket creation."""

    def test_default_target(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0x0, size="256M",
                       pending_trans=16)
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

    @pytest.mark.parametrize("size_str,expected_bytes", [
        ("1K", 1024),
        ("64K", 65536),
        ("256M", 256 * 1024 * 1024),
        ("1G", 1024 * 1024 * 1024),
    ])
    def test_size_parsing(self, pdd_dir, size_str, expected_bytes):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        targ = noc.add_target("t", protocol=axi, clock=clk,
                              base=0, size=size_str)
        assert targ.size == expected_bytes
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

    def test_seq_id_allocation(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G",
                       seq_id_allocation="ROUND_ROBIN")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "seqIdAllocation" in content
        assert "ROUND_ROBIN" in content


class TestUsePress:
    """usePress feature on initiator."""

    def test_use_press_pdd(self, pdd_dir):
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
        # Press port should have width = urgency_levels
        assert "tacticalPorts" in content


class TestConversion:
    """Protocol conversion on initiator/target."""

    def test_initiator_conversion(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk,
                          conversion={"dataWidth": "128"})
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "conversion" in content
        assert "128" in content

    def test_target_conversion(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G",
                       conversion={"dataWidth": "32"})
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "conversion" in content


class TestSpecialsMapping:
    """specials_mapping on target socket."""

    def test_specials_in_pdd(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G",
                       specials_mapping={
                           "AWCache": {"Bufferable": "#0"},
                           "ARCache": {"Modifiable": "#1"},
                       })
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "AWCache" in content
        assert "Bufferable" in content
