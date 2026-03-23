"""pytest configuration — fixtures for PDD generation and Docker E2E tests."""

import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

# Ensure flexnoc_dsl is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flexnoc_dsl import (
    NocProject, AXI, APB, OCP, AHB, AXI_Lite, ACE_Lite,
    PowerDomain, Voltage,
)

# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line("markers", "docker: E2E tests requiring FlexNoC Docker image")


# ---------------------------------------------------------------------------
# PDD helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def pdd_dir(tmp_path):
    """Provide a temp directory for PDD output."""
    return tmp_path


def parse_pdd(path: str) -> ET.Element:
    """Parse a PDD file and return the root element."""
    tree = ET.parse(path)
    return tree.getroot()


def find_objects(root: ET.Element, kind: str, name: str = None):
    """Find <object> elements by kind (and optionally name)."""
    results = []
    for obj in root.iter("object"):
        if obj.get("kind") == kind:
            if name is None or obj.get("name") == name:
                results.append(obj)
    return results


def find_entry(element: ET.Element, key: str) -> ET.Element:
    """Find a direct-child <entry> with given key. Returns None if not found."""
    for entry in element.iter("entry"):
        if entry.get("key") == key:
            return entry
    return None


def get_entry_value(element: ET.Element, key: str) -> str:
    """Get the value attribute of an entry with given key. Returns None if not found."""
    entry = find_entry(element, key)
    if entry is not None:
        return entry.get("value")
    return None


def assert_pdd_valid(path: str):
    """Basic structural validation of PDD XML."""
    root = parse_pdd(path)
    assert root.tag == "object"
    assert root.get("kind") == "project"
    # Must have at least one protocol, architecture, structure, specification
    kinds = {obj.get("kind") for obj in root.findall("object")}
    assert "protocol" in kinds, "PDD missing protocol object"
    assert "switchBasedArchitecture" in kinds, "PDD missing architecture"
    assert "switchBasedStructure" in kinds, "PDD missing structure"
    assert "specification" in kinds, "PDD missing specification"


# ---------------------------------------------------------------------------
# Minimal NoC helpers (reusable across tests)
# ---------------------------------------------------------------------------

@pytest.fixture
def basic_noc():
    """Create a minimal NocProject with AXI protocol and single clock."""
    def _make(name="test_noc", addr=32, data=64, id_width=4, freq="500MHz"):
        noc = NocProject(name)
        axi = noc.add_protocol("AXI_prot", AXI(addr=addr, data=data, id=id_width))
        clk = noc.add_clock("clk", freq=freq, port="clk", reset="rst_n")
        return noc, axi, clk
    return _make


@pytest.fixture
def simple_2x2(basic_noc, pdd_dir):
    """Generate a simple 2-init, 2-target AXI crossbar and return (noc, pdd_path)."""
    noc, axi, clk = basic_noc()
    noc.add_initiator("init_0", protocol=axi, clock=clk)
    noc.add_initiator("init_1", protocol=axi, clock=clk)
    noc.add_target("targ_0", protocol=axi, clock=clk, base=0x0, size="256M")
    noc.add_target("targ_1", protocol=axi, clock=clk, base=0x10000000, size="256M")
    noc.connect_all()
    noc.set_export("Verilog", simulator="VCS")
    pdd_path = str(pdd_dir / "simple_2x2.pdd")
    noc.write_pdd(pdd_path)
    return noc, pdd_path


# ---------------------------------------------------------------------------
# Docker E2E fixture
# ---------------------------------------------------------------------------

FLEXNOC_WORK = os.path.expanduser("~/flexnoc-work")

DOCKER_SETUP = (
    "ip link set eth0 down; "
    "ip link set eth0 name xp0; "
    "ip link set xp0 address 00:21:5a:45:ac:60; "
    "ip link set xp0 up; "
    "cd /opt/arteris/License && rm -f run/*.pid && bash arteris start 2>/dev/null && sleep 5; "
    "Xvfb :99 -screen 0 1024x768x24 & sleep 2; "
    "export DISPLAY=:99; "
    "source /opt/flexnoc/5.3.0/etc/bashrc; "
    'export LD_LIBRARY_PATH="/opt/flexnoc/5.3.0/TopologyEditor/lib:$LD_LIBRARY_PATH"; '
)


@pytest.fixture
def docker_runner():
    """Fixture returning a function that runs FlexNoC export inside Docker.

    Usage:
        result = docker_runner(pdd_path, struct_name, export_name, output_subdir)
        assert result.returncode == 0
    """
    def _run(pdd_path: str, struct_name: str, export_name: str = "exports.Vlog",
             output_subdir: str = "test_output", timeout: int = 300):
        # Copy PDD into flexnoc-work so Docker can access it
        pdd_basename = os.path.basename(pdd_path)
        dst = os.path.join(FLEXNOC_WORK, pdd_basename)
        shutil.copy2(pdd_path, dst)

        output_dir = os.path.join(FLEXNOC_WORK, output_subdir)
        os.makedirs(output_dir, exist_ok=True)

        flexnoc_cmd = (
            f"FlexNoC -d False -p /work/{pdd_basename} exportVerilog "
            f"-s {struct_name} -c {export_name} -o /work/{output_subdir}"
        )

        docker_cmd = [
            "docker", "run", "--rm",
            "--hostname", "YunqiLaptop",
            "--cap-add", "NET_ADMIN",
            "--entrypoint", "bash",
            "-v", f"{FLEXNOC_WORK}:/work",
            "flexnoc:5.3.0-standalone",
            "-c", DOCKER_SETUP + flexnoc_cmd,
        ]

        result = subprocess.run(
            docker_cmd, capture_output=True, text=True, timeout=timeout,
        )

        # Cleanup PDD copy
        if os.path.exists(dst):
            os.remove(dst)

        return result

    return _run


@pytest.fixture
def docker_output_dir():
    """Return path and cleanup helper for docker output."""
    subdir = f"pytest_output_{os.getpid()}"
    path = os.path.join(FLEXNOC_WORK, subdir)
    os.makedirs(path, exist_ok=True)
    yield path, subdir
    # Cleanup after test
    if os.path.exists(path):
        shutil.rmtree(path)
