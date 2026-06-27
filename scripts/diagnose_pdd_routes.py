#!/usr/bin/env python3
"""Diagnose FlexNoC PDD specification connectivity vs architecture routes."""

import argparse
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple


def _strip_ref(value: str, prefix: str) -> str:
    if not value:
        return value
    head = f"({prefix}:"
    if value.startswith(head) and value.endswith(")"):
        return value[len(head):-1]
    return value


def _node_name(value: str) -> str:
    if not value:
        return value
    if value.startswith("(switchBasedArchitecture:") and value.endswith(")"):
        return value[len("(switchBasedArchitecture:"):-1]
    return value


def _load_spec_connectivity(root) -> Dict[Tuple[str, str], bool]:
    spec = root.find("./object[@kind='specification']")
    if spec is None:
        return {}
    conn = spec.find("./properties/entry[@key='connectivity']")
    if conn is None:
        return {}

    result = {}
    for init_entry in conn.findall("./entry"):
        init_ref = _strip_ref(init_entry.get("key", ""), "specification")
        for targ_entry in init_entry.findall("./entry"):
            targ_ref = _strip_ref(targ_entry.get("key", ""), "specification")
            result[(init_ref, targ_ref)] = targ_entry.get("value") == "True"
    return result


def _load_arch_routes(root):
    arch = root.find("./object[@kind='switchBasedArchitecture']")
    if arch is None:
        return [], Counter(), set(), set()

    route_entry = arch.find("./properties/entry[@key='datapathRoute']")
    routes: List[Tuple[str, str]] = []
    used_nodes = Counter()
    if route_entry is not None:
        for init_entry in route_entry.findall("./entry"):
            init_ref = _strip_ref(init_entry.get("key", ""), "switchBasedArchitecture")
            for targ_entry in init_entry.findall("./entry"):
                targ_ref = _strip_ref(targ_entry.get("key", ""), "switchBasedArchitecture")
                routes.append((init_ref, targ_ref))
                for path_name in ("requestPath", "responsePath"):
                    path_entry = targ_entry.find(f"./entry[@key='{path_name}']")
                    if path_entry is None:
                        continue
                    for step in path_entry.findall("./entry"):
                        used_nodes[_node_name(step.get("value", ""))] += 1

    arch_nodes = {
        obj.get("name")
        for obj in arch.findall("./object")
        if obj.get("kind") in {"dtpSwitch", "dtpLink"} and obj.get("name")
    }
    struct = root.find("./object[@kind='switchBasedStructure']")
    struct_nodes = set()
    if struct is not None:
        struct_nodes = {
            shadow.get("name")
            for shadow in struct.findall("./shadow")
            if shadow.get("name")
        }

    return routes, used_nodes, arch_nodes, struct_nodes


def diagnose(pdd_path: Path) -> int:
    root = ET.parse(pdd_path).getroot()
    connectivity = _load_spec_connectivity(root)
    routes, used_nodes, arch_nodes, struct_nodes = _load_arch_routes(root)

    stale_routes = []
    missing_connectivity = []
    for init_ref, targ_ref in routes:
        key = (init_ref, targ_ref)
        if key not in connectivity:
            missing_connectivity.append((init_ref, targ_ref))
        elif not connectivity[key]:
            stale_routes.append((init_ref, targ_ref))

    unused_nodes = sorted(node for node in arch_nodes if used_nodes[node] == 0)
    missing_struct_shadows = sorted(node for node in arch_nodes if node not in struct_nodes)

    print(f"PDD: {pdd_path}")
    print(f"spec_connectivity_entries: {len(connectivity)}")
    print(f"architecture_datapath_routes: {len(routes)}")
    print(f"architecture_nodes: {len(arch_nodes)}")
    print()

    if stale_routes:
        print("STALE_ROUTES:")
        for init_ref, targ_ref in stale_routes:
            print(f"  {init_ref} -> {targ_ref} is False in specification connectivity")
    else:
        print("STALE_ROUTES: none")

    if missing_connectivity:
        print("MISSING_CONNECTIVITY_ENTRIES:")
        for init_ref, targ_ref in missing_connectivity:
            print(f"  {init_ref} -> {targ_ref}")
    else:
        print("MISSING_CONNECTIVITY_ENTRIES: none")

    if unused_nodes:
        print("UNUSED_ARCH_NODES:")
        for node in unused_nodes:
            print(f"  {node}")
    else:
        print("UNUSED_ARCH_NODES: none")

    if missing_struct_shadows:
        print("MISSING_STRUCTURE_SHADOWS:")
        for node in missing_struct_shadows:
            print(f"  {node}")
    else:
        print("MISSING_STRUCTURE_SHADOWS: none")

    return 1 if (stale_routes or missing_connectivity or unused_nodes or missing_struct_shadows) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdd", type=Path, help="FlexNoC PDD file")
    args = parser.parse_args()
    return diagnose(args.pdd)


if __name__ == "__main__":
    sys.exit(main())
