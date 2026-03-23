#!/usr/bin/env python3
"""Test script for P2 features: H2 usePress, F4 specials, D7 conversion,
A4 AXI4/5, A5 ACE-Lite, A6 AHB, A7 AXI-Lite."""

import sys, os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = REPO_ROOT / "work"
WORK_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(REPO_ROOT))

from flexnoc_dsl import (NocProject, AXI, APB, AHB, AXI_Lite, ACE_Lite,
                          PowerDomain, Voltage)

PDD = str(WORK_DIR / "test_p2_features.pdd")

noc = NocProject("p2_test")

# Protocols
axi = noc.add_protocol("AXI_prot", AXI(addr=32, data=64, id=4))
axi_ext = noc.add_protocol("AXI_ext", AXI(addr=32, data=64, id=8,
                                           wReqUser=1, wRspUser=1))
ahb = noc.add_protocol("AHB_prot", AHB(addr=32, data=32))
axil = noc.add_protocol("AXIL_prot", AXI_Lite(addr=32, data=32))
ace = noc.add_protocol("ACE_prot", ACE_Lite(addr=32, data=64, id=4))

# Clock
clk = noc.add_clock("clk_dom", freq="500MHz")

# -- H2: usePress on initiator --
init0 = noc.add_initiator("cpu_init", protocol=axi, clock=clk,
                          use_press=True)

# -- A4: AXI4/5 extended protocol --
init1 = noc.add_initiator("ext_init", protocol=axi_ext, clock=clk)

# -- A5: ACE-Lite --
init2 = noc.add_initiator("ace_init", protocol=ace, clock=clk)

# -- D7: conversion on target (empty) --
targ0 = noc.add_target("sram_targ", protocol=axi, clock=clk,
                        base=0x0, size="256M")

# -- F4: custom specials mapping --
targ1 = noc.add_target("custom_targ", protocol=axi, clock=clk,
                        base=0x10000000, size="256M",
                        specials_mapping={
                            "ARCache": {"CONST_1": "#0,1,2,3"},
                            "AWCache": {"CONST_1": "#0,1,2,3"},
                            "Prot": {"CONST_1": "#0,1,2"},
                        })

# -- A6: AHB target --
targ2 = noc.add_target("ahb_targ", protocol=ahb, clock=clk,
                        base=0x20000000, size="256M",
                        pending_trans=1)

# -- A7: AXI-Lite target --
targ3 = noc.add_target("axil_targ", protocol=axil, clock=clk,
                        base=0x30000000, size="256M")

noc.connect_all()
noc.set_export("Verilog", simulator="VCS")
noc.write_pdd(PDD)

# Self-checks
with open(PDD) as f:
    pdd = f.read()

checks = [
    ("H2: usePress", '<entry key="usePress" value="True"/>' in pdd),
    ("D7: conversion (empty)", '<entry key="conversion"/>' in pdd),
    ("F4: custom CONST_1 ARCache",
     'key="CONST_1" value="#0,1,2,3"' in pdd),
    ("A4: wReqUser", '<entry key="wReqUser" value="1"/>' in pdd),
    ("A4: wRspUser", '<entry key="wRspUser" value="1"/>' in pdd),
    ("A5: ACE-Lite protocol", 'name="ACE_prot"' in pdd),
    ("A6: AHB protocol", 'value="AHB"' in pdd),
    ("A7: AXI-Lite no wId", 'name="AXIL_prot"' in pdd),
]

passed = 0
for name, ok in checks:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {name}")
    if ok:
        passed += 1

print(f"\n{passed}/{len(checks)} checks passed")
if passed < len(checks):
    sys.exit(1)
print(f"\nPDD written to {PDD}")
