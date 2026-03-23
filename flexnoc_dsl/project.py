"""NocProject — main entry point for FlexNoC DSL."""

from .protocol import Protocol
from .clock import ClockDomain, _parse_freq
from .socket import Initiator, Target, Flow, Mapping, _parse_size, create_interleaved_mappings
from .port import Port, ModeFlag, Observer, UserFlag, PowerDomain, Voltage
from .architecture import Architecture
from .pdd_writer import PddWriter


class NocProject:
    """Top-level NoC project builder.

    Usage:
        noc = NocProject("my_noc")
        axi = noc.add_protocol("AXI_prot", AXI(addr=32, data=64, id=4))
        clk = noc.add_clock("clk_domain", freq="500MHz", port="clk", reset="rst_n")
        noc.add_initiator("init_0", protocol=axi, clock=clk)
        noc.add_target("targ_0", protocol=axi, clock=clk, base=0x0, size="256M")
        noc.connect_all()
        noc.set_export("Verilog", simulator="VCS")
        noc.write_pdd("output.pdd")
    """

    def __init__(self, name: str):
        self._name = name
        self._spec_name = name
        self._arch_name = f"{name}_arch"
        self._struct_name = f"{name}_struct"

        self._protocols: dict[str, Protocol] = {}
        self._clocks: list[ClockDomain] = []
        self._initiators: list[Initiator] = []
        self._targets: list[Target] = []
        self._observers: list[Observer] = []
        self._mode_flags: list[ModeFlag] = []
        self._user_flags: list[UserFlag] = []
        self._power_domains: list[PowerDomain] = []
        self._voltages: list[Voltage] = []
        self._user_ports: list[Port] = []
        self._connectivity: dict = {}  # (init_name, targ_name) -> bool
        self._urgency_levels: int = 2
        self._use_error_codes: bool = False
        self._arbiter_mode: str = "ROTATE"  # ROTATE, PRIORITY, ROUND_ROBIN, FIFO
        self._export: dict = {}
        self._exports: list[dict] = []  # multiple export options
        self._noc_registers: dict = {}

        self._architecture = Architecture()

    @property
    def architecture(self) -> Architecture:
        """Access the architecture layer for manual topology control."""
        return self._architecture

    # ---- Protocol ----

    def add_protocol(self, name: str, proto: Protocol) -> Protocol:
        proto.name = name
        self._protocols[name] = proto
        return proto

    # ---- Clock ----

    def add_clock(self, name: str, freq="500MHz", port: str = "clk",
                  reset: str = "rst_n", test_mode: str = "Tm",
                  clock_type: str = "Root",
                  voltage_ref: str = "",
                  comment: str = "",
                  power_ref: str = "") -> ClockDomain:
        clk = ClockDomain(
            name=name,
            frequency=_parse_freq(freq),
            port_name=port,
            reset_name=reset,
            test_mode=test_mode,
            clock_type=clock_type,
            voltage_ref=voltage_ref,
            comment=comment,
            power_ref=power_ref,
        )
        self._clocks.append(clk)
        return clk

    # ---- Sockets ----

    def add_initiator(self, name: str, protocol: Protocol = None,
                      clock: ClockDomain = None,
                      pending_trans: int = 4, pending_ids: int = 1,
                      use_soft_lock: bool = False,
                      use_press: bool = False,
                      clock_gating: str = "",
                      comment: str = "",
                      power_domain: str = "",
                      conversion: dict = None) -> Initiator:
        init = Initiator(
            name=name,
            protocol_ref=protocol.name if protocol else "",
            clock=clock,
            pending_trans=pending_trans,
            pending_ids=pending_ids,
            use_soft_lock=use_soft_lock,
            use_press=use_press,
            clock_gating=clock_gating,
            comment=comment,
            power_domain=power_domain,
            conversion=conversion or {},
        )
        init._protocol_obj = protocol
        self._initiators.append(init)
        return init

    def add_target(self, name: str, protocol: Protocol = None,
                   clock: ClockDomain = None,
                   base: int = 0, size="0",
                   pending_trans: int = 16,
                   seq_id_width: int = 0,
                   use_soft_lock: bool = False,
                   clock_gating: str = "",
                   comment: str = "",
                   power_domain: str = "",
                   seq_id_allocation: str = "",
                   conversion: dict = None,
                   specials_mapping: dict = None) -> Target:
        parsed_size = _parse_size(size) if isinstance(size, str) else size
        targ = Target(
            name=name,
            protocol_ref=protocol.name if protocol else "",
            clock=clock,
            base_address=base,
            size=parsed_size,
            pending_trans=pending_trans,
            seq_id_width=seq_id_width,
            use_soft_lock=use_soft_lock,
            clock_gating=clock_gating,
            comment=comment,
            power_domain=power_domain,
            seq_id_allocation=seq_id_allocation,
            conversion=conversion or {},
            specials_mapping=specials_mapping or {},
        )
        targ._protocol_obj = protocol
        self._targets.append(targ)
        return targ

    def add_interleaved_targets(self, names: list, protocol: Protocol = None,
                                clock: ClockDomain = None,
                                total_base: int = 0, total_size="0",
                                stripe_size="4K",
                                pending_trans: int = 16,
                                seq_id_width: int = 0,
                                use_soft_lock: bool = False,
                                min_interleave_size: int = -1,
                                access: str = "ReadWrite") -> list:
        """Create multiple targets with interleaved (striped) address mappings.

        This configures address-based interleaving where consecutive stripes
        of the global address space are routed to different targets in
        round-robin fashion. Commonly used for DDR interleaving.

        Args:
            names: List of target names, e.g. ["DDR0", "DDR1"].
            protocol: Shared protocol for all targets.
            clock: Shared clock domain.
            total_base: Start of the interleaved address region.
            total_size: Total size of the interleaved region (e.g. "2G").
            stripe_size: Interleave granularity (e.g. "1K", "4K").
            pending_trans: Max pending transactions per target.
            seq_id_width: wSeqId for target NIU.
            use_soft_lock: Enable soft lock on targets.
            min_interleave_size: Response interleave size (-1=omit).
            access: Access type for all mappings.

        Returns:
            List of Target objects created.
        """
        parsed_total = _parse_size(total_size)
        parsed_stripe = _parse_size(stripe_size)
        num_targets = len(names)
        per_target_size = parsed_total // num_targets

        all_mappings = create_interleaved_mappings(
            num_targets=num_targets,
            stripe_size=parsed_stripe,
            total_size=parsed_total,
            base_address=total_base,
            access=access,
        )

        targets = []
        for i, name in enumerate(names):
            targ = Target(
                name=name,
                protocol_ref=protocol.name if protocol else "",
                clock=clock,
                base_address=total_base,
                size=per_target_size,
                pending_trans=pending_trans,
                seq_id_width=seq_id_width,
                use_soft_lock=use_soft_lock,
                min_interleave_size=min_interleave_size,
            )
            targ._protocol_obj = protocol
            # Set up the flow with interleaved mappings
            flow = Flow(name="0", mappings=all_mappings[i])
            targ.flows = [flow]
            self._targets.append(targ)
            targets.append(targ)
        return targets

    # ---- Observers ----

    def add_observer(self, name: str, clock: ClockDomain = None) -> Observer:
        obs = Observer(name=name, clock=clock)
        self._observers.append(obs)
        return obs

    # ---- Mode Flags ----

    def add_mode_flag(self, name: str, port: str = "",
                      active_value: int = 1) -> ModeFlag:
        mf = ModeFlag(name=name, port_name=port or name.lower(),
                      active_value=active_value)
        self._mode_flags.append(mf)
        return mf

    # ---- User Flags ----

    def add_user_flag(self, name: str) -> UserFlag:
        """Add a user-defined flag (e.g. '0_debug', '1_privileged')."""
        uf = UserFlag(name=name)
        self._user_flags.append(uf)
        return uf

    # ---- Power & Voltage ----

    def add_power_domain(self, name: str, kind: str = "ALWAYS_ON",
                         comment: str = "",
                         activity_zones: list = None) -> PowerDomain:
        """Add a power domain (e.g. ALWAYS_ON, SUPPLY, SWITCHABLE).

        Args:
            name: Domain name (e.g. 'INTERCO_dom').
            kind: ALWAYS_ON, SUPPLY, or SWITCHABLE.
            comment: Optional designer comment.
            activity_zones: Optional list of activity zone names.
        """
        pd = PowerDomain(name=name, kind=kind, comment=comment,
                         activity_zones=activity_zones or [])
        self._power_domains.append(pd)
        return pd

    def add_voltage(self, name: str, value: str = "0.81",
                    comment: str = "") -> Voltage:
        """Add a voltage object."""
        v = Voltage(name=name, value=value, comment=comment)
        self._voltages.append(v)
        return v

    # ---- User Ports ----

    def add_user_port(self, name: str, direction: str = "Input",
                      width: int = 1, clock: ClockDomain = None,
                      default: int = None) -> Port:
        port = Port(
            name=name,
            port_type="User",
            clock_ref=clock.clock_ref if clock else "None",
            width=width,
            direction=direction,
            default_val=default,
        )
        self._user_ports.append(port)
        return port

    # ---- NOC Registers ----

    def add_noc_registers(self, name: str, clock: ClockDomain = None,
                          base: int = 0):
        self._noc_registers = {"name": name, "clock": clock, "base": base}

    # ---- QoS ----

    def set_urgency_levels(self, levels: int):
        self._urgency_levels = levels

    def set_arbiter_mode(self, mode: str = "ROTATE"):
        """Set the default arbiter mode.

        Valid values: FIXED, ROTATE, ROUND_ROBIN, FIFO, ROUND_ROBIN_URG
        """
        self._arbiter_mode = mode

    def set_use_error_codes(self, enabled: bool = True):
        """Enable useErrorCodes in specification globals."""
        self._use_error_codes = enabled

    # ---- Connectivity ----

    def connect_all(self):
        """Set full mesh connectivity (all initiators → all targets)."""
        for init in self._initiators:
            for targ in self._targets:
                self._connectivity[(init.name, targ.name)] = True

    def connect(self, init_name: str, targ_names: list):
        """Connect specific initiator to specific targets."""
        for targ_name in targ_names:
            self._connectivity[(init_name, targ_name)] = True

    def disconnect(self, init_name: str, targ_name: str):
        """Explicitly disconnect an initiator from a target."""
        self._connectivity[(init_name, targ_name)] = False

    # ---- Export ----

    def set_export(self, fmt: str = "Verilog", simulator: str = "VCS",
                   name: str = "",
                   synthesis_tool: str = "",
                   files: str = "",
                   customer_cells: dict = None):
        """Configure an export option.

        Args:
            fmt: Export format ('Verilog', 'SystemC').
            simulator: Simulator name ('VCS', 'Xcelium', 'ModelSim').
            name: Export option name.
            synthesis_tool: 'DC' or 'Genus' (empty=simulation only).
            files: 'SingleFile' to merge all RTL into one file.
            customer_cells: Dict of cell overrides, e.g.
                {'GaterCell': '/path/to/G.v', 'SynchronizerCell': '/path/to/S.v'}
        """
        export = {
            "name": name or f"exports.{'Vlog' if fmt == 'Verilog' else fmt}",
            "format": fmt,
            "simulator": simulator,
            "synthesis_tool": synthesis_tool,
            "files": files,
            "customer_cells": customer_cells or {},
        }
        self._export = export
        # Also add to multi-export list
        self._exports.append(export)

    def add_export(self, fmt: str = "Verilog", simulator: str = "VCS",
                   name: str = "",
                   synthesis_tool: str = "",
                   files: str = "",
                   customer_cells: dict = None):
        """Add an additional export option (supports multiple exports)."""
        export = {
            "name": name or f"exports.{'Vlog' if fmt == 'Verilog' else fmt}",
            "format": fmt,
            "simulator": simulator,
            "synthesis_tool": synthesis_tool,
            "files": files,
            "customer_cells": customer_cells or {},
        }
        self._exports.append(export)

    # ---- Build & Write ----

    def _finalize(self):
        """Compute derived values before writing."""
        # Ensure all sockets have default flows
        for init in self._initiators:
            total_mask = 0
            for targ in self._targets:
                if self._connectivity.get((init.name, targ.name), False):
                    # Check actual mapping coverage (handles interleaved targets)
                    end = targ.base_address + targ.size
                    for flow in targ.flows:
                        for m in flow.mappings:
                            m_end = m.global_address + m.effective_mask() + 1
                            if m_end > end:
                                end = m_end
                    if end > total_mask:
                        total_mask = end
            total_mask = total_mask - 1 if total_mask else 0
            init._ensure_default_flow(total_mask)

        for targ in self._targets:
            targ._ensure_default_flow()

        # If no connectivity set, default to full mesh
        if not self._connectivity:
            self.connect_all()

        # Auto-derive architecture
        self._architecture.auto_derive(
            self._initiators, self._targets, self._clocks,
            observers=self._observers,
            noc_registers=self._noc_registers or None,
            urgency_levels=self._urgency_levels,
        )

    def write_pdd(self, path: str):
        """Finalize and write PDD to file."""
        self._finalize()
        writer = PddWriter(self)
        writer.write(path)

    def get_export_command(self, pdd_path: str, output_dir: str = "./output") -> str:
        """Return the FlexNoC CLI command to export Verilog from this PDD."""
        export_name = self._export.get("name", "exports.Vlog")
        return (
            f"FlexNoC -d False -p {pdd_path} exportVerilog "
            f"-s {self._struct_name} -c {export_name} -o {output_dir}"
        )
