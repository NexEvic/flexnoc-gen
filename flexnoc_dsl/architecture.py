"""Architecture auto-derivation and manual override."""

from .switch import DtpSwitch, DtpLink, SrvSwitch, ObsSwitch, Route


class Architecture:
    """Manages the switchBasedArchitecture layer.

    Can auto-derive a crossbar topology from specification, or accept
    manual switch/link/route definitions for custom topologies.
    """

    def __init__(self):
        self.switches: list[DtpSwitch] = []
        self.links: list[DtpLink] = []
        self.srv_switches: list[SrvSwitch] = []
        self.obs_switches: list[ObsSwitch] = []
        self.routes: list[Route] = []
        self.observation_routes: list[dict] = []
        self.service_routes: list[dict] = []
        self._manual_mode = False

    # --- Manual topology API ---

    def add_switch(self, name: str, clock=None, n_byte_per_word: int = 8,
                   header_penalty: str = "NONE") -> DtpSwitch:
        self._manual_mode = True
        clock_ref = clock.arch_clock_ref if clock else ""
        sw = DtpSwitch(name=name, clock_ref=clock_ref,
                       n_byte_per_word=n_byte_per_word,
                       header_penalty=header_penalty)
        self.switches.append(sw)
        return sw

    def add_link(self, name: str, clock=None, buffering: str = "FIFO",
                 size: int = 32, packets: int = 4,
                 n_byte_per_word: int = 8) -> DtpLink:
        self._manual_mode = True
        clock_ref = clock.arch_clock_ref if clock else ""
        link = DtpLink(name=name, clock_ref=clock_ref, buffering=buffering,
                       n_byte=size, n_packet=packets,
                       n_byte_per_word=n_byte_per_word)
        self.links.append(link)
        return link

    def set_route(self, init_flow: str, targ_flow: str,
                  request: list = None, response: list = None):
        """Set explicit route. Elements are switch/link objects or names."""
        def _to_names(path):
            if not path:
                return []
            return [getattr(e, "name", e) for e in path]

        self.routes.append(Route(
            init_ref=init_flow, targ_ref=targ_flow,
            request_path=_to_names(request),
            response_path=_to_names(response),
        ))

    # --- Auto-derivation ---

    def auto_derive(self, initiators, targets, clocks, observers=None,
                    noc_registers=None, urgency_levels=2):
        """Auto-derive crossbar topology from specification elements."""
        if self._manual_mode:
            self._fill_domain_crossings(initiators, targets)
            return

        clock_groups = self._group_by_clock(initiators, targets)

        if len(clock_groups) == 1:
            self._derive_single_clock(initiators, targets, clocks)
        else:
            self._derive_multi_clock(initiators, targets, clocks, clock_groups)

        if observers:
            self._derive_observation(observers, targets, clocks)
        if noc_registers:
            self._derive_service(noc_registers, clocks)

    def _group_by_clock(self, initiators, targets) -> dict:
        groups = {}
        for i in initiators:
            clk_name = i.clock.name if i.clock else "default"
            groups.setdefault(clk_name, {"inits": [], "targs": []})
            groups[clk_name]["inits"].append(i)
        for t in targets:
            clk_name = t.clock.name if t.clock else "default"
            groups.setdefault(clk_name, {"inits": [], "targs": []})
            groups[clk_name]["targs"].append(t)
        return groups

    def _derive_single_clock(self, initiators, targets, clocks):
        clock = initiators[0].clock if initiators else targets[0].clock
        max_data = max(
            [_get_data_width(i) for i in initiators] +
            [_get_data_width(t) for t in targets],
            default=8,
        )
        n_byte = max_data // 8

        # 2 switches: sw0 = response (initiator side), sw1 = request (target side)
        sw0 = DtpSwitch(
            name="dtpSwitch000",
            clock_ref=clock.arch_clock_ref,
            domain_crossings=[f"(switchBasedArchitecture:{i.name}/I)"
                              for i in initiators],
            n_byte_per_word=n_byte,
        )
        sw1 = DtpSwitch(
            name="dtpSwitch001",
            clock_ref=clock.arch_clock_ref,
            domain_crossings=[f"(switchBasedArchitecture:{t.name}/T)"
                              for t in targets],
            n_byte_per_word=n_byte,
        )
        self.switches = [sw0, sw1]

        # All routes: init → sw1 (request) → target, target → sw0 (response) → init
        for init in initiators:
            for tidx, targ in enumerate(targets):
                for fi, flow in enumerate(init.flows or [type("F", (), {"name": "0"})()]):
                    for ft, tflow in enumerate(targ.flows or [type("F", (), {"name": "0"})()]):
                        self.routes.append(Route(
                            init_ref=f"{init.name}/I/{flow.name}",
                            targ_ref=f"{targ.name}/T/{tflow.name}",
                            request_path=["dtpSwitch001"],
                            response_path=["dtpSwitch000"],
                        ))

    def _derive_multi_clock(self, initiators, targets, clocks, clock_groups):
        """Multi-clock: one switch pair per domain + FIFO links between domains."""
        sw_idx = 0
        domain_switches = {}  # clock_name -> (req_sw, rsp_sw)

        all_clocks_used = set()
        for i in initiators:
            all_clocks_used.add(i.clock.name if i.clock else "default")
        for t in targets:
            all_clocks_used.add(t.clock.name if t.clock else "default")

        clock_map = {c.name: c for c in clocks}

        # Create switch pair per domain
        for clk_name in sorted(all_clocks_used):
            clock = clock_map.get(clk_name)
            if not clock:
                continue
            max_data = 8
            for i in initiators:
                if (i.clock and i.clock.name == clk_name):
                    max_data = max(max_data, _get_data_width(i))
            for t in targets:
                if (t.clock and t.clock.name == clk_name):
                    max_data = max(max_data, _get_data_width(t))
            n_byte = max(max_data // 8, 1)

            rsp_sw = DtpSwitch(
                name=f"dtpSwitch{sw_idx:03d}",
                clock_ref=clock.arch_clock_ref,
                domain_crossings=[],
                n_byte_per_word=n_byte,
            )
            sw_idx += 1
            req_sw = DtpSwitch(
                name=f"dtpSwitch{sw_idx:03d}",
                clock_ref=clock.arch_clock_ref,
                domain_crossings=[],
                n_byte_per_word=n_byte,
            )
            sw_idx += 1
            self.switches.extend([rsp_sw, req_sw])
            domain_switches[clk_name] = (req_sw, rsp_sw)

        # Fill domain crossings
        for i in initiators:
            clk_name = i.clock.name if i.clock else "default"
            if clk_name in domain_switches:
                _, rsp_sw = domain_switches[clk_name]
                rsp_sw.domain_crossings.append(
                    f"(switchBasedArchitecture:{i.name}/I)")

        for t in targets:
            clk_name = t.clock.name if t.clock else "default"
            if clk_name in domain_switches:
                req_sw, _ = domain_switches[clk_name]
                req_sw.domain_crossings.append(
                    f"(switchBasedArchitecture:{t.name}/T)")

        # Create FIFO links between domains and routes
        link_idx = 0
        created_links = {}  # (src_domain, dst_domain) -> (fwd_link, rev_link)

        for init in initiators:
            i_clk = init.clock.name if init.clock else "default"
            for targ in targets:
                t_clk = targ.clock.name if targ.clock else "default"
                req_sw_i, rsp_sw_i = domain_switches.get(i_clk, (None, None))
                req_sw_t, rsp_sw_t = domain_switches.get(t_clk, (None, None))

                if i_clk == t_clk:
                    # Same domain
                    req_path = [req_sw_t.name] if req_sw_t else []
                    rsp_path = [rsp_sw_i.name] if rsp_sw_i else []
                else:
                    # Cross-domain: need FIFO links
                    pair_key = tuple(sorted([i_clk, t_clk]))
                    if pair_key not in created_links:
                        t_clock = clock_map.get(t_clk)
                        i_clock = clock_map.get(i_clk)
                        fwd_link = DtpLink(
                            name=f"fifo_req_{link_idx:03d}",
                            clock_ref=t_clock.arch_clock_ref if t_clock else "",
                            buffering="FIFO", n_byte=32, n_packet=4,
                        )
                        rev_link = DtpLink(
                            name=f"fifo_rsp_{link_idx:03d}",
                            clock_ref=i_clock.arch_clock_ref if i_clock else "",
                            buffering="FIFO", n_byte=32, n_packet=4,
                        )
                        self.links.extend([fwd_link, rev_link])
                        created_links[pair_key] = (fwd_link, rev_link)
                        link_idx += 1
                    fwd_link, rev_link = created_links[pair_key]
                    if req_sw_t and rsp_sw_i:
                        req_path = [rsp_sw_i.name, fwd_link.name, req_sw_t.name]
                        rsp_path = [rsp_sw_t.name, rev_link.name, rsp_sw_i.name]
                    else:
                        req_path = [fwd_link.name]
                        rsp_path = [rev_link.name]

                for fi, flow in enumerate(init.flows or [type("F", (), {"name": "0"})()]):
                    for ft, tflow in enumerate(targ.flows or [type("F", (), {"name": "0"})()]):
                        self.routes.append(Route(
                            init_ref=f"{init.name}/I/{flow.name}",
                            targ_ref=f"{targ.name}/T/{tflow.name}",
                            request_path=req_path,
                            response_path=rsp_path,
                        ))

    def _fill_domain_crossings(self, initiators, targets):
        """For manual mode, fill domain crossings on existing switches."""
        pass  # User handles this manually

    def _derive_observation(self, observers, targets, clocks):
        """Auto-derive observation switches and routes."""
        for obs in observers:
            obs_clk = obs.clock
            obs_sw = ObsSwitch(
                name=f"obsSwitch{len(self.obs_switches):03d}",
                clock_ref=obs_clk.arch_clock_ref if obs_clk else "",
            )
            self.obs_switches.append(obs_sw)

            for targ_name in obs.watched_targets:
                self.observation_routes.append({
                    "source": f"(switchBasedArchitecture:{targ_name}/T)",
                    "observer": f"(switchBasedArchitecture:{obs.name})",
                    "path": [obs_sw.name],
                    "priority": 3,
                })

    def _derive_service(self, noc_registers, clocks):
        """Auto-derive service switch and routes."""
        noc_clk = noc_registers.get("clock")
        srv_sw = SrvSwitch(
            name=f"srvSwitch{len(self.srv_switches):03d}",
            clock_ref=noc_clk.arch_clock_ref if noc_clk else "",
            domain_crossings=[
                f"(switchBasedArchitecture:{noc_registers['name']})"
            ],
        )
        self.srv_switches.append(srv_sw)


def _get_data_width(socket) -> int:
    """Get data width from a socket's protocol reference."""
    if hasattr(socket, "_protocol_obj") and socket._protocol_obj:
        return socket._protocol_obj.data_width
    return 64
