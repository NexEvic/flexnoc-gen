#!/usr/bin/env python3
"""Simple 2x2 AXI crossbar example — equivalent to axi_xbar_2x2_v3.pdd."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = REPO_ROOT / "work"
WORK_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(REPO_ROOT))

from flexnoc_dsl import NocProject, AXI

# Create project
noc = NocProject("xbar_2x2")

# Protocol
axi = noc.add_protocol("AXI_prot", AXI(addr=32, data=64, id=4))

# Clock domain
clk = noc.add_clock("clk_domain", freq="500MHz", port="clk", reset="rst_n")

# Initiators
noc.add_initiator("init_0", protocol=axi, clock=clk, pending_trans=4, pending_ids=1)
noc.add_initiator("init_1", protocol=axi, clock=clk, pending_trans=4, pending_ids=1)

# Targets
noc.add_target("targ_0", protocol=axi, clock=clk,
               base=0x00000000, size="256M", pending_trans=16)
noc.add_target("targ_1", protocol=axi, clock=clk,
               base=0x10000000, size="256M", pending_trans=16)

# Connectivity (full mesh)
noc.connect_all()

# Export
noc.set_export("Verilog", simulator="VCS")

# Write PDD
output_path = str(WORK_DIR / "xbar_2x2_generated.pdd")
noc.write_pdd(output_path)
print(f"PDD written to: {output_path}")
print(f"Export command: {noc.get_export_command(output_path)}")
