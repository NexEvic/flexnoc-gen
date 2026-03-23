"""Docker E2E integration tests — require FlexNoC Docker image.

Run with: pytest -m docker tests/test_e2e_docker.py
"""

import os
import pytest

from flexnoc_dsl import NocProject, AXI, APB, OCP, AHB, AXI_Lite, ACE_Lite

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


# ---------------------------------------------------------------------------
# Extended protocol coverage
# ---------------------------------------------------------------------------

class TestProtocolFullE2E:
    """RTL generation for protocols not yet covered in TestProtocolE2E."""

    def test_ocp_export(self, pdd_dir, docker_runner, docker_output_dir):
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_ocp")
        ocp = noc.add_protocol("p", OCP(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=ocp, clock=clk)
        noc.add_target("t", protocol=ocp, clock=clk, base=0, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_ocp.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_ocp_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_axi_lite_export(self, pdd_dir, docker_runner, docker_output_dir):
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_axil")
        axil = noc.add_protocol("p", AXI_Lite(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axil, clock=clk)
        noc.add_target("t", protocol=axil, clock=clk, base=0, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_axil.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_axil_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_ace_lite_export(self, pdd_dir, docker_runner, docker_output_dir):
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_ace")
        ace = noc.add_protocol("p", ACE_Lite(addr=32, data=64, id=4))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=ace, clock=clk)
        noc.add_target("t", protocol=ace, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_ace.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_ace_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_axi_extensions_export(self, pdd_dir, docker_runner, docker_output_dir):
        """AXI with wReqUser / wRspUser (AXI4/5 user signals)."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_axiext")
        axi = noc.add_protocol("p", AXI(addr=32, data=64, id=8, wReqUser=1, wRspUser=1))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_axiext.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_axiext_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"


# ---------------------------------------------------------------------------
# Socket-level features
# ---------------------------------------------------------------------------

class TestSocketE2E:
    """Socket feature E2E RTL generation."""

    def test_interleaved_ddr_export(self, pdd_dir, docker_runner, docker_output_dir):
        """2-way address-interleaved DDR targets."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_interleave")
        axi = noc.add_protocol("p", AXI(addr=32, data=64, id=8))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu", protocol=axi, clock=clk)
        noc.add_interleaved_targets(
            names=["DDR0", "DDR1"],
            protocol=axi, clock=clk,
            total_base=0, total_size="2G",
            stripe_size="1K", min_interleave_size=0,
        )
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_interleave.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_interleave_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_clock_gating_export(self, pdd_dir, docker_runner, docker_output_dir):
        """clockGating=#Common on both initiator and target sockets."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_clkgate")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk, clock_gating="#Common")
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G",
                       clock_gating="#Common")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_clkgate.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_clkgate_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_custom_specials_export(self, pdd_dir, docker_runner, docker_output_dir):
        """Target with custom specials_mapping (ARCache/AWCache/Prot constants)."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_specials")
        axi = noc.add_protocol("p", AXI(addr=32, data=64, id=4))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G",
                       specials_mapping={
                           "ARCache": {"CONST_1": "#0,1,2,3"},
                           "AWCache": {"CONST_1": "#0,1,2,3"},
                           "Prot":    {"CONST_1": "#0,1,2"},
                       })
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_specials.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_specials_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_use_press_export(self, pdd_dir, docker_runner, docker_output_dir):
        """usePress on initiator socket."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_press")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk, use_press=True)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_press.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_press_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_seq_id_allocation_export(self, pdd_dir, docker_runner, docker_output_dir):
        """seqIdAllocation=DYNAMIC on target."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_seqid")
        axi = noc.add_protocol("p", AXI(addr=32, data=64, id=4))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G",
                       seq_id_allocation="DYNAMIC")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_seqid.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_seqid_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"


# ---------------------------------------------------------------------------
# Port and flag features
# ---------------------------------------------------------------------------

