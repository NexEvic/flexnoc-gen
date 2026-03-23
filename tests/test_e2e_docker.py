"""Docker E2E integration tests — require FlexNoC Docker image.

Run with: pytest -m docker tests/test_e2e_docker.py
"""

import os
import pytest

from flexnoc_dsl import NocProject, AXI, APB, AHB, AXI_Lite

pytestmark = pytest.mark.docker


class TestBasicE2E:
    """Basic FlexNoC export via Docker."""

    def test_simple_2x2_export(self, pdd_dir, docker_runner, docker_output_dir):
        """Minimal 2x2 AXI crossbar → export → verify output files."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_basic")
        axi = noc.add_protocol("p", AXI(addr=32, data=64, id=4))
        clk = noc.add_clock("clk", freq="500MHz")
        noc.add_initiator("init_0", protocol=axi, clock=clk)
        noc.add_initiator("init_1", protocol=axi, clock=clk)
        noc.add_target("targ_0", protocol=axi, clock=clk, base=0, size="256M")
        noc.add_target("targ_1", protocol=axi, clock=clk, base=0x10000000, size="256M")
        noc.connect_all()
        noc.set_export("Verilog", simulator="VCS")

        pdd_path = str(pdd_dir / "e2e_basic.pdd")
        noc.write_pdd(pdd_path)

        result = docker_runner(pdd_path, "e2e_basic_struct", "exports.Vlog",
                               output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

        # Verify output files
        assert os.path.exists(os.path.join(output_path, "e2e_basic_struct.v"))
        assert os.path.exists(os.path.join(output_path, "simulationFileNames.txt"))

    def test_single_init_target(self, pdd_dir, docker_runner, docker_output_dir):
        """1x1 configuration."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_1x1")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")

        pdd_path = str(pdd_dir / "e2e_1x1.pdd")
        noc.write_pdd(pdd_path)

        result = docker_runner(pdd_path, "e2e_1x1_struct", "exports.Vlog",
                               output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"


class TestProtocolE2E:
    """Protocol-specific E2E tests."""

    def test_apb_export(self, pdd_dir, docker_runner, docker_output_dir):
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_apb")
        apb = noc.add_protocol("p", APB(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=apb, clock=clk)
        noc.add_target("t", protocol=apb, clock=clk, base=0, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")

        pdd_path = str(pdd_dir / "e2e_apb.pdd")
        noc.write_pdd(pdd_path)

        result = docker_runner(pdd_path, "e2e_apb_struct", "exports.Vlog",
                               output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_ahb_export(self, pdd_dir, docker_runner, docker_output_dir):
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_ahb")
        ahb = noc.add_protocol("p", AHB(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=ahb, clock=clk)
        noc.add_target("t", protocol=ahb, clock=clk, base=0, size="64K",
                       pending_trans=1)
        noc.connect_all()
        noc.set_export("Verilog")

        pdd_path = str(pdd_dir / "e2e_ahb.pdd")
        noc.write_pdd(pdd_path)

        result = docker_runner(pdd_path, "e2e_ahb_struct", "exports.Vlog",
                               output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_mixed_axi_apb_export(self, pdd_dir, docker_runner, docker_output_dir):
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_mix")
        axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64))
        apb = noc.add_protocol("APB_p", APB(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="256M")
        noc.add_target("io", protocol=apb, clock=clk, base=0x10000000, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")

        pdd_path = str(pdd_dir / "e2e_mix.pdd")
        noc.write_pdd(pdd_path)

        result = docker_runner(pdd_path, "e2e_mix_struct", "exports.Vlog",
                               output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"


class TestFeatureE2E:
    """Feature-specific E2E tests."""

    def test_power_domain_export(self, pdd_dir, docker_runner, docker_output_dir):
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_power")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_power_domain("MAIN_dom", kind="ALWAYS_ON")
        noc.add_voltage("VDD", value="0.81")
        clk = noc.add_clock("clk", voltage_ref="VDD", power_ref="MAIN_dom")
        noc.add_initiator("i", protocol=axi, clock=clk, power_domain="MAIN_dom")
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G",
                       power_domain="MAIN_dom")
        noc.connect_all()
        noc.set_export("Verilog")

        pdd_path = str(pdd_dir / "e2e_power.pdd")
        noc.write_pdd(pdd_path)

        result = docker_runner(pdd_path, "e2e_power_struct", "exports.Vlog",
                               output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_multi_clock_export(self, pdd_dir, docker_runner, docker_output_dir):
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_mclock")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk1 = noc.add_clock("clk_fast", freq="1GHz", port="clk_fast", reset="rst1")
        clk2 = noc.add_clock("clk_slow", freq="100MHz", port="clk_slow", reset="rst2")
        noc.add_initiator("cpu", protocol=axi, clock=clk1)
        noc.add_target("mem", protocol=axi, clock=clk2, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")

        pdd_path = str(pdd_dir / "e2e_mclock.pdd")
        noc.write_pdd(pdd_path)

        result = docker_runner(pdd_path, "e2e_mclock_struct", "exports.Vlog",
                               output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_qos_full_export(self, pdd_dir, docker_runner, docker_output_dir):
        """Full QoS: urgency + press + error codes."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_qos")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk, use_press=True)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.set_urgency_levels(4)
        noc.set_arbiter_mode("ROUND_ROBIN")
        noc.set_use_error_codes(True)
        noc.connect_all()
        noc.set_export("Verilog")

        pdd_path = str(pdd_dir / "e2e_qos.pdd")
        noc.write_pdd(pdd_path)

        result = docker_runner(pdd_path, "e2e_qos_struct", "exports.Vlog",
                               output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_user_flags_export(self, pdd_dir, docker_runner, docker_output_dir):
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_flags")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_target("mem", protocol=axi, clock=clk, base=0, size="1G")
        noc.add_user_flag("0_debug")
        noc.add_user_flag("1_secure")
        noc.add_mode_flag("test_mode", port="i_test")
        noc.connect_all()
        noc.set_export("Verilog")

        pdd_path = str(pdd_dir / "e2e_flags.pdd")
        noc.write_pdd(pdd_path)

        result = docker_runner(pdd_path, "e2e_flags_struct", "exports.Vlog",
                               output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"
