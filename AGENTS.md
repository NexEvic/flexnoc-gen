# AGENTS.md — flexnoc-gen

> Python DSL for generating FlexNoC PDD (Project Design Description) files programmatically.
> Target: FlexNoC 5.3.0 | Python 3.8+

---

## Project Structure

```
flexnoc_dsl/          # Core DSL (8 modules)
  __init__.py         # Public API exports
  protocol.py         # AXI/APB/OCP/AHB/AXI_Lite/ACE_Lite factories
  clock.py            # ClockDomain, _parse_freq helper
  socket.py           # Initiator/Target/Flow/Mapping, interleave helpers
  port.py             # Port/ModeFlag/UserFlag/Observer/PowerDomain/Voltage
  power.py            # Power domain definitions
  project.py          # NocProject — main API (~409 lines)
  pdd_writer.py       # PDD XML generator (~1087 lines)
  architecture.py     # auto_derive + manual topology
  switch.py           # DtpSwitch/DtpLink/SrvSwitch/ObsSwitch/Route

tests/                # pytest suite (99 tests)
  conftest.py         # Shared fixtures: pdd_dir, basic_noc, simple_2x2, docker_runner
  test_protocol.py    # Protocol creation and PDD entries
  test_clock.py       # Clock domains and frequency parsing
  test_socket.py      # Initiator/Target/Flow/Mapping
  test_port.py        # Port and flag types
  test_power.py       # Power domains
  test_architecture.py # Topology auto-derive
  test_flow_mapping.py # Address mapping and interleaving
  test_qos.py         # QoS and urgency settings
  test_connectivity.py # connect_all and explicit connections
  test_mixed_protocol.py # Multi-protocol NoCs
  test_export.py      # Export options (Verilog/XML/FV)
  test_e2e_docker.py  # Docker E2E (requires FlexNoC image, marked @docker)

examples/
  simple_2x2.py       # Minimal 2x2 crossbar
  interleaved_ddr.py  # Address interleaving
  test_p0_features.py # P0 feature examples
  test_p1_features.py # P1 feature examples
  test_p2_features.py # P2 feature examples

docs/cases/           # Debug case library for known FlexNoC/PDD failures
scripts/
  diagnose_pdd_routes.py # PDD connectivity/route consistency checker
```

---

## Build / Lint / Test Commands

### Running Tests

```bash
# All unit tests (skip Docker E2E)
python -m pytest tests/ -v -m "not docker"

# E2E Docker tests (requires flexnoc:5.3.0-standalone image)
python -m pytest tests/test_e2e_docker.py -v

# Single test file
python -m pytest tests/test_protocol.py -v

# Single test
python -m pytest tests/test_protocol.py::TestAXIProtocol::test_axi_default -v

# Single test with stdout
python -m pytest tests/test_protocol.py::TestAXIProtocol::test_axi_default -v -s

# Run tests matching a pattern
python -m pytest tests/ -v -k "test_axi"

# Run with coverage
python -m pytest tests/ -v --cov=flexnoc_dsl --cov-report=term-missing
```

### Generating PDD Output

```bash
# Run an example script
python examples/simple_2x2.py    # generates xbar_2x2.pdd in work/

# Run FlexNoC export in Docker (requires PDD file)
docker run --rm -v $(pwd):/work flexnoc:5.3.0-standalone \
  /opt/flexnoc/bin/flexnoc -pdd /work/xbar_2x2.pdd -d False -o /work/output
```

### Required PDD Debug Before Blocking

When `exportVerilog` reports `Element ... is not stable`, `A Node has not been placed on any route`, or `Incompatible settings ... datapathRoute`, do not stop after the first failed export. First check the case library and run:

```bash
python3 scripts/diagnose_pdd_routes.py <generated.pdd>
```

Exit code 1 means the script found a PDD consistency issue; keep the printed
report as diagnostic evidence.

If the script reports stale routes or unused architecture nodes, classify the issue as a `flexnoc-gen` PDD generation problem, not as a FlexNoC license/tool-environment blocker. See `docs/cases/001_sparse_connectivity_stale_routes.md`.

---

## Code Style Guidelines

### Imports

- **Relative imports** within `flexnoc_dsl/`:
  ```python
  from .protocol import Protocol
  from .clock import ClockDomain, _parse_freq
  from .socket import Initiator, Target, Flow, Mapping, _parse_size, create_interleaved_mappings
  ```
- Use `from xml.etree.ElementTree import Element, SubElement, tostring` (qualified names acceptable for XML)
- No wildcard imports (`from module import *`) except in `__all__` and `__init__.py`

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Classes | PascalCase | `class NocProject`, `class ClockDomain` |
| Dataclasses | PascalCase | `@dataclass class DtpSwitch` |
| Functions/methods | snake_case | `def _parse_freq(...)`, `def add_protocol(...)` |
| Private helpers | snake_case with underscore prefix | `def _parse_size(...)`, `_to_names(...)` |
| Variables | snake_case | `self._protocols`, `n_byte`, `arch_clock_ref` |
| Constants | SCREAMING_SNAKE | `PDD_VERSION = "5.3.0r186A"` |
| Module-level "private" | leading underscore | `_parse_freq`, `_get_data_width` |

### Type Hints

- Use Python 3.8+ type hints (`List`, `Dict` from typing or built-in `list`/`dict`)
- Dataclass fields: annotate with types directly
  ```python
  @dataclass
  class Protocol:
      name: str = ""
      protocol_type: str = ""
      addr_width: int = 32
      extra: dict = field(default_factory=dict)
  ```
