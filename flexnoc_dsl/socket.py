"""Socket, Initiator, Target, Flow, and Mapping definitions."""

import math
from dataclasses import dataclass, field
from typing import Optional


def _parse_size(size) -> int:
    """Parse size string like '256M' to bytes."""
    if isinstance(size, int):
        return size
    s = str(size).strip().upper()
    multipliers = {"T": 1 << 40, "G": 1 << 30, "M": 1 << 20, "K": 1 << 10}
    for suffix, mult in multipliers.items():
        if s.endswith(suffix):
            return int(float(s[: -len(suffix)]) * mult)
    return int(s, 0)  # support 0x prefix


def compute_interleave_mask(per_target_size: int, stripe_size: int,
                            num_targets: int) -> int:
    """Compute the striped mask for address interleaving.

    In FlexNoC, interleaved mappings use a mask with zero bits at the
    stripe boundary to select between targets. For example, 2-way
    interleave with 1KB stripes clears bit 10 in the mask.

    Args:
        per_target_size: Address space size per individual target (bytes).
        stripe_size: Granularity of interleaving (bytes, must be power of 2).
        num_targets: Number of interleaved targets (must be power of 2).

    Returns:
        The mask value for use in PDD mapping entries.
    """
    interleave_bits = int(math.log2(num_targets))
    stripe_bit = int(math.log2(stripe_size))
    # Aperture span covers per_target_size with interleave bits inserted
    aperture_span = per_target_size << interleave_bits
    base_mask = aperture_span - 1
    # Clear the interleave selection bits
    for i in range(interleave_bits):
        base_mask &= ~(1 << (stripe_bit + i))
    return base_mask


def create_interleaved_mappings(num_targets: int, stripe_size: int,
                                total_size: int, base_address: int = 0,
                                access: str = "ReadWrite") -> list:
    """Create mapping lists for interleaved targets.

    Returns a list of lists: one list of Mapping objects per target.
    Target 0 gets stripes where the selection bits are 0,
    Target 1 gets stripes where the selection bits are 1, etc.

    Args:
        num_targets: Number of interleaved targets (power of 2).
        stripe_size: Interleave granularity in bytes (power of 2).
        total_size: Total interleaved address range in bytes.
        base_address: Starting global address of the interleaved region.
        access: Access type for all mappings.

    Returns:
        List of (mask, [(global_addr, local_addr), ...]) per target.
    """
    per_target_size = total_size // num_targets
    interleave_bits = int(math.log2(num_targets))
    stripe_bit = int(math.log2(stripe_size))

    mask = compute_interleave_mask(per_target_size, stripe_size, num_targets)

    # Effective address bits per aperture (number of 1-bits in mask)
    effective_bits = bin(mask).count("1")
    effective_size = 1 << effective_bits
    # Number of apertures needed per target
    apertures_per_target = max(1, per_target_size // effective_size)

    # Aperture span in global address space
    aperture_span = 1 << (mask.bit_length())

    all_target_mappings = []
    for targ_idx in range(num_targets):
        mappings = []
        for ap_idx in range(apertures_per_target):
            global_addr = (base_address
                           + ap_idx * aperture_span
                           + (targ_idx << stripe_bit))
            local_addr = ap_idx * effective_size
            mappings.append(Mapping(
                name=str(len(mappings)),
                global_address=global_addr,
                local_address=local_addr,
                mask=mask,
                access=access,
            ))
        all_target_mappings.append(mappings)
    return all_target_mappings


@dataclass
class Mapping:
    """Address mapping within a flow."""
    name: str
    global_address: int = 0
    local_address: int = 0
    mask: int = 0  # computed from size if not set
    size: int = 0  # convenience; converted to mask
    access: str = "ReadWrite"  # ReadWrite, Read, Write, None
    modes: dict = field(default_factory=dict)  # {ModeFlag: bool}
    comment: str = ""

    def effective_mask(self) -> int:
        if self.mask:
            return self.mask
        if self.size:
            return self.size - 1
        return 0


@dataclass
class Flow:
    """A traffic flow within an initiator or target."""
    name: str = "0"
    mappings: list = field(default_factory=list)
    default_error_target: str = ""

    def add_mapping(self, name: str = "", base: int = 0, size=0,
                    local_address: int = 0, access: str = "ReadWrite",
                    mode: dict = None, comment: str = "") -> "Mapping":
        parsed_size = _parse_size(size) if size else 0
        idx = len(self.mappings)
        m = Mapping(
            name=name or str(idx),
            global_address=base,
            local_address=local_address,
            size=parsed_size,
            access=access,
            modes=mode or {},
            comment=comment,
        )
        self.mappings.append(m)
        return m


@dataclass
class Initiator:
    """An initiator socket."""
    name: str
    protocol_ref: str = ""  # name of the protocol object
    clock_ref: str = ""  # clock domain name
    clock: object = None  # ClockDomain
    pending_trans: int = 4
    pending_ids: int = 1
    use_soft_lock: bool = False
    use_press: bool = False  # QoS pressure signal
    min_interleave_size: int = -1  # -1=omit, 0=no response interleaving
    flows: list = field(default_factory=list)
    user_mapping: dict = field(default_factory=dict)
    clock_gating: str = ""  # "", "#Common", or custom value
    comment: str = ""
    power_domain: str = ""  # ref to power domain name
    conversion: dict = field(default_factory=dict)  # protocol conversion config

    def flow(self, idx: int = 0) -> Flow:
        while len(self.flows) <= idx:
            self.flows.append(Flow(name=str(len(self.flows))))
        return self.flows[idx]

    def _ensure_default_flow(self, total_mask: int):
        if not self.flows:
            f = Flow(name="0")
            f.add_mapping("0", base=0, size=0)
            f.mappings[0].mask = total_mask
            self.flows.append(f)


@dataclass
class Target:
    """A target socket."""
    name: str
    protocol_ref: str = ""
    clock_ref: str = ""
    clock: object = None
    base_address: int = 0
    size: int = 0  # bytes
    pending_trans: int = 16
    seq_id_width: int = 0  # wSeqId, defaults to protocol id_width
    use_soft_lock: bool = False
    min_interleave_size: int = -1  # -1=omit, 0=no response interleaving
    flows: list = field(default_factory=list)
    user_mapping: dict = field(default_factory=dict)
    clock_gating: str = ""  # "", "#Common", or custom value
    comment: str = ""
    power_domain: str = ""  # ref to power domain name
    seq_id_allocation: str = ""  # "", "DYNAMIC", "STATIC"
    conversion: dict = field(default_factory=dict)  # protocol conversion config
    specials_mapping: dict = field(default_factory=dict)  # custom specials override

    def flow(self, idx: int = 0) -> Flow:
        while len(self.flows) <= idx:
            self.flows.append(Flow(name=str(len(self.flows))))
        return self.flows[idx]

    def _ensure_default_flow(self):
        if not self.flows:
            f = Flow(name="0")
            f.add_mapping("0", base=self.base_address, size=0)
            f.mappings[0].mask = self.size - 1 if self.size else 0
            self.flows.append(f)
