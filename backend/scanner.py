import socket
import concurrent.futures
import time
from typing import List, Tuple, Generator, Dict, Any
from urllib.parse import urlparse

from models import PortResult

CONNECT_TIMEOUT = 1.0
BANNER_TIMEOUT = 2.0
MAX_WORKERS = 200
BATCH_SIZE = 50


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
        futures = {
            executor.submit(scan_port, resolved_ip, port): port for port in ports
        }
        results: List[PortResult] = []
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    duration = time.perf_counter() - start_time
    results.sort(key=lambda r: r.port)
    return resolved_ip, results, round(duration, 4)


def scan_ports_batched(
    target: str,
    start_port: int,
    end_port: int,
    batch_size: int = BATCH_SIZE,
) -> Generator[Dict[str, Any], None, None]:
    """
    Scan a range of TCP ports in batches, yielding progress after each batch.

    Yields:
        dict with keys:
            - type: "start" | "batch" | "complete"
            - For "start": resolved_ip, total_ports, batch_size
            - For "batch": batch_number, ports_scanned, results, batch_duration, throughput
            - For "complete": total_duration, total_scanned, open_ports, all_results
    """
    resolved_ip = resolve_target(target)
    all_ports = list(range(start_port, end_port + 1))
    total_ports = len(all_ports)

    yield {
        "type": "start",
        "resolved_ip": resolved_ip,
        "target": target,
        "total_ports": total_ports,
        "batch_size": batch_size,
        "start_port": start_port,
        "end_port": end_port,
    }

    all_results: List[PortResult] = []
    scan_start_time = time.perf_counter()
    batch_number = 0

    for i in range(0, total_ports, batch_size):
        batch_ports = all_ports[i : i + batch_size]
        batch_start_time = time.perf_counter()
        batch_number += 1

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(MAX_WORKERS, len(batch_ports))
        ) as executor:
            futures = {
                executor.submit(scan_port, resolved_ip, port): port
                for port in batch_ports
            }
            batch_results: List[PortResult] = []
            for future in concurrent.futures.as_completed(futures):
                batch_results.append(future.result())

        batch_results.sort(key=lambda r: r.port)
        all_results.extend(batch_results)

        batch_duration = time.perf_counter() - batch_start_time
        throughput = len(batch_ports) / batch_duration if batch_duration > 0 else 0

        yield {
            "type": "batch",
            "batch_number": batch_number,
            "ports_scanned": len(batch_ports),
            "ports_scanned_total": len(all_results),
            "results": [r.model_dump() for r in batch_results],
            "batch_duration": round(batch_duration, 4),
            "throughput": round(throughput, 2),
            "progress_percent": round((len(all_results) / total_ports) * 100, 1),
        }

    total_duration = time.perf_counter() - scan_start_time
    all_results.sort(key=lambda r: r.port)
    open_count = sum(1 for r in all_results if r.status == "open")

    yield {
        "type": "complete",
        "total_duration": round(total_duration, 4),
        "total_scanned": len(all_results),
        "open_ports": open_count,
    }
