"""Tests for protocol creation and PDD output."""

import pytest
from flexnoc_dsl import NocProject, AXI, APB, OCP, AHB, AXI_Lite, ACE_Lite
from conftest import parse_pdd, find_objects, get_entry_value, find_entry, assert_pdd_valid


class TestAXIProtocol:
    """AXI protocol factory and PDD entries."""

    def test_axi_default(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i0", protocol=axi, clock=clk)
        noc.add_target("t0", protocol=axi, clock=clk, base=0, size="256M")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        root = parse_pdd(path)
        protos = find_objects(root, "protocol", "AXI_p")
        assert len(protos) == 1
        proto_entry = find_entry(protos[0], "protocol")
        assert proto_entry.get("value") == "AXI"
        assert get_entry_value(proto_entry, "wAddr") == "32"
        assert get_entry_value(proto_entry, "wData") == "64"

    def test_axi_with_id(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64, id=8))
        clk = noc.add_clock("clk")
        noc.add_initiator("i0", protocol=axi, clock=clk)
        noc.add_target("t0", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        root = parse_pdd(path)
        proto_entry = find_entry(find_objects(root, "protocol")[0], "protocol")
        assert get_entry_value(proto_entry, "wId") == "8"

    def test_axi_en_flags(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=32, read=False, write=True))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        root = parse_pdd(path)
        proto_entry = find_entry(find_objects(root, "protocol")[0], "protocol")
        assert get_entry_value(proto_entry, "enRead") == "False"
        assert get_entry_value(proto_entry, "enWrite") == "True"

    @pytest.mark.parametrize("data_width", [32, 64, 128, 256])
    def test_axi_data_widths(self, pdd_dir, data_width):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=data_width))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        root = parse_pdd(path)
        proto_entry = find_entry(find_objects(root, "protocol")[0], "protocol")
        assert get_entry_value(proto_entry, "wData") == str(data_width)


class TestAPBProtocol:
    """APB protocol factory and PDD entries."""

    def test_apb_basic(self, pdd_dir):
        noc = NocProject("t")
        apb = noc.add_protocol("APB_p", APB(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=apb, clock=clk)
        noc.add_target("t", protocol=apb, clock=clk, base=0, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        root = parse_pdd(path)
        proto_entry = find_entry(find_objects(root, "protocol")[0], "protocol")
        assert proto_entry.get("value") == "APB"


class TestOCPProtocol:
    """OCP_Lite protocol."""

    def test_ocp_basic(self, pdd_dir):
        noc = NocProject("t")
        ocp = noc.add_protocol("OCP_p", OCP(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=ocp, clock=clk)
        noc.add_target("t", protocol=ocp, clock=clk, base=0, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        root = parse_pdd(path)
        proto_entry = find_entry(find_objects(root, "protocol")[0], "protocol")
        assert proto_entry.get("value") == "OCP_Lite"


class TestAHBProtocol:
    """AHB protocol factory and PDD constraints."""

    def test_ahb_basic(self, pdd_dir):
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

        root = parse_pdd(path)
        proto_entry = find_entry(find_objects(root, "protocol")[0], "protocol")
        assert proto_entry.get("value") == "AHB"
        # AHB should NOT have enRead/enWrite/useFixed
        assert get_entry_value(proto_entry, "enRead") is None
        assert get_entry_value(proto_entry, "enWrite") is None

    def test_ahb_user_mapping(self, pdd_dir):
        """AHB targets should auto-generate HProt/XorHProt_6 userMapping."""
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

        # Check that spec target has userMapping with HProt
        with open(path) as f:
            content = f.read()
        assert "HProt" in content


class TestAXILiteProtocol:
    """AXI_Lite (subset of AXI)."""

    def test_axi_lite_pdd_type(self, pdd_dir):
        noc = NocProject("t")
        axil = noc.add_protocol("AXIL_p", AXI_Lite(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axil, clock=clk)
        noc.add_target("t", protocol=axil, clock=clk, base=0, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        root = parse_pdd(path)
        proto_entry = find_entry(find_objects(root, "protocol")[0], "protocol")
        # AXI_Lite maps to AXI type in PDD
        assert proto_entry.get("value") == "AXI"


class TestACELiteProtocol:
    """ACE_Lite (AXI variant)."""

    def test_ace_lite_pdd_type(self, pdd_dir):
        noc = NocProject("t")
        ace = noc.add_protocol("ACE_p", ACE_Lite(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=ace, clock=clk)
        noc.add_target("t", protocol=ace, clock=clk, base=0, size="256M")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        root = parse_pdd(path)
        proto_entry = find_entry(find_objects(root, "protocol")[0], "protocol")
        assert proto_entry.get("value") == "AXI"
