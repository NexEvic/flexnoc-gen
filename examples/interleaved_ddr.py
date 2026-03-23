#!/usr/bin/env python3
"""Example: 2-way DDR interleaving with 1KB stripes.

Creates a NoC with one CPU initiator connected to two interleaved DDR
targets. The 2GB global address range is striped across DDR0 and DDR1
at 1KB granularity.

Global address map:
  0x0000_0000 - 0x0000_03FF  →  DDR0 (stripe 0)
  0x0000_0400 - 0x0000_07FF  →  DDR1 (stripe 1)
  0x0000_0800 - 0x0000_0BFF  →  DDR0 (stripe 2)
  ...
  Total: 2GB interleaved, 1GB per DDR target
"""

import sys, os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = REPO_ROOT / "work"
WORK_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(REPO_ROOT))

from flexnoc_dsl import NocProject, AXI

noc = NocProject("interleaved_noc")

# Protocol
axi = noc.add_protocol("AXI64_prot", AXI(addr=32, data=64, id=8))

# Clock
clk = noc.add_clock("sys_clk", freq="500MHz", port="clk", reset="rst_n")

# Initiator
noc.add_initiator("CPU", protocol=axi, clock=clk, pending_trans=8)

# Interleaved DDR targets: 2-way, 1KB stripe, 2GB total
noc.add_interleaved_targets(
    names=["DDR0", "DDR1"],
    protocol=axi,
    clock=clk,
    total_base=0,
    total_size="2G",
    stripe_size="1K",
    min_interleave_size=0,  # no response interleaving
)

noc.connect_all()
noc.set_export("Verilog", simulator="VCS")
output_path = str(WORK_DIR / "interleaved_ddr.pdd")
noc.write_pdd(output_path)

print(f"Generated {output_path}")
print(f"Export command: {noc.get_export_command(output_path)}")
