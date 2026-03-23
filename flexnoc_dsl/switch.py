"""Switch and link definitions for architecture layer."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DtpSwitch:
    """A datapath switch in the architecture."""
    name: str
    clock_ref: str = ""  # arch-scope clock reference
    domain_crossings: list = field(default_factory=list)
    n_byte_per_word: int = 8
    header_penalty: str = "NONE"
    input_pipes: dict = field(default_factory=dict)   # {crossing_ref: num_stages}
    output_pipes: dict = field(default_factory=dict)  # {crossing_ref: num_stages}


@dataclass
class DtpLink:
    """A datapath link (FIFO or rate adapter) for CDC or buffering."""
    name: str
    clock_ref: str = ""
    buffering: str = "FIFO"  # FIFO or RATE_ADAPTER
    n_byte: int = 32
    n_packet: int = 4
    n_byte_per_word: int = 8
    header_penalty: str = "NONE"
    has_module: bool = True  # False for virtual links like adaptrsp


@dataclass
class SrvSwitch:
    """A service switch for NOC register access."""
    name: str
    clock_ref: str = ""
    domain_crossings: list = field(default_factory=list)
    n_byte_per_word: int = 1
    header_penalty: str = "AUTO"


@dataclass
class ObsSwitch:
    """An observation switch for error reporting paths."""
    name: str
    clock_ref: str = ""
    domain_crossings: list = field(default_factory=list)
    n_byte_per_word: int = 0
    header_penalty: str = "AUTO"


@dataclass
class Route:
    """A routing path from initiator flow to target flow."""
    init_ref: str  # e.g., "init_0/I/0"
    targ_ref: str  # e.g., "targ_0/T/0"
    request_path: list = field(default_factory=list)  # list of switch/link names
    response_path: list = field(default_factory=list)
