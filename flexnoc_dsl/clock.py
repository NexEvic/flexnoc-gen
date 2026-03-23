"""Clock domain definitions for FlexNoC DSL."""

from dataclasses import dataclass, field
from typing import Optional


def _parse_freq(freq) -> float:
    """Parse frequency string like '500MHz' to float Hz."""
    if isinstance(freq, (int, float)):
        return float(freq)
    s = str(freq).strip().upper()
    multipliers = {"GHZ": 1e9, "MHZ": 1e6, "KHZ": 1e3, "HZ": 1.0}
    for suffix, mult in multipliers.items():
        if s.endswith(suffix):
            return float(s[: -len(suffix)]) * mult
    return float(s)


@dataclass
class ClockDomain:
    """A clock regime with its manager and clock output."""
    name: str
    frequency: float  # Hz
    port_name: str  # clock port name in specification
    reset_name: str  # reset port name in specification
    test_mode: str = "Tm"  # test mode port name
    manager_name: str = "Cm"
    clock_name: str = "Clk"
    clock_type: str = "Root"  # Root or Gated
    voltage_ref: str = ""  # reference to a voltage object name
    comment: str = ""
    power_ref: str = ""  # reference to power domain/activity zone, e.g. "NoC_dom/NoC_zone"

    @property
    def clock_ref(self) -> str:
        """Return the full clock path reference for use in entries."""
        return f"(specification:{self.name}/{self.manager_name}/{self.clock_name})"

    @property
    def arch_clock_ref(self) -> str:
        """Return clock ref in architecture scope."""
        return f"(switchBasedArchitecture:{self.name}/{self.manager_name}/{self.clock_name})"
