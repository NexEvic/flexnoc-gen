"""Tests for export configuration: single/multi, customerCells, synthesisTool, files."""

import pytest
from flexnoc_dsl import NocProject, AXI
from conftest import parse_pdd, find_objects, find_entry, get_entry_value, assert_pdd_valid


class TestSingleExport:
    """Basic export configuration."""

    def test_verilog_vcs(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog", simulator="VCS")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        root = parse_pdd(path)
        exports = find_objects(root, "exportOption")
        assert len(exports) >= 1
        exp = exports[0]
        exp_entry = find_entry(exp, "exportOption")
        assert exp_entry.get("value") == "Verilog"
        assert get_entry_value(exp_entry, "simulator") == "VCS"

    def test_auto_name_verilog(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        root = parse_pdd(path)
        exports = find_objects(root, "exportOption")
        assert any(e.get("name") == "exports.Vlog" for e in exports)


class TestMultiExport:
    """Multiple export options."""

    def test_two_exports(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog", simulator="VCS", name="exports.Vlog")
        noc.add_export("Verilog", simulator="ModelSim", name="exports.synth",
                       synthesis_tool="DC")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        root = parse_pdd(path)
        exports = find_objects(root, "exportOption")
        names = [e.get("name") for e in exports]
        assert "exports.Vlog" in names
        assert "exports.synth" in names


class TestSynthesisTool:
    """synthesisTool export option."""

    @pytest.mark.parametrize("tool", ["DC", "Genus"])
    def test_synthesis_tool(self, pdd_dir, tool):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog", synthesis_tool=tool)
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "synthesisTool" in content
        assert tool in content


class TestCustomerCells:
    """customerCells export option."""

    def test_customer_cells(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog", customer_cells={
            "GaterCell": "/path/to/gater.v",
        })
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "customerCells" in content
        assert "GaterCell" in content
        assert "descriptionPath" in content


class TestFilesOption:
    """files export option (SingleFile)."""

    def test_single_file(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog", files="SingleFile")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "SingleFile" in content


class TestExportCommand:
    """get_export_command() method."""

    def test_command_format(self):
        noc = NocProject("my_noc")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog", name="exports.Vlog")
        cmd = noc.get_export_command("my_noc.pdd", "/work/output")
        assert "FlexNoC" in cmd
        assert "-d False" in cmd
        assert "my_noc.pdd" in cmd
        assert "my_noc_struct" in cmd
        assert "exports.Vlog" in cmd
        assert "/work/output" in cmd
