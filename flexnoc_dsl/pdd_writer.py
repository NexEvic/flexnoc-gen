"""PDD XML writer — converts internal model to FlexNoC PDD format."""

from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


class PddWriter:
    """Generates PDD XML from a NocProject."""

    PDD_VERSION = "5.3.0r186A"
    FLEXNOC_REV = "5.3.0"

    def __init__(self, project):
        self.p = project

    def write(self, path: str):
        root = self._build_root()
        xml_str = tostring(root, encoding="unicode")
        pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
        # Remove XML declaration, PDD files don't use it
        lines = pretty.split("\n")
        if lines and lines[0].startswith("<?xml"):
            lines = lines[1:]
        with open(path, "w") as f:
            f.write("\n".join(lines))

    def _build_root(self) -> Element:
        root = Element("object")
        root.set("kind", "project")
        root.set("name", "")
        root.set("savedWithFlexNoCrev", self.FLEXNOC_REV)
        root.set("v", self.PDD_VERSION)

        self._add_protocols(root)
        self._add_architecture(root)
        self._add_structure(root)
        self._add_specification(root)
        self._add_export_folder(root)
        self._add_export_option(root)
        return root

    # ---- Protocols ----

    def _add_protocols(self, root):
        for name, proto in self.p._protocols.items():
            obj = SubElement(root, "object")
            obj.set("disabled", "0")
            obj.set("kind", "protocol")
            obj.set("name", name)
            props = SubElement(obj, "properties")
            pentry = SubElement(props, "entry")
            pentry.set("key", "protocol")
            pentry.set("value", proto.protocol_type)
            for k, v in self._protocol_entries(proto):
                e = SubElement(pentry, "entry")
                e.set("key", k)
                e.set("value", str(v))

    def _protocol_entries(self, proto):
        entries = []
        if proto.protocol_type in ("AXI", "OCP_Lite"):
            entries.extend([
                ("enRead", proto.en_read),
                ("enWrite", proto.en_write),
                ("useFixed", proto.use_fixed),
                ("wAddr", proto.addr_width),
                ("wData", proto.data_width),
            ])
            if proto.id_width:
                entries.append(("wId", proto.id_width))
        elif proto.protocol_type == "AHB":
            entries.extend([
                ("wAddr", proto.addr_width),
                ("wData", proto.data_width),
            ])
        else:
            # APB and others: addr + data
            entries.extend([
                ("wAddr", proto.addr_width),
                ("wData", proto.data_width),
            ])
        for k, v in proto.extra.items():
            entries.append((k, v))
        return entries

    # ---- Architecture ----

    def _needs_reassembly(self, init):
        """Check if initiator connects to targets with different protocol."""
        init_proto = self.p._protocols.get(init.protocol_ref)
        if not init_proto:
            return False
        for targ in self.p._targets:
            if self.p._connectivity.get((init.name, targ.name), False):
                targ_proto = self.p._protocols.get(targ.protocol_ref)
                if targ_proto and targ_proto.protocol_type != init_proto.protocol_type:
                    return True
        return False

    def _add_architecture(self, root):
        arch = self.p._architecture
        obj = SubElement(root, "object")
        obj.set("disabled", "1")
        obj.set("kind", "switchBasedArchitecture")
        obj.set("name", self.p._arch_name)
        obj.set("origin", f"(project:{self.p._spec_name})")
        props = SubElement(obj, "properties")

        # datapathRoute
        self._add_datapath_routes(props, arch)
        # dvmRoute
        _add_empty_entry(props, "dvmRoute")
        # globals
        self._add_arch_globals(props)
        # observationRoute
        self._add_observation_routes(props, arch)
        # serviceRoute
        self._add_service_routes(props, arch)

        # dtpSwitch objects
        for sw in arch.switches:
            self._add_dtp_switch(obj, sw)
        # dtpLink objects
        for link in arch.links:
            self._add_dtp_link(obj, link)
        # srvSwitch objects
        for srv in arch.srv_switches:
            self._add_srv_switch(obj, srv)
        # obsSwitch objects
        for obs in arch.obs_switches:
            self._add_obs_switch(obj, obs)

        # Shadow elements for sockets
        for init in self.p._initiators:
            self._add_init_shadow(obj, init)
        for targ in self.p._targets:
            self._add_targ_shadow(obj, targ)
        # Press shadow in architecture
        if any(i.use_press for i in self.p._initiators):
            ps = SubElement(obj, "shadow")
            ps.set("name", "press")
            SubElement(ps, "properties")

    def _add_datapath_routes(self, props, arch):
        dr = SubElement(props, "entry")
        dr.set("key", "datapathRoute")

        # Group routes by init_ref
        by_init = {}
        for route in arch.routes:
            by_init.setdefault(route.init_ref, []).append(route)

        for init_ref, routes in by_init.items():
            init_entry = SubElement(dr, "entry")
            init_entry.set("key", f"(switchBasedArchitecture:{init_ref})")
            for route in routes:
                targ_entry = SubElement(init_entry, "entry")
                targ_entry.set("key", f"(switchBasedArchitecture:{route.targ_ref})")
                # requestPath
                req = SubElement(targ_entry, "entry")
                req.set("key", "requestPath")
                for idx, sw_name in enumerate(route.request_path):
                    step = SubElement(req, "entry")
                    step.set("key", str(idx))
                    step.set("value", f"(switchBasedArchitecture:{sw_name})")
                # responsePath
                rsp = SubElement(targ_entry, "entry")
                rsp.set("key", "responsePath")
                for idx, sw_name in enumerate(route.response_path):
                    step = SubElement(rsp, "entry")
                    step.set("key", str(idx))
                    step.set("value", f"(switchBasedArchitecture:{sw_name})")

    def _add_arch_globals(self, props):
        g = SubElement(props, "entry")
        g.set("key", "globals")
        arb = SubElement(g, "entry")
        arb.set("key", "muxDefaultArbiters")
        mode = self.p._arbiter_mode
        for n in ["2 ports", "3 ports", "4 ports"]:
            e = SubElement(arb, "entry")
            e.set("key", n)
            e.set("value", mode)

    def _add_observation_routes(self, props, arch):
        obs_entry = SubElement(props, "entry")
        obs_entry.set("key", "observationRoute")
        for obs_route in arch.observation_routes:
            src = SubElement(obs_entry, "entry")
            src.set("key", obs_route["source"])
            dst = SubElement(src, "entry")
            dst.set("key", obs_route["observer"])
            req = SubElement(dst, "entry")
            req.set("key", "requestPath")
            req.set("value", str(obs_route.get("priority", 3)))
            for idx, sw_name in enumerate(obs_route["path"]):
                step = SubElement(req, "entry")
                step.set("key", str(idx))
                step.set("value", f"(switchBasedArchitecture:{sw_name})")

    def _add_service_routes(self, props, arch):
        srv_entry = SubElement(props, "entry")
        srv_entry.set("key", "serviceRoute")
        for srv_route in arch.service_routes:
            noc_reg = SubElement(srv_entry, "entry")
            noc_reg.set("key", srv_route["noc_registers"])
            for target_info in srv_route.get("targets", []):
                tgt = SubElement(noc_reg, "entry")
                tgt.set("key", target_info["target"])
                req = SubElement(tgt, "entry")
                req.set("key", "requestPath")
                for idx, name in enumerate(target_info.get("request_path", [])):
                    s = SubElement(req, "entry")
                    s.set("key", str(idx))
                    s.set("value", f"(switchBasedArchitecture:{name})")
                rsp = SubElement(tgt, "entry")
                rsp.set("key", "responsePath")
                for idx, name in enumerate(target_info.get("response_path", [])):
                    s = SubElement(rsp, "entry")
                    s.set("key", str(idx))
                    s.set("value", f"(switchBasedArchitecture:{name})")

    def _add_dtp_switch(self, parent, sw):
        obj = SubElement(parent, "object")
        obj.set("disabled", "0")
        obj.set("kind", "dtpSwitch")
        obj.set("name", sw.name)
        props = SubElement(obj, "properties")
        # common
        common = SubElement(props, "entry")
        common.set("key", "common")
        clk = SubElement(common, "entry")
        clk.set("key", "clock")
        clk.set("value", sw.clock_ref)
        # datapath
        dp = SubElement(props, "entry")
        dp.set("key", "datapath")
        dc = SubElement(dp, "entry")
        dc.set("key", "domainCrossings")
        for crossing in sw.domain_crossings:
            e = SubElement(dc, "entry")
            e.set("key", crossing)
        # inputPipes
        ip = SubElement(dp, "entry")
        ip.set("key", "inputPipes")
        for pipe_ref, stages in sw.input_pipes.items():
            pe = SubElement(ip, "entry")
            pe.set("key", pipe_ref)
            pe.set("value", str(stages))
        # outputPipes
        op = SubElement(dp, "entry")
        op.set("key", "outputPipes")
        for pipe_ref, stages in sw.output_pipes.items():
            pe = SubElement(op, "entry")
            pe.set("key", pipe_ref)
            pe.set("value", str(stages))
        ser = SubElement(dp, "entry")
        ser.set("key", "serialization")
        hp = SubElement(ser, "entry")
        hp.set("key", "headerPenalty")
        hp.set("value", sw.header_penalty)
        bpw = SubElement(ser, "entry")
        bpw.set("key", "nBytePerWord")
        bpw.set("value", str(sw.n_byte_per_word))

    def _add_dtp_link(self, parent, link):
        obj = SubElement(parent, "object")
        obj.set("disabled", "0")
        obj.set("kind", "dtpLink")
        obj.set("name", link.name)
        props = SubElement(obj, "properties")
        common = SubElement(props, "entry")
        common.set("key", "common")
        clk = SubElement(common, "entry")
        clk.set("key", "clock")
        clk.set("value", link.clock_ref)
        if not link.has_module:
            mod = SubElement(common, "entry")
            mod.set("key", "module")
            mod.set("value", "None")
        dp = SubElement(props, "entry")
        dp.set("key", "datapath")
        buf = SubElement(dp, "entry")
        buf.set("key", "buffering")
        buf.set("value", link.buffering)
        nb = SubElement(buf, "entry")
        nb.set("key", "nByte")
        nb.set("value", str(link.n_byte))
        np_ = SubElement(buf, "entry")
        np_.set("key", "nPacket")
        np_.set("value", str(link.n_packet))
        ser = SubElement(dp, "entry")
        ser.set("key", "serialization")
        hp = SubElement(ser, "entry")
        hp.set("key", "headerPenalty")
        hp.set("value", link.header_penalty)
        bpw = SubElement(ser, "entry")
        bpw.set("key", "nBytePerWord")
        bpw.set("value", str(link.n_byte_per_word))

    def _add_srv_switch(self, parent, srv):
        obj = SubElement(parent, "object")
        obj.set("disabled", "0")
        obj.set("kind", "srvSwitch")
        obj.set("name", srv.name)
        props = SubElement(obj, "properties")
        common = SubElement(props, "entry")
        common.set("key", "common")
        clk = SubElement(common, "entry")
        clk.set("key", "clock")
        clk.set("value", srv.clock_ref)
        svc = SubElement(props, "entry")
        svc.set("key", "service")
        dc = SubElement(svc, "entry")
        dc.set("key", "domainCrossings")
        for c in srv.domain_crossings:
            e = SubElement(dc, "entry")
            e.set("key", c)
        _add_empty_entry(svc, "inputPipes")
        _add_empty_entry(svc, "outputPipes")
        ser = SubElement(svc, "entry")
        ser.set("key", "serialization")
        hp = SubElement(ser, "entry")
        hp.set("key", "headerPenalty")
        hp.set("value", srv.header_penalty)
        bpw = SubElement(ser, "entry")
        bpw.set("key", "nBytePerWord")
        bpw.set("value", str(srv.n_byte_per_word))

    def _add_obs_switch(self, parent, obs):
        obj = SubElement(parent, "object")
        obj.set("disabled", "0")
        obj.set("kind", "obsSwitch")
        obj.set("name", obs.name)
        props = SubElement(obj, "properties")
        common = SubElement(props, "entry")
        common.set("key", "common")
        clk = SubElement(common, "entry")
        clk.set("key", "clock")
        clk.set("value", obs.clock_ref)
        o = SubElement(props, "entry")
        o.set("key", "observation")
        _add_empty_entry(o, "domainCrossings")
        _add_empty_entry(o, "inputPipes")
        _add_empty_entry(o, "outputPipes")
        ser = SubElement(o, "entry")
        ser.set("key", "serialization")
        hp = SubElement(ser, "entry")
        hp.set("key", "headerPenalty")
        hp.set("value", obs.header_penalty)
        bpw = SubElement(ser, "entry")
        bpw.set("key", "nBytePerWord")
        bpw.set("value", str(obs.n_byte_per_word))

    def _add_init_shadow(self, parent, init):
        shadow = SubElement(parent, "shadow")
        shadow.set("name", init.name)
        SubElement(shadow, "properties")
        i_shadow = SubElement(shadow, "shadow")
        i_shadow.set("name", "I")
        i_props = SubElement(i_shadow, "properties")
        dp = SubElement(i_props, "entry")
        dp.set("key", "datapath")
        perf = SubElement(dp, "entry")
        perf.set("key", "performance")
        _add_kv(perf, "nPendingOrderId", str(init.pending_ids))
        _add_kv(perf, "nPendingTrans", str(init.pending_trans))
        # nReassemblyBuffer needed when protocol conversion exists
        if self._needs_reassembly(init):
            _add_kv(perf, "nReassemblyBuffer", "2")
        # Flow shadows
        for flow in (init.flows or [type("F", (), {"name": "0"})()]):
            f_shadow = SubElement(i_shadow, "shadow")
            f_shadow.set("name", flow.name)
            SubElement(f_shadow, "properties")
            for mapping in getattr(flow, "mappings", [type("M", (), {"name": "0"})()]):
                m_shadow = SubElement(f_shadow, "shadow")
                m_shadow.set("name", getattr(mapping, "name", "0"))
                SubElement(m_shadow, "properties")

    def _add_targ_shadow(self, parent, targ):
        shadow = SubElement(parent, "shadow")
        shadow.set("name", targ.name)
        SubElement(shadow, "properties")
        t_shadow = SubElement(shadow, "shadow")
        t_shadow.set("name", "T")
        t_props = SubElement(t_shadow, "properties")
        dp = SubElement(t_props, "entry")
        dp.set("key", "datapath")
        perf = SubElement(dp, "entry")
        perf.set("key", "performance")
        _add_kv(perf, "nPendingTrans", str(targ.pending_trans))
        if targ.seq_id_allocation:
            _add_kv(perf, "seqIdAllocation", targ.seq_id_allocation)
        for flow in (targ.flows or [type("F", (), {"name": "0"})()]):
            f_shadow = SubElement(t_shadow, "shadow")
            f_shadow.set("name", flow.name)
            SubElement(f_shadow, "properties")
            for mapping in getattr(flow, "mappings", [type("M", (), {"name": "0"})()]):
                m_shadow = SubElement(f_shadow, "shadow")
                m_shadow.set("name", getattr(mapping, "name", "0"))
                SubElement(m_shadow, "properties")

    # ---- Structure ----

    def _add_structure(self, root):
        arch = self.p._architecture
        obj = SubElement(root, "object")
        obj.set("disabled", "1")
        obj.set("kind", "switchBasedStructure")
        obj.set("name", self.p._struct_name)
        obj.set("origin", f"(project:{self.p._arch_name})")
        SubElement(obj, "properties")

        # Shadow for each socket
        for init in self.p._initiators:
            self._add_struct_socket_shadow(obj, init.name, "I", init.flows,
                                           use_press=init.use_press)
        for targ in self.p._targets:
            self._add_struct_socket_shadow(obj, targ.name, "T", targ.flows)
        # Shadow for observers
        for obs in self.p._observers:
            s = SubElement(obj, "shadow")
            s.set("name", obs.name)
            p = SubElement(s, "properties")
            if obs.interrupt_port:
                tp = SubElement(p, "entry")
                tp.set("key", "tacticalPorts")
                main = SubElement(tp, "entry")
                main.set("key", "main")
                fault = SubElement(main, "entry")
                fault.set("key", "Fault_0")
                fault.set("value", f"(switchBasedStructure:{obs.interrupt_port})")
        # Shadow for switches
        for sw in arch.switches:
            s = SubElement(obj, "shadow")
            s.set("name", sw.name)
            SubElement(s, "properties")
        # Shadow for links
        for link in arch.links:
            s = SubElement(obj, "shadow")
            s.set("name", link.name)
            SubElement(s, "properties")
        # Shadow for srv/obs switches
        for srv in arch.srv_switches:
            s = SubElement(obj, "shadow")
            s.set("name", srv.name)
            SubElement(s, "properties")
        for obs_sw in arch.obs_switches:
            s = SubElement(obj, "shadow")
            s.set("name", obs_sw.name)
            SubElement(s, "properties")
        # Press shadow if any initiator uses press
        if any(i.use_press for i in self.p._initiators):
            ps = SubElement(obj, "shadow")
            ps.set("name", "press")
            SubElement(ps, "properties")

    def _add_struct_socket_shadow(self, parent, socket_name, role, flows,
                                   use_press=False):
        s = SubElement(parent, "shadow")
        s.set("name", socket_name)
        p = SubElement(s, "properties")
        if use_press:
            tp = SubElement(p, "entry")
            tp.set("key", "tacticalPorts")
            main = SubElement(tp, "entry")
            main.set("key", "main")
            press = SubElement(main, "entry")
            press.set("key", "Press")
            press.set("value", "(switchBasedStructure:press)")
        r = SubElement(s, "shadow")
        r.set("name", role)
        SubElement(r, "properties")
        for flow in (flows or [type("F", (), {"name": "0", "mappings": [type("M", (), {"name": "0"})()]})()]):
            f = SubElement(r, "shadow")
            f.set("name", flow.name)
            SubElement(f, "properties")
            for mapping in getattr(flow, "mappings", [type("M", (), {"name": "0"})()]):
                m = SubElement(f, "shadow")
                m.set("name", getattr(mapping, "name", "0"))
                SubElement(m, "properties")

    # ---- Specification ----

    def _add_specification(self, root):
        obj = SubElement(root, "object")
        obj.set("disabled", "0")
        obj.set("kind", "specification")
        obj.set("name", self.p._spec_name)
        props = SubElement(obj, "properties")

        self._add_connectivity(props)
        self._add_dependencies(props)
        self._add_spec_globals(props)

        # Socket objects
        for init in self.p._initiators:
            self._add_init_socket(obj, init)
        for targ in self.p._targets:
            self._add_targ_socket(obj, targ)
        # Observer objects
        for obs in self.p._observers:
            self._add_observer_obj(obj, obs)
        # Mode flags
        for mf in self.p._mode_flags:
            self._add_mode_flag(obj, mf)
        # User flags
        for uf in self.p._user_flags:
            self._add_user_flag(obj, uf)
        # Power domains
        for pd in self.p._power_domains:
            self._add_power_domain(obj, pd)
        # Voltage objects
        for v in self.p._voltages:
            self._add_voltage(obj, v)
        # Clock regimes
        for clk in self.p._clocks:
            self._add_clock_regime(obj, clk)
        # Ports
        self._add_spec_ports(obj)

    def _add_connectivity(self, props):
        conn = SubElement(props, "entry")
        conn.set("key", "connectivity")
        connectivity = self.p._connectivity
        for init in self.p._initiators:
            for flow in (init.flows or [type("F", (), {"name": "0"})()]):
                init_key = f"(specification:{init.name}/I/{flow.name})"
                i_entry = SubElement(conn, "entry")
                i_entry.set("key", init_key)
                for targ in self.p._targets:
                    for tflow in (targ.flows or [type("F", (), {"name": "0"})()]):
                        targ_key = f"(specification:{targ.name}/T/{tflow.name})"
                        connected = connectivity.get(
                            (init.name, targ.name), True)
                        t_entry = SubElement(i_entry, "entry")
                        t_entry.set("key", targ_key)
                        t_entry.set("value", str(connected))

    def _add_dependencies(self, props):
        dep = SubElement(props, "entry")
        dep.set("key", "dependencies")
        primary = SubElement(dep, "entry")
        primary.set("key", "primary")
        for init in self.p._initiators:
            e = SubElement(primary, "entry")
            e.set("key", f"(specification:{init.name})")
            e.set("value", "True")
        for targ in self.p._targets:
            e = SubElement(primary, "entry")
            e.set("key", f"(specification:{targ.name})")
            e.set("value", "True")

    def _add_spec_globals(self, props):
        g = SubElement(props, "entry")
        g.set("key", "globals")
        compat = SubElement(g, "entry")
        compat.set("key", "backwardCompatibilityModes")
        _add_kv(compat, "V431AsyncCDCNoPartialReset", "False")
        _add_kv(g, "nUrgencyLevel", str(self.p._urgency_levels))
        if self.p._use_error_codes:
            _add_kv(g, "useErrorCodes", "True")

    def _add_init_socket(self, parent, init):
        sock = SubElement(parent, "object")
        sock.set("disabled", "0")
        sock.set("kind", "socket")
        sock.set("name", init.name)
        props = SubElement(sock, "properties")
        _add_kv(props, "clock", init.clock.clock_ref if init.clock else "")
        # clockGating
        if init.clock_gating:
            _add_kv(props, "clockGating", init.clock_gating)
        # comment
        if init.comment:
            _add_kv(props, "comment", init.comment)
        # power domain
        if init.power_domain:
            pw = SubElement(props, "entry")
            pw.set("key", "power")
            _add_kv(pw, "IPpowerDomain",
                    f"(specification:{init.power_domain})")
        # conversion
        if init.conversion:
            conv = SubElement(props, "entry")
            conv.set("key", "conversion")
            for ck, cv in init.conversion.items():
                _add_kv(conv, ck, str(cv))
        else:
            _add_empty_entry(props, "conversion")
        # Protocol reference
        prot = SubElement(props, "entry")
        prot.set("key", "protocol")
        prot.set("value", "REFERENCE")
        ref = SubElement(prot, "entry")
        ref.set("key", "reference")
        ref.set("value", f"(project:{init.protocol_ref})")
        # User mapping
        um = SubElement(props, "entry")
        um.set("key", "userMapping")
        drv = SubElement(um, "entry")
        drv.set("key", "driving")
        # If user_mapping has userFlags entries, emit them
        if init.user_mapping.get("userFlags"):
            uf_entry = SubElement(drv, "entry")
            uf_entry.set("key", "userFlags")
            for flag_ref, value in init.user_mapping["userFlags"].items():
                _add_kv(uf_entry, f"(specification:{flag_ref})", str(value))

        # Initiator role
        irole = SubElement(sock, "object")
        irole.set("disabled", "0")
        irole.set("kind", "initiator")
        irole.set("name", "I")
        iprops = SubElement(irole, "properties")
        params = SubElement(iprops, "entry")
        params.set("key", "parameters")
        _add_kv(params, "useSoftLock", str(init.use_soft_lock))
        if init.use_press:
            _add_kv(params, "usePress", "True")
        if init.min_interleave_size >= 0:
            _add_kv(params, "minInterleaveSize",
                    str(init.min_interleave_size))

        # Flows
        for flow in init.flows:
            self._add_flow(irole, flow)

    def _add_targ_socket(self, parent, targ):
        sock = SubElement(parent, "object")
        sock.set("disabled", "0")
        sock.set("kind", "socket")
        sock.set("name", targ.name)
        props = SubElement(sock, "properties")
        _add_kv(props, "clock", targ.clock.clock_ref if targ.clock else "")
        # clockGating
        if targ.clock_gating:
            _add_kv(props, "clockGating", targ.clock_gating)
        # comment
        if targ.comment:
            _add_kv(props, "comment", targ.comment)
        # power domain
        if targ.power_domain:
            pw = SubElement(props, "entry")
            pw.set("key", "power")
            _add_kv(pw, "IPpowerDomain",
                    f"(specification:{targ.power_domain})")
        # conversion
        if targ.conversion:
            conv = SubElement(props, "entry")
            conv.set("key", "conversion")
            for ck, cv in targ.conversion.items():
                _add_kv(conv, ck, str(cv))
        else:
            _add_empty_entry(props, "conversion")
        prot = SubElement(props, "entry")
        prot.set("key", "protocol")
        prot.set("value", "REFERENCE")
        ref = SubElement(prot, "entry")
        ref.set("key", "reference")
        ref.set("value", f"(project:{targ.protocol_ref})")
        # User mapping for targets
        um = SubElement(props, "entry")
        um.set("key", "userMapping")
        proto = self.p._protocols.get(targ.protocol_ref)
        user_flags = self.p._user_flags
        if proto and proto.protocol_type == "AXI":
            if user_flags:
                # Use userFlags-based mapping
                self._write_axi_userflag_mapping(um, targ)
            else:
                # Custom specials or default CONST_0
                specials = targ.specials_mapping
                for sig in ["ARCache", "AWCache"]:
                    s = SubElement(um, "entry")
                    s.set("key", sig)
                    sp = SubElement(s, "entry")
                    sp.set("key", "specials")
                    custom = specials.get(sig, {})
                    if custom:
                        for const_name, bits in custom.items():
                            c = SubElement(sp, "entry")
                            c.set("key", const_name)
                            c.set("value", bits)
                    else:
                        c = SubElement(sp, "entry")
                        c.set("key", "CONST_0")
                        c.set("value", "#0,1,2,3")
                prot_e = SubElement(um, "entry")
                prot_e.set("key", "Prot")
                sp = SubElement(prot_e, "entry")
                sp.set("key", "specials")
                prot_custom = specials.get("Prot", {})
                if prot_custom:
                    for const_name, bits in prot_custom.items():
                        c = SubElement(sp, "entry")
                        c.set("key", const_name)
                        c.set("value", bits)
                else:
                    c = SubElement(sp, "entry")
                    c.set("key", "CONST_0")
                    c.set("value", "#0,1,2")
        elif proto and proto.protocol_type == "AHB":
            # AHB needs HProt + XorHProt_6 userMapping
            for sig, bits in [("HProt", "#0,1,2,3"),
                              ("XorHProt_6", "#0")]:
                hp = SubElement(um, "entry")
                hp.set("key", sig)
                sp = SubElement(hp, "entry")
                sp.set("key", "specials")
                c = SubElement(sp, "entry")
                c.set("key", "CONST_0")
                c.set("value", bits)

        # Target role
        trole = SubElement(sock, "object")
        trole.set("disabled", "0")
        trole.set("kind", "target")
        trole.set("name", "T")
        tprops = SubElement(trole, "properties")
        params = SubElement(tprops, "entry")
        params.set("key", "parameters")
        _add_kv(params, "useSoftLock", str(targ.use_soft_lock))
        if targ.min_interleave_size >= 0:
            _add_kv(params, "minInterleaveSize",
                    str(targ.min_interleave_size))
        seq_id = targ.seq_id_width
        if not seq_id and proto:
            seq_id = proto.id_width
        if seq_id:
            _add_kv(params, "wSeqId", str(seq_id))

        for flow in targ.flows:
            self._add_flow(trole, flow)

    def _write_axi_userflag_mapping(self, um_parent, socket_obj):
        """Write AXI userMapping using userFlags instead of CONST_0 specials.

        Uses user_mapping dict from the socket if present, otherwise
        generates a default mapping based on PSI reference conventions.
        """
        custom = socket_obj.user_mapping
        user_flags = self.p._user_flags
        flag_names = [uf.name for uf in user_flags]

        if custom:
            # User-provided explicit mapping: {signal: {flag_name: bit_index}}
            for signal, flag_map in custom.items():
                if signal == "userFlags":
                    continue  # initiator driving style, handled elsewhere
                sig_entry = SubElement(um_parent, "entry")
                sig_entry.set("key", signal)
                uf_entry = SubElement(sig_entry, "entry")
                uf_entry.set("key", "userFlags")
                for flag_name, bit_idx in flag_map.items():
                    _add_kv(uf_entry, f"(specification:{flag_name})",
                            f"#{bit_idx}")
        else:
            # Default: all flags → CONST_0 on ARCache/AWCache/Prot/User
            for sig in ["ARCache", "AWCache"]:
                s = SubElement(um_parent, "entry")
                s.set("key", sig)
                sp = SubElement(s, "entry")
                sp.set("key", "specials")
                c = SubElement(sp, "entry")
                c.set("key", "CONST_0")
                c.set("value", "#0,1,2,3")
            prot_e = SubElement(um_parent, "entry")
            prot_e.set("key", "Prot")
            sp = SubElement(prot_e, "entry")
            sp.set("key", "specials")
            c = SubElement(sp, "entry")
            c.set("key", "CONST_0")
            c.set("value", "#0,1,2")

    def _add_flow(self, parent, flow):
        fobj = SubElement(parent, "object")
        fobj.set("disabled", "0")
        fobj.set("kind", "flow")
        fobj.set("name", flow.name)
        fprops = SubElement(fobj, "properties")
        if flow.default_error_target:
            _add_kv(fprops, "defaultErrorTarget",
                    f"(specification:{flow.default_error_target})")
        for mapping in flow.mappings:
            self._add_mapping(fobj, mapping)

    def _add_mapping(self, parent, mapping):
        mobj = SubElement(parent, "object")
        mobj.set("disabled", "0")
        mobj.set("kind", "mapping")
        mobj.set("name", mapping.name)
        mprops = SubElement(mobj, "properties")
        if mapping.access and mapping.access != "ReadWrite":
            _add_kv(mprops, "access", mapping.access)
        if mapping.comment:
            _add_kv(mprops, "comment", mapping.comment)
        _add_kv(mprops, "globalAddress", str(mapping.global_address))
        _add_kv(mprops, "localAddress", str(mapping.local_address))
        _add_kv(mprops, "mask", str(mapping.effective_mask()))
        if mapping.modes:
            modes = SubElement(mprops, "entry")
            modes.set("key", "modes")
            for mode_flag, val in mapping.modes.items():
                flag_name = mode_flag.name if hasattr(mode_flag, "name") else str(mode_flag)
                _add_kv(modes, f"(specification:{flag_name})", str(val))
        # readPermissions / writePermissions (empty entries for now)
        _add_empty_entry(mprops, "readPermissions")
        _add_empty_entry(mprops, "writePermissions")

    def _add_observer_obj(self, parent, obs):
        obj = SubElement(parent, "object")
        obj.set("disabled", "0")
        obj.set("kind", "observer")
        obj.set("name", obs.name)
        props = SubElement(obj, "properties")
        _add_kv(props, "clock",
                obs.clock.clock_ref if obs.clock else "")
        _add_kv(props, "debugOutput", obs.debug_output)
        el = SubElement(props, "entry")
        el.set("key", "errorLoggers")
        _add_kv(el, "0", "#Standard filtering")

    def _add_mode_flag(self, parent, mf):
        obj = SubElement(parent, "object")
        obj.set("disabled", "0")
        obj.set("kind", "modeFlag")
        obj.set("name", mf.name)
        props = SubElement(obj, "properties")
        mpv = SubElement(props, "entry")
        mpv.set("key", "modePortValues")
        _add_kv(mpv, f"(specification:{mf.port_name})",
                str(mf.active_value))

    def _add_user_flag(self, parent, uf):
        obj = SubElement(parent, "object")
        obj.set("disabled", "0")
        obj.set("kind", "userFlag")
        obj.set("name", uf.name)
        SubElement(obj, "properties")

    def _add_power_domain(self, parent, pd):
        obj = SubElement(parent, "object")
        obj.set("disabled", "0")
        obj.set("kind", "power")
        obj.set("name", pd.name)
        props = SubElement(obj, "properties")
        dl = SubElement(props, "entry")
        dl.set("key", "domainLvl")
        if pd.comment:
            _add_kv(dl, "comment", pd.comment)
        _add_kv(dl, "kind", pd.kind)
        # SUPPLY domains need interfaceLvl
        if pd.kind != "ALWAYS_ON":
            il = SubElement(props, "entry")
            il.set("key", "interfaceLvl")
            _add_kv(il, "powerController", "None")
        # Activity zones as child objects
        for az_name in pd.activity_zones:
            az = SubElement(obj, "object")
            az.set("disabled", "0")
            az.set("kind", "activityZone")
            az.set("name", az_name)
            SubElement(az, "properties")

    def _add_voltage(self, parent, v):
        obj = SubElement(parent, "object")
        obj.set("disabled", "0")
        obj.set("kind", "voltage")
        obj.set("name", v.name)
        props = SubElement(obj, "properties")
        if v.comment:
            _add_kv(props, "comment", v.comment)
        _add_kv(props, "value", v.value)

    def _add_clock_regime(self, parent, clk):
        regime = SubElement(parent, "object")
        regime.set("disabled", "0")
        regime.set("kind", "clockRegime")
        regime.set("name", clk.name)
        rprops = SubElement(regime, "properties")
        if clk.comment:
            _add_kv(rprops, "comment", clk.comment)
        _add_kv(rprops, "frequency", str(clk.frequency))
        if clk.voltage_ref:
            _add_kv(rprops, "voltage",
                    f"(specification:{clk.voltage_ref})")

        mgr = SubElement(regime, "object")
        mgr.set("disabled", "0")
        mgr.set("kind", "clockManager")
        mgr.set("name", clk.manager_name)
        mprops = SubElement(mgr, "properties")
        dl = SubElement(mprops, "entry")
        dl.set("key", "domainLvl")
        if clk.power_ref:
            _add_kv(dl, "power",
                    f"(specification:{clk.power_ref})")
        il = SubElement(mprops, "entry")
        il.set("key", "internalLvl")
        ms = SubElement(il, "entry")
        ms.set("key", "mainSignals")
        _add_kv(ms, "resetN", f"(specification:{clk.reset_name})")
        _add_kv(ms, "rootClock", f"(specification:{clk.port_name})")
        _add_kv(ms, "testMode", f"(specification:{clk.test_mode})")

        clock_obj = SubElement(mgr, "object")
        clock_obj.set("disabled", "0")
        clock_obj.set("kind", "clock")
        clock_obj.set("name", clk.clock_name)
        cprops = SubElement(clock_obj, "properties")
        _add_kv(cprops, "type", clk.clock_type)

    def _add_spec_ports(self, parent):
        # Track which ports we've already added
        added = set()

        # Clock ports
        for clk in self.p._clocks:
            if clk.port_name not in added:
                self._add_port(parent, clk.port_name, "Clock")
                added.add(clk.port_name)
            if clk.reset_name not in added:
                self._add_reset_port(parent, clk.reset_name, clk)
                added.add(clk.reset_name)

        # TestMode port (shared across all clocks)
        tm_names = set(clk.test_mode for clk in self.p._clocks)
        for tm in tm_names:
            if tm not in added:
                self._add_port(parent, tm, "TestMode", clock_ref="None")
                added.add(tm)

        # User ports
        for port in self.p._user_ports:
            if port.name not in added:
                self._add_user_port(parent, port)
                added.add(port.name)

        # Mode ports
        for mf in self.p._mode_flags:
            if mf.port_name not in added:
                # Find clock for this mode port
                mode_clk = self.p._clocks[0] if self.p._clocks else None
                port = SubElement(parent, "object")
                port.set("disabled", "0")
                port.set("kind", "port")
                port.set("name", mf.port_name)
                pp = SubElement(port, "properties")
                tp = SubElement(pp, "entry")
                tp.set("key", "type")
                tp.set("value", "Mode")
                _add_kv(tp, "clock",
                        mode_clk.clock_ref if mode_clk else "None")
                _add_kv(tp, "width", "1")
                added.add(mf.port_name)

        # Press port (auto-generated when any initiator uses usePress)
        if any(i.use_press for i in self.p._initiators):
            if "press" not in added:
                press_clk = self.p._clocks[0] if self.p._clocks else None
                port = SubElement(parent, "object")
                port.set("disabled", "0")
                port.set("kind", "port")
                port.set("name", "press")
                pp = SubElement(port, "properties")
                tp = SubElement(pp, "entry")
                tp.set("key", "type")
                tp.set("value", "User")
                _add_kv(tp, "clock",
                        press_clk.clock_ref if press_clk else "None")
                _add_kv(tp, "direction", "Input")
                sim = SubElement(tp, "entry")
                sim.set("key", "simulationModel")
                sim.set("value", "CONSTANT")
                _add_kv(sim, "defaultVal", "0")
                _add_kv(tp, "width",
                        str(self.p._urgency_levels))
                added.add("press")

    def _add_port(self, parent, name, port_type, clock_ref=None):
        port = SubElement(parent, "object")
        port.set("disabled", "0")
        port.set("kind", "port")
        port.set("name", name)
        pp = SubElement(port, "properties")
        tp = SubElement(pp, "entry")
        tp.set("key", "type")
        tp.set("value", port_type)
        if port_type == "TestMode":
            _add_kv(tp, "clock", "None")
        elif clock_ref:
            _add_kv(tp, "clock", clock_ref)

    def _add_reset_port(self, parent, name, clk):
        port = SubElement(parent, "object")
        port.set("disabled", "0")
        port.set("kind", "port")
        port.set("name", name)
        pp = SubElement(port, "properties")
        tp = SubElement(pp, "entry")
        tp.set("key", "type")
        tp.set("value", "ResetN")
        da = SubElement(tp, "entry")
        da.set("key", "deassertion")
        da.set("value", "Deassertion on edge of")
        _add_kv(da, "clock", clk.clock_ref)

    def _add_user_port(self, parent, port_def):
        port = SubElement(parent, "object")
        port.set("disabled", "0")
        port.set("kind", "port")
        port.set("name", port_def.name)
        pp = SubElement(port, "properties")
        tp = SubElement(pp, "entry")
        tp.set("key", "type")
        tp.set("value", "User")
        _add_kv(tp, "clock", port_def.clock_ref or "None")
        if port_def.direction:
            _add_kv(tp, "direction", port_def.direction)
        if port_def.width > 1:
            _add_kv(tp, "width", str(port_def.width))
        if port_def.default_val is not None:
            sim = SubElement(tp, "entry")
            sim.set("key", "simulationModel")
            sim.set("value", "CONSTANT")
            _add_kv(sim, "defaultVal", str(port_def.default_val))

    # ---- Export ----

    def _add_export_folder(self, root):
        folder = SubElement(root, "object")
        folder.set("disabled", "0")
        folder.set("kind", "folder")
        folder.set("name", "exports")
        SubElement(folder, "properties")

    def _add_export_option(self, root):
        exports = self.p._exports if self.p._exports else (
            [self.p._export] if self.p._export else [])
        for exp in exports:
            if not exp:
                continue
            obj = SubElement(root, "object")
            obj.set("disabled", "0")
            obj.set("kind", "exportOption")
            obj.set("name", exp["name"])
            props = SubElement(obj, "properties")
            eo = SubElement(props, "entry")
            eo.set("key", "exportOption")
            eo.set("value", exp["format"])
            # customerCells
            cells = exp.get("customer_cells", {})
            if cells:
                cc = SubElement(eo, "entry")
                cc.set("key", "customerCells")
                for cell_name, path in cells.items():
                    ce = SubElement(cc, "entry")
                    ce.set("key", cell_name)
                    syn = SubElement(ce, "entry")
                    syn.set("key", "synthesis")
                    _add_kv(syn, "descriptionPath", f"#{path}")
            # files
            if exp.get("files"):
                _add_kv(eo, "files", exp["files"])
            # simulator
            if exp.get("simulator"):
                _add_kv(eo, "simulator", exp["simulator"])
            # synthesisTool
            if exp.get("synthesis_tool"):
                _add_kv(eo, "synthesisTool", exp["synthesis_tool"])


# ---- Helpers ----

def _add_kv(parent, key, value):
    e = SubElement(parent, "entry")
    e.set("key", key)
    e.set("value", value)
    return e


def _add_empty_entry(parent, key):
    e = SubElement(parent, "entry")
    e.set("key", key)
    return e
