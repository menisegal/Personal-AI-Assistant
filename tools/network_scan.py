"""Home network/hardware discovery tools: LAN devices, Bluetooth/BLE, and mDNS.

Discovery only — nothing here controls, pairs with, or connects to any
device. Intended to run on the Raspberry Pi itself, using whatever Wi-Fi/LAN
and Bluetooth hardware it's physically attached to.
"""

import asyncio
import ipaddress
import re
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from langchain_core.tools import tool

PING_TIMEOUT_SEC = 1
PING_WORKERS = 64
BLE_SCAN_TIMEOUT_SEC = 8.0
MDNS_SCAN_TIMEOUT_SEC = 5.0


def _get_local_ip() -> str:
    """Best-effort local IP address (doesn't actually send any data)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def _ping(ip: str) -> None:
    """Ping once, just to populate the OS's ARP/neighbor table. Ignores the result."""
    if sys.platform == "win32":
        cmd = ["ping", "-n", "1", "-w", str(PING_TIMEOUT_SEC * 1000), str(ip)]
    else:
        cmd = ["ping", "-c", "1", "-W", str(PING_TIMEOUT_SEC), str(ip)]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=PING_TIMEOUT_SEC + 2)
    except Exception:
        pass


def _read_neighbor_table() -> dict[str, str]:
    """Return {ip: mac} from the OS neighbor/ARP table (Linux `ip neigh`, else `arp -a`)."""
    mapping: dict[str, str] = {}
    try:
        output = subprocess.run(["ip", "neigh", "show"], capture_output=True, text=True,
                                 timeout=5).stdout
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 5 and "lladdr" in parts:
                ip = parts[0]
                mac = parts[parts.index("lladdr") + 1]
                mapping[ip] = mac
        if mapping:
            return mapping
    except Exception:
        pass

    try:
        output = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=5).stdout
        mac_re = r"([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}"
        for line in output.splitlines():
            ip_match = re.search(r"\d+\.\d+\.\d+\.\d+", line)
            mac_match = re.search(mac_re, line)
            if ip_match and mac_match:
                mapping[ip_match.group(0)] = mac_match.group(0)
    except Exception:
        pass

    return mapping


def _resolve_hostname(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""


@tool
def scan_lan_devices() -> str:
    """Scan the local home network (Wi-Fi/LAN) for active devices.

    Pings every address in the local /24 subnet, then reads the resulting
    ARP/neighbor table to list which devices responded, with their IP, MAC
    address, and hostname when resolvable. Discovery only — this does not
    control or identify the exact type of any device, and takes ~10-30
    seconds to finish.
    """
    try:
        local_ip = _get_local_ip()
        network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
    except Exception as e:
        return f"Could not determine the local network: {e}"

    hosts = [str(ip) for ip in network.hosts()]

    with ThreadPoolExecutor(max_workers=PING_WORKERS) as executor:
        list(executor.map(_ping, hosts))

    neighbors = _read_neighbor_table()
    neighbors = {
        ip: mac for ip, mac in neighbors.items()
        if mac.lower().replace("-", ":") != "ff:ff:ff:ff:ff:ff"
        and not ipaddress.ip_address(ip).is_multicast
        and ip != str(network.broadcast_address)
    }
    if not neighbors:
        return f"Pinged {len(hosts)} addresses on {network}, but couldn't read the ARP/neighbor table."

    lines = [f"Found {len(neighbors)} device(s) on {network}:"]
    for ip, mac in sorted(neighbors.items(), key=lambda kv: tuple(int(p) for p in kv[0].split("."))):
        hostname = _resolve_hostname(ip)
        who = f" ({hostname})" if hostname else ""
        lines.append(f"- {ip}{who} — {mac}")
    return "\n".join(lines)


@tool
def scan_bluetooth_devices() -> str:
    """Scan for nearby Bluetooth/BLE devices.

    Listens for BLE advertisements for a few seconds using the device's
    Bluetooth radio. Returns each device's address and name (if advertised).
    Discovery only — does not pair or connect to anything.
    """
    try:
        from bleak import BleakScanner
    except ImportError:
        return "bleak is not installed — Bluetooth scanning is unavailable."

    async def _scan():
        return await BleakScanner.discover(timeout=BLE_SCAN_TIMEOUT_SEC)

    try:
        devices = asyncio.run(_scan())
    except Exception as e:
        return f"Bluetooth scan failed: {e}"

    if not devices:
        return "No nearby Bluetooth devices found."

    lines = [f"Found {len(devices)} Bluetooth device(s):"]
    for d in devices:
        lines.append(f"- {d.name or 'Unknown'} ({d.address})")
    return "\n".join(lines)


@tool
def scan_mdns_devices() -> str:
    """Scan for smart-home devices announcing themselves via mDNS/Bonjour.

    Many smart TVs, Chromecasts, printers, speakers, and other smart-home
    devices advertise themselves this way. Discovery only — does not control
    or connect to any device. Takes a few seconds to finish.
    """
    try:
        from zeroconf import Zeroconf, ServiceBrowser, ZeroconfServiceTypes
    except ImportError:
        return "zeroconf is not installed — mDNS scanning is unavailable."

    zc = Zeroconf()
    found = []

    class _Listener:
        def add_service(self, zeroconf, service_type, name):
            info = zeroconf.get_service_info(service_type, name, timeout=1000)
            addresses = info.parsed_addresses() if info else []
            found.append((name, service_type, addresses[0] if addresses else ""))

        def remove_service(self, zeroconf, service_type, name):
            pass

        def update_service(self, zeroconf, service_type, name):
            pass

    try:
        service_types = ZeroconfServiceTypes.find(zc=zc, timeout=MDNS_SCAN_TIMEOUT_SEC)
        browsers = [ServiceBrowser(zc, st, _Listener()) for st in service_types]
        time.sleep(MDNS_SCAN_TIMEOUT_SEC)
    except Exception as e:
        return f"mDNS scan failed: {e}"
    finally:
        zc.close()

    if not found:
        return "No mDNS-announcing devices found."

    lines = [f"Found {len(found)} mDNS device(s):"]
    for name, service_type, addr in found:
        lines.append(f"- {name} [{service_type}]" + (f" @ {addr}" if addr else ""))
    return "\n".join(lines)
