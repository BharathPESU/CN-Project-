import socket
import concurrent.futures
import time
from typing import List, Tuple
from urllib.parse import urlparse

from models import PortResult

# Timeout (seconds) for each connection attempt
CONNECT_TIMEOUT = 1.0
# Timeout (seconds) for banner grabbing after a successful connection
BANNER_TIMEOUT = 2.0
# Max worker threads for concurrent scanning
MAX_WORKERS = 200


def normalize_target(target: str) -> str:
        """
        Normalize user-entered target values into a hostname/IP string.

        Accepts values like:
            - 192.168.1.10
            - laptop.local
            - 192.168.1.10:22
            - http://192.168.1.10:8000

        Returns:
            Hostname/IP only (without scheme, path, or port).
        """
        cleaned = (target or "").strip()
        if not cleaned:
                raise ValueError("Target cannot be empty.")

        parsed = urlparse(cleaned if "://" in cleaned else f"//{cleaned}")
        host = parsed.hostname or cleaned

        if not host:
                raise ValueError(f"Invalid target '{target}'.")

        return host.strip()


def resolve_target(target: str) -> str:
    """
    Resolve a hostname or IP string to a dotted-decimal IP address.
    Raises ValueError if the target cannot be resolved.
    """
    normalized_target = normalize_target(target)
    try:
        return socket.gethostbyname(normalized_target)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve target '{target}': {exc}") from exc


def get_service_name(port: int) -> str:
    """
    Return the well-known service name for a port, or 'unknown' if not found.
    """
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return "unknown"


def grab_banner(ip: str, port: int) -> str | None:
    """
    Attempt to receive a banner string from an open port.
    Returns the decoded banner on success, or None if nothing is received.
    """
    try:
        with socket.create_connection((ip, port), timeout=BANNER_TIMEOUT) as sock:
            # Some services (e.g. HTTP) require a nudge before sending a banner
            try:
                sock.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
            except OSError:
                pass
            raw = sock.recv(1024)
            return raw.decode(errors="replace").strip() or None
    except OSError:
        return None


def scan_port(ip: str, port: int) -> PortResult:
    """
    Scan a single TCP port on *ip*.
    Returns a PortResult with status, service name, and optional banner.
    """
    try:
        with socket.create_connection((ip, port), timeout=CONNECT_TIMEOUT):
            service = get_service_name(port)
            banner = grab_banner(ip, port)
            return PortResult(port=port, status="open", service=service, banner=banner)
    except (ConnectionRefusedError, socket.timeout, OSError):
        service = get_service_name(port)
        return PortResult(port=port, status="closed", service=service, banner=None)


def scan_ports(
    target: str,
    start_port: int,
    end_port: int,
) -> Tuple[str, List[PortResult], float]:
    """
    Scan a range of TCP ports on *target* concurrently.

    Returns:
        resolved_ip  – the dotted-decimal IP that was actually scanned
        results      – list of PortResult sorted by port number
        duration     – wall-clock scan time in seconds
    """
    resolved_ip = resolve_target(target)
    ports = range(start_port, end_port + 1)

    start_time = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(scan_port, resolved_ip, port): port for port in ports}
        results: List[PortResult] = []
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    duration = time.perf_counter() - start_time
    results.sort(key=lambda r: r.port)
    return resolved_ip, results, round(duration, 4)