class TestPortE2E:
    """Port, flag, and observer E2E RTL generation."""

    def test_user_port_export(self, pdd_dir, docker_runner, docker_output_dir):
        """UserPort input + ModeFlag."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_port")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.add_user_port("cfg_in", direction="in", width=4)
        noc.add_mode_flag("scan_mode", port="i_scan")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_port.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_port_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_user_flag_mapping_export(self, pdd_dir, docker_runner, docker_output_dir):
        """UserFlags with userMapping on initiator and target."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_uf_map")
        axi = noc.add_protocol("p", AXI(addr=32, data=64, id=4))
        clk = noc.add_clock("clk")
        noc.add_user_flag("0_debug")
        noc.add_user_flag("1_secure")
        init = noc.add_initiator("i", protocol=axi, clock=clk)
        init.user_mapping = {
            "userFlags": {"0_debug": "CONST_0", "1_secure": "CONST_0"}
        }
        targ = noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        targ.user_mapping = {
            "ARCache": {"1_secure": 0, "0_debug": 1},
            "AWCache": {"1_secure": 0, "0_debug": 1},
            "Prot":    {"0_debug": 0, "1_secure": 1},
        }
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_uf_map.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_uf_map_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"


# ---------------------------------------------------------------------------
# Architecture features
# ---------------------------------------------------------------------------

