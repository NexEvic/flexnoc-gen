#!/usr/bin/env python3
"""E2E test for P1 features: Power/Voltage, Export options, useErrorCodes,
seqIdAllocation, comment, readPermissions/writePermissions, voltage ref."""

import sys, os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = REPO_ROOT / "work"
WORK_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(REPO_ROOT))

from flexnoc_dsl import NocProject, AXI

def main():
    noc = NocProject("p1_test")

    # Protocol
    axi = noc.add_protocol("AXI_p", AXI(addr=32, data=64, id=4))

    # Voltage object
    v = noc.add_voltage("voltage", value="0.81", comment="#TBD by designer")

    # Power domains
    pd_always = noc.add_power_domain("INTERCO_dom", kind="ALWAYS_ON",
                                      comment="#kind TBD by designer")
    pd_noc = noc.add_power_domain("NoC_dom", kind="ALWAYS_ON",
                                   comment="#NoC power domain")

    # Clock with voltage reference and power domain reference
    clk = noc.add_clock("clk_domain", freq="500MHz", port="clk",
                        reset="rst_n", voltage_ref="voltage",
                        comment="#Main clock domain",
                        power_ref="NoC_dom")

    # useErrorCodes
    noc.set_use_error_codes(True)

    # Initiators with power domain and comment
    init0 = noc.add_initiator("cpu_init", protocol=axi, clock=clk,
                               clock_gating="#Common",
                               comment="CPU initiator port",
                               power_domain="NoC_dom")

    # Targets with seqIdAllocation and power domain
    targ0 = noc.add_target("mem_targ", protocol=axi, clock=clk,
                            base=0x0, size="256M",
                            comment="Main memory target",
                            power_domain="NoC_dom",
                            seq_id_allocation="DYNAMIC")

    targ1 = noc.add_target("periph_targ", protocol=axi, clock=clk,
                            base=0x10000000, size="256M",
                            power_domain="INTERCO_dom")

    noc.connect_all()
    noc.set_arbiter_mode("ROUND_ROBIN")

    # Multiple export options
    noc.set_export("Verilog", simulator="VCS", name="exports.Vlog")

    noc.add_export("Verilog", simulator="ModelSim",
                   name="exports.synthesisDC",
                   synthesis_tool="DC",
                   files="SingleFile",
                   customer_cells={
                       "GaterCell": "/path/to/G.v",
                       "SynchronizerCell": "/path/to/S.v",
                   })

    _pdd_path = str(WORK_DIR / "test_p1_features.pdd")
    noc.write_pdd(_pdd_path)

    # ---- Self-validation ----
    with open(_pdd_path) as f:
        content = f.read()

    checks = [
        ('voltage object', 'kind="voltage"' in content),
        ('voltage value', 'value="0.81"' in content),
        ('power ALWAYS_ON', 'kind="power"' in content and 'ALWAYS_ON' in content),
        ('power NoC_dom', 'NoC_dom' in content),
        ('clockRegime voltage ref', '(specification:voltage)' in content),
        ('clockRegime comment', '#Main clock domain' in content),
        ('useErrorCodes', 'useErrorCodes' in content and 'True' in content),
        ('socket comment', 'CPU initiator port' in content),
        ('IPpowerDomain', 'IPpowerDomain' in content),
        ('seqIdAllocation', 'seqIdAllocation' in content and 'DYNAMIC' in content),
        ('readPermissions', 'readPermissions' in content),
        ('writePermissions', 'writePermissions' in content),
        ('synthesisTool DC', 'synthesisTool' in content and 'DC' in content),
        ('customerCells', 'customerCells' in content),
        ('GaterCell path', 'G.v' in content),
        ('files SingleFile', 'SingleFile' in content),
        ('multiple exports', content.count('kind="exportOption"') >= 2),
    ]

    print("P1 Feature Self-checks:")
    all_pass = True
    for name, result in checks:
        status = "PASS" if result else "FAIL"
        if not result:
            all_pass = False
        print(f"  {status}: {name}")

    if all_pass:
        print(f"\nAll {len(checks)} checks passed!")
    else:
        print(f"\nSome checks FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()
