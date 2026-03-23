"""Tests for PowerDomain, Voltage, ActivityZone, IPpowerDomain."""

import pytest
from flexnoc_dsl import NocProject, AXI, PowerDomain, Voltage
from conftest import parse_pdd, find_objects, assert_pdd_valid


class TestPowerDomain:
    """Power domain creation and PDD output."""

    def test_always_on(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        pd = noc.add_power_domain("MAIN_dom", kind="ALWAYS_ON")
        clk = noc.add_clock("clk", freq="500MHz", power_ref="MAIN_dom")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        with open(path) as f:
            content = f.read()
        assert "MAIN_dom" in content
        assert "ALWAYS_ON" in content

    def test_supply_domain(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_power_domain("SUPPLY_dom", kind="SUPPLY")
        clk = noc.add_clock("clk", power_ref="SUPPLY_dom")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "SUPPLY" in content

    def test_power_domain_comment(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_power_domain("DOM", kind="ALWAYS_ON", comment="Main domain")
        clk = noc.add_clock("clk", power_ref="DOM")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "Main domain" in content


class TestActivityZone:
    """Activity zones within power domains."""

    def test_activity_zones(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_power_domain("DOM", kind="ALWAYS_ON",
                             activity_zones=["zone_A", "zone_B"])
        clk = noc.add_clock("clk", power_ref="DOM")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "zone_A" in content
        assert "zone_B" in content


class TestVoltage:
    """Voltage object creation."""

    def test_voltage_basic(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_voltage("VDD", value="0.81")
        clk = noc.add_clock("clk", voltage_ref="VDD")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)
        assert_pdd_valid(path)

        with open(path) as f:
            content = f.read()
        assert "VDD" in content
        assert "0.81" in content

    def test_voltage_comment(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_voltage("VDD", value="0.9", comment="Core voltage")
        clk = noc.add_clock("clk", voltage_ref="VDD")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "Core voltage" in content


class TestIPpowerDomain:
    """IP power domain on socket."""

    def test_initiator_power_domain(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_power_domain("CPU_dom", kind="ALWAYS_ON")
        clk = noc.add_clock("clk", power_ref="CPU_dom")
        noc.add_initiator("cpu", protocol=axi, clock=clk,
                          power_domain="CPU_dom")
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "IPpowerDomain" in content
        assert "CPU_dom" in content

    def test_target_power_domain(self, pdd_dir):
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_power_domain("MEM_dom", kind="ALWAYS_ON")
        clk = noc.add_clock("clk", power_ref="MEM_dom")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G",
                       power_domain="MEM_dom")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "IPpowerDomain" in content


class TestClockManagerPower:
    """clockManager node when power domains exist."""

    def test_clock_manager_generated(self, pdd_dir):
        """When power domain + power_ref exist, clockManager should appear."""
        noc = NocProject("t")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_power_domain("DOM", kind="ALWAYS_ON")
        clk = noc.add_clock("clk", power_ref="DOM")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        path = str(pdd_dir / "test.pdd")
        noc.write_pdd(path)

        with open(path) as f:
            content = f.read()
        assert "clockManager" in content
