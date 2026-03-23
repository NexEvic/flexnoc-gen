"""Protocol definitions for FlexNoC DSL."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Protocol:
    """Base protocol configuration."""
    name: str = ""
    protocol_type: str = ""  # AXI, APB, OCP_Lite, SERVICE, LLI
    addr_width: int = 32
    data_width: int = 64
    id_width: int = 4
    en_read: bool = True
    en_write: bool = True
    use_fixed: bool = False
    extra: dict = field(default_factory=dict)


def AXI(addr: int = 32, data: int = 64, id: int = 4,
        read: bool = True, write: bool = True, fixed: bool = False,
        **kwargs) -> Protocol:
    """Create an AXI protocol definition."""
    return Protocol(
        protocol_type="AXI", addr_width=addr, data_width=data,
        id_width=id, en_read=read, en_write=write, use_fixed=fixed,
        extra=kwargs,
    )


def APB(addr: int = 32, data: int = 32, **kwargs) -> Protocol:
    """Create an APB protocol definition."""
    return Protocol(
        protocol_type="APB", addr_width=addr, data_width=data,
        id_width=0, en_read=True, en_write=True, extra=kwargs,
    )


def OCP(addr: int = 32, data: int = 64, id: int = 4, **kwargs) -> Protocol:
    """Create an OCP_Lite protocol definition."""
    return Protocol(
        protocol_type="OCP_Lite", addr_width=addr, data_width=data,
        id_width=id, en_read=True, en_write=True, extra=kwargs,
    )


def AHB(addr: int = 32, data: int = 32, **kwargs) -> Protocol:
    """Create an AHB protocol definition."""
    return Protocol(
        protocol_type="AHB", addr_width=addr, data_width=data,
        id_width=0, en_read=True, en_write=True, extra=kwargs,
    )


def AXI_Lite(addr: int = 32, data: int = 32, **kwargs) -> Protocol:
    """Create an AXI-Lite protocol definition (subset of AXI, no bursts/ID)."""
    return Protocol(
        protocol_type="AXI", addr_width=addr, data_width=data,
        id_width=0, en_read=True, en_write=True,
        use_fixed=False, extra=kwargs,
    )


def ACE_Lite(addr: int = 32, data: int = 64, id: int = 4,
             use_barrier: bool = False, dvm: bool = False,
             early_wr_rsp: bool = False, **kwargs) -> Protocol:
    """Create an ACE-Lite protocol (AXI coherency extension).

    Note: ACE-Lite features (useBarrier, DVM) require FlexNoC versions
    that support ACE coherency. In FlexNoC 5.3.0, these are emitted
    at socket/initiator level rather than protocol level.

    Args:
        use_barrier: Enable barrier transactions.
        dvm: Enable DVM (Distributed Virtual Memory) support.
        early_wr_rsp: Enable early write response.
    """
    return Protocol(
        protocol_type="AXI", addr_width=addr, data_width=data,
        id_width=id, en_read=True, en_write=True, extra=kwargs,
    )
