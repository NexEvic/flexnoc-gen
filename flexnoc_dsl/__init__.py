"""FlexNoC DSL — Python API for generating FlexNoC PDD files.

Usage:
    from flexnoc_dsl import NocProject, AXI, APB, OCP

    noc = NocProject("my_noc")
    axi = noc.add_protocol("AXI_prot", AXI(addr=32, data=64, id=4))
    clk = noc.add_clock("clk_domain", freq="500MHz", port="clk", reset="rst_n")
    noc.add_initiator("init_0", protocol=axi, clock=clk)
    noc.add_target("targ_0", protocol=axi, clock=clk, base=0x0, size="256M")
    noc.connect_all()
    noc.set_export("Verilog", simulator="VCS")
    noc.write_pdd("output.pdd")
"""

from .project import NocProject
from .protocol import AXI, APB, OCP, AHB, AXI_Lite, ACE_Lite, Protocol
from .clock import ClockDomain
from .socket import Initiator, Target, Flow, Mapping, compute_interleave_mask, create_interleaved_mappings
from .port import Port, ModeFlag, Observer, UserFlag, PowerDomain, Voltage
from .architecture import Architecture
from .switch import DtpSwitch, DtpLink, SrvSwitch, ObsSwitch, Route

__all__ = [
    "NocProject", "AXI", "APB", "OCP", "Protocol", "ClockDomain",
    "Initiator", "Target", "Flow", "Mapping",
    "compute_interleave_mask", "create_interleaved_mappings",
    "Port", "ModeFlag", "Observer", "UserFlag",
    "Architecture", "DtpSwitch", "DtpLink", "SrvSwitch", "ObsSwitch", "Route",
]