- Method return types: annotate when non-trivial
  ```python
  def parse_pdd(path: str) -> ET.Element: ...
  def get_entry_value(element: ET.Element, key: str) -> str: ...
  ```

### Docstrings

Use Google-style docstrings with `Args:`, `Returns:` sections:

```python
def compute_interleave_mask(per_target_size: int, stripe_size: int,
                            num_targets: int) -> int:
    """Compute the striped mask for address interleaving.

    In FlexNoC, interleaved mappings use a mask with zero bits at the
    stripe boundary to select between targets.

    Args:
        per_target_size: Address space size per individual target (bytes).
        stripe_size: Granularity of interleaving (bytes, must be power of 2).
        num_targets: Number of interleaved targets (must be power of 2).

    Returns:
        The mask value for use in PDD mapping entries.
    """
```

### Dataclass Usage

Use `@dataclass` for all data structure classes (Protocol, ClockDomain, Port, Switch, Route, etc.):

```python
@dataclass
class DtpSwitch:
    name: str
    clock_ref: str = ""
    domain_crossings: list = field(default_factory=dict)
    n_byte_per_word: int = 8
```

### Error Handling

- **Type checking**: Use `isinstance()` before operations
  ```python
  if isinstance(freq, (int, float)):
      return float(freq)
  s = str(freq).strip().upper()
  ```
- **None checks**: Use `if entry is not None:` pattern (avoid `if not entry` for None)
- **Key lookups**: Use `dict.get()` with defaults when keys may be absent
  ```python
  clock = clock_map.get(clk_name)
  if not clock:
      continue
  ```
- **Path construction**: Use `pathlib.Path` for file paths; `os.path` is also acceptable
- **No raise statements** in DSL model code — validation errors should produce clear log messages

### XML Generation (pdd_writer.py)

- Use `xml.etree.ElementTree` with `SubElement` for building PDD XML
- Set attributes via `.set()` method:
  ```python
  obj = SubElement(root, "object")
  obj.set("kind", "protocol")
  obj.set("name", name)
  ```
- Use `tostring(..., encoding="unicode")` + `minidom.toprettyxml()` for pretty printing
- Strip XML declaration with `lines[1:]` if first line starts with `<?xml`

### File Organization

- One class per module preferred for `flexnoc_dsl/` core modules
- Helper functions (private) go in the same module as their primary user
- `_parse_*` and `_get_*` are private helpers — do not export from `__init__.py`

### Test Conventions

- Use pytest fixtures from `conftest.py`: `pdd_dir`, `basic_noc`, `simple_2x2`
- Helper functions in `conftest.py`: `parse_pdd()`, `find_objects()`, `find_entry()`, `get_entry_value()`, `assert_pdd_valid()`
- Test class naming: `Test<FeatureName>` (e.g., `TestAXIProtocol`, `TestClockBasic`)
- Test method naming: `test_<description>` (snake_case)
- Use `@pytest.mark.parametrize` for multiple input variants
- Mark Docker-dependent tests with `@pytest.mark.docker`
- PDD validation helper: `assert_pdd_valid(path)` checks for `project`, `protocol`, `switchBasedArchitecture`, `switchBasedStructure`, `specification` objects

### Module `__init__.py` Exports

Only export public API — do not expose private helpers:

```python
__all__ = [
    "NocProject", "AXI", "APB", "OCP", "Protocol", "ClockDomain",
    "Initiator", "Target", "Flow", "Mapping",
    "compute_interleave_mask", "create_interleaved_mappings",
    "Port", "ModeFlag", "Observer", "UserFlag",
    "Architecture", "DtpSwitch", "DtpLink", "SrvSwitch", "ObsSwitch", "Route",
]
```

---

## FlexNoC DSL Usage Patterns

### Minimal NoC Construction

```python
from flexnoc_dsl import NocProject, AXI

noc = NocProject("my_noc")
axi = noc.add_protocol("AXI_prot", AXI(addr=32, data=64, id=4))
clk = noc.add_clock("clk", freq="500MHz", port="clk", reset="rst_n")
noc.add_initiator("init_0", protocol=axi, clock=clk)
noc.add_target("targ_0", protocol=axi, clock=clk, base=0x0, size="256M")
noc.connect_all()
noc.set_export("Verilog", simulator="VCS")
noc.write_pdd("output.pdd")
```

### Protocol Factory Functions

Protocols are created via factory functions (not direct class instantiation):
- `AXI(addr=32, data=64, id=4)` → `Protocol(protocol_type="AXI", ...)`
- `APB(addr=32, data=32)` → `Protocol(protocol_type="APB", ...)`
- `OCP(...)`, `AHB(...)`, `AXI_Lite(...)`, `ACE_Lite(...)`

### Clock Frequency Parsing

`_parse_freq()` handles: `100MHz`, `1GHz`, `250MHz`, `33MHz` → float Hz

### Size Parsing

`_parse_size()` handles: `"256M"`, `"1G"`, `"64K"`, `0x1000` → int bytes

### Sparse Connectivity Rule

For sparse connectivity, architecture and specification must agree:

- A `datapathRoute` entry may exist only when the matching specification connectivity entry is `True`.
- A disconnected pair such as `init/I/0 -> target/T/0 = False` must not remain in architecture `datapathRoute`.
- Auto-derived `dtpSwitch` or `dtpLink` nodes with zero route usage must be pruned together with their structure shadows.
- If a generated PDD violates these rules, regenerate or patch the generator; do not mark the FlexNoC export as an external tool blocker.
