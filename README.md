# flexnoc-gen

A Python DSL for generating [FlexNoC](https://arteris.com/flexnoc/) PDD (Project Design Description) files programmatically.

> Target FlexNoC: 5.3.0 | Python 3.8+

## Overview

`flexnoc-gen` lets you describe a NoC at the specification level — protocols, clocks, sockets, and connections — and automatically derives the architecture and structure layers. FlexNoC then exports synthesizable Verilog RTL.

```python
from flexnoc_dsl import NocProject, AXI

noc = NocProject("xbar_2x2")
axi = noc.add_protocol("AXI_prot", AXI(addr=32, data=64, id=4))
clk = noc.add_clock("clk_domain", freq="500MHz")

noc.add_initiator("init_0", protocol=axi, clock=clk)
noc.add_initiator("init_1", protocol=axi, clock=clk)
noc.add_target("targ_0", protocol=axi, clock=clk, base=0x0, size="256M")
noc.add_target("targ_1", protocol=axi, clock=clk, base=0x10000000, size="256M")

noc.connect_all()
noc.set_export("Verilog", simulator="VCS")
noc.write_pdd("xbar_2x2.pdd")
```

The 10-line script above generates a 458-line PDD which FlexNoC compiles into 31,813 lines of Verilog RTL ✅

## Features

- **6 protocols**: AXI, APB, OCP, AHB, AXI-Lite, ACE-Lite
- **Multi-clock CDC**: mixed-frequency clock domains
- **Address interleaving**: stripe-based interleaved DDR targets
- **Full port control**: UserPort, ModeFlag, UserFlag, Observer
- **Power domains**: PowerDomain, Voltage, ActivityZone, IPpowerDomain
- **Architecture control**: auto-derived crossbar + manual override (Pipeline, arbitration, QoS)
- **Multi-export**: simultaneous Verilog + XML + FV output
- **AXI4/AXI5 extensions**: user signals, QoS, error codes

## Installation

```bash
git clone https://github.com/agent123123123/flexnoc-gen.git
cd flexnoc-gen

# No pip install needed — import directly
# If FlexNoC bashrc was sourced, clean up first:
unset PYTHONHOME && unset PYTHONPATH
```

## Usage

```bash
cd flexnoc-gen
python examples/simple_2x2.py    # generates xbar_2x2.pdd
```

Run with FlexNoC (Docker):

```bash
docker run --rm -v $(pwd):/work flexnoc:5.3.0-standalone \
  /opt/flexnoc/bin/flexnoc -pdd /work/xbar_2x2.pdd -d False -o /work/output
```

## Project Structure

```
flexnoc_dsl/          # DSL core (8 modules)
  __init__.py
  protocol.py         # AXI/APB/OCP/AHB/AXI_Lite/ACE_Lite factories
  clock.py            # ClockDomain, freq parsing
  socket.py           # Initiator/Target/Flow/Mapping, interleave
  port.py             # Port/ModeFlag/UserFlag/Observer
  power.py            # PowerDomain/Voltage/ActivityZone
  project.py          # NocProject — main API (~450 lines)
  pdd_writer.py       # PDD XML generator (~1100 lines)
  architecture.py     # auto_derive + manual topology
  switch.py           # DtpSwitch/DtpLink/SrvSwitch/ObsSwitch/Route

examples/             # Example scripts
  simple_2x2.py
  interleaved_ddr.py
  test_p0_features.py
  test_p1_features.py
  test_p2_features.py

tests/                # pytest suite (99 tests)
  conftest.py
  test_protocol.py
  test_clock.py
  test_socket.py
  test_flow_mapping.py
  test_port.py
  test_power.py
  test_architecture.py
  test_export.py
  test_qos.py
  test_connectivity.py
  test_mixed_protocol.py
  test_e2e_docker.py   # requires Docker

docs/                 # Full documentation
  index.md
  api/
  guides/
```

## Running Tests

```bash
# Unit tests (no Docker required)
cd flexnoc-gen
python -m pytest tests/ -v -m "not docker"

# E2E Docker tests
python -m pytest tests/test_e2e_docker.py -v
```

## Documentation

See [`docs/index.md`](docs/index.md) for the full documentation index.

| Doc | Content |
|-----|---------|
| [docs/api/protocol.md](docs/api/protocol.md) | Protocol APIs |
| [docs/api/clock.md](docs/api/clock.md) | Clock domains & CDC |
| [docs/api/socket.md](docs/api/socket.md) | Sockets & interleaving |
| [docs/api/port.md](docs/api/port.md) | Ports & flags |
| [docs/api/power.md](docs/api/power.md) | Power domains |
| [docs/api/architecture.md](docs/api/architecture.md) | Topology control |
| [docs/api/export.md](docs/api/export.md) | Export options |
| [docs/api/project.md](docs/api/project.md) | NocProject reference |
| [docs/guides/docker-e2e.md](docs/guides/docker-e2e.md) | Docker E2E workflow |
| [docs/guides/feature-compatibility.md](docs/guides/feature-compatibility.md) | Feature constraints |

## License

Internal tool. See [Arteris FlexNoC](https://arteris.com) for FlexNoC licensing.
