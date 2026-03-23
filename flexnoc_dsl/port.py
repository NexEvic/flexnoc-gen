"""Port definitions for FlexNoC DSL."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Port:
    """Base port definition."""
    name: str
    port_type: str  # Clock, ResetN, TestMode, Mode, User
    clock_ref: str = ""  # reference to clock, "None" for async
    width: int = 1
    direction: str = ""  # Input, Output (for User type)
    default_val: Optional[int] = None  # simulation default
    comment: str = ""
    ip_power_domain: str = ""
    deassertion_clock: str = ""  # for ResetN
    mode_port_values: dict = field(default_factory=dict)  # for ModeFlag


@dataclass
class ModeFlag:
    """A mode flag (like Boot) that controls mapping selection."""
    name: str
    port_name: str  # which port drives this flag
    active_value: int = 1


@dataclass
class UserFlag:
    """A user-defined flag (e.g. secure, privileged, debug) for userMapping."""
    name: str  # e.g. "0_debug", "1_privileged", "2_secureN"


@dataclass
class PowerDomain:
    """A power domain object (e.g. ALWAYS_ON, SUPPLY)."""
    name: str
    kind: str = "ALWAYS_ON"  # ALWAYS_ON, SUPPLY, SWITCHABLE
    comment: str = ""
    activity_zones: list = field(default_factory=list)  # list of str names


@dataclass
class Voltage:
    """A voltage domain object."""
    name: str
    value: str = "0.81"
    comment: str = ""


@dataclass
class Observer:
    """An error observer that watches targets."""
    name: str
    clock: object = None  # ClockDomain
    clock_ref: str = ""
    watched_targets: list = field(default_factory=list)
    interrupt_port: str = ""
    debug_output: str = "None"
    error_loggers: dict = field(default_factory=dict)