class TestArchitectureE2E:
    """Arbitration and topology E2E RTL generation."""

    def test_round_robin_arbitration_export(self, pdd_dir, docker_runner, docker_output_dir):
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_arb")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i0", protocol=axi, clock=clk)
        noc.add_initiator("i1", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.set_arbiter_mode("ROUND_ROBIN")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_arb.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_arb_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_urgency_levels_export(self, pdd_dir, docker_runner, docker_output_dir):
        """4 urgency levels in QoS config."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_urgency")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.set_urgency_levels(4)
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_urgency.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_urgency_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_use_error_codes_export(self, pdd_dir, docker_runner, docker_output_dir):
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_errcodes")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.set_use_error_codes(True)
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_errcodes.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_errcodes_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"


# ---------------------------------------------------------------------------
# Export options
# ---------------------------------------------------------------------------

class TestExportOptionsE2E:
    """Export configuration E2E RTL generation."""

    def test_multi_export_export(self, pdd_dir, docker_runner, docker_output_dir):
        """PDD with two export options — RTL from the first one."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_multiexp")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog", simulator="VCS", name="exports.Vlog")
        noc.add_export("Verilog", simulator="ModelSim", name="exports.sim",
                       files="SingleFile")
        pdd_path = str(pdd_dir / "e2e_multiexp.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_multiexp_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_synthesis_dc_export(self, pdd_dir, docker_runner, docker_output_dir):
        """Export with synthesisTool=DC."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_dc")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        clk = noc.add_clock("clk")
        noc.add_initiator("i", protocol=axi, clock=clk)
        noc.add_target("t", protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog", simulator="VCS", name="exports.Vlog")
        noc.add_export("Verilog", simulator="ModelSim", name="exports.dc",
                       synthesis_tool="DC")
        pdd_path = str(pdd_dir / "e2e_dc.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_dc_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"


# ---------------------------------------------------------------------------
# Mixed-protocol NoCs
# ---------------------------------------------------------------------------

class TestMixedProtocolE2E:
    """Mixed-protocol E2E RTL generation."""

    def test_axi_axilite_export(self, pdd_dir, docker_runner, docker_output_dir):
        """AXI initiator → AXI target + AXI-Lite peripheral."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_axi_axil")
        axi  = noc.add_protocol("AXI_p",  AXI(addr=32, data=64, id=4))
        axil = noc.add_protocol("AXIL_p", AXI_Lite(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu",    protocol=axi,  clock=clk)
        noc.add_target("sram",   protocol=axi,  clock=clk, base=0,          size="256M")
        noc.add_target("periph", protocol=axil, clock=clk, base=0x10000000, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_axi_axil.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_axi_axil_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_axi_apb_ahb_export(self, pdd_dir, docker_runner, docker_output_dir):
        """3-protocol: AXI initiator → AXI + APB + AHB targets."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_3prot")
        axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64, id=4))
        apb = noc.add_protocol("APB_p", APB(addr=32, data=32))
        ahb = noc.add_protocol("AHB_p", AHB(addr=32, data=32))
        clk = noc.add_clock("clk")
        noc.add_initiator("cpu",  protocol=axi, clock=clk)
        noc.add_target("ddr",  protocol=axi, clock=clk, base=0,          size="256M")
        noc.add_target("io",   protocol=apb, clock=clk, base=0x10000000, size="64K")
        noc.add_target("sram", protocol=ahb, clock=clk, base=0x20000000, size="64K",
                       pending_trans=1)
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_3prot.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_3prot_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_ace_lite_with_axi_export(self, pdd_dir, docker_runner, docker_output_dir):
        """ACE-Lite initiator → AXI target (cross-protocol conversion)."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_ace_axi")
        axi = noc.add_protocol("AXI_p", AXI(addr=32,  data=64, id=4))
        ace = noc.add_protocol("ACE_p", ACE_Lite(addr=32, data=64, id=4))
        clk = noc.add_clock("clk")
        noc.add_initiator("ace_i", protocol=ace, clock=clk)
        noc.add_target("mem",     protocol=axi, clock=clk, base=0, size="1G")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_ace_axi.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_ace_axi_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"

    def test_multi_clock_mixed_protocol_export(self, pdd_dir, docker_runner, docker_output_dir):
        """Multi-clock + mixed protocol (AXI + APB across clock domains)."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_mc_mix")
        axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64, id=4))
        apb = noc.add_protocol("APB_p", APB(addr=32, data=32))
        clk_fast = noc.add_clock("clk_fast", freq="500MHz", port="clk_fast", reset="rst_fast")
        clk_slow = noc.add_clock("clk_slow", freq="100MHz", port="clk_slow", reset="rst_slow")
        noc.add_initiator("cpu",  protocol=axi, clock=clk_fast)
        noc.add_target("ddr",  protocol=axi, clock=clk_fast, base=0,          size="256M")
        noc.add_target("uart", protocol=apb, clock=clk_slow, base=0x10000000, size="64K")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_mc_mix.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_mc_mix_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"


# ---------------------------------------------------------------------------
# Power domain + clock reference combinations
# ---------------------------------------------------------------------------

class TestPowerClockE2E:
    """Power domain and voltage reference E2E RTL generation."""

    def test_supply_domain_export(self, pdd_dir, docker_runner, docker_output_dir):
        """SUPPLY_DOMAIN power kind with voltage reference on clock."""
        output_path, output_subdir = docker_output_dir
        noc = NocProject("e2e_supply")
        axi = noc.add_protocol("p", AXI(addr=32, data=64))
        noc.add_power_domain("MAIN", kind="ALWAYS_ON")
        noc.add_power_domain("PERIPH", kind="SUPPLY_DOMAIN")
        noc.add_voltage("VDD", value="0.81")
        clk = noc.add_clock("clk", freq="500MHz", voltage_ref="VDD", power_ref="MAIN")
        noc.add_initiator("i", protocol=axi, clock=clk, power_domain="MAIN")
        noc.add_target("t0", protocol=axi, clock=clk, base=0,          size="256M",
                       power_domain="MAIN")
        noc.add_target("t1", protocol=axi, clock=clk, base=0x10000000, size="256M",
                       power_domain="PERIPH")
        noc.connect_all()
        noc.set_export("Verilog")
        pdd_path = str(pdd_dir / "e2e_supply.pdd")
        noc.write_pdd(pdd_path)
        result = docker_runner(pdd_path, "e2e_supply_struct", output_subdir=output_subdir)
        assert result.returncode == 0, f"FlexNoC failed:\n{result.stderr[-2000:]}"
