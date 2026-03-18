"""
port_scanner.py
---------------
A concurrent TCP port scanner built on Python's built-in socket library
and ThreadPoolExecutor for high-throughput scanning.

Public API
~~~~~~~~~~
    scan_ports(target, start_port, end_port, max_workers=100) -> list[dict]

Each returned dict has the shape:
    {
        "port":    <int>        – the port number,
        "status":  <str>        – "open" or "closed",
        "service": <str>        – well-known service name, or "Unknown",
        "banner":  <str|None>   – first 1024 bytes received from the port,
                                   decoded to str, or None if unavailable
    }

Concurrency model
~~~~~~~~~~~~~~~~~
Each port probe runs in its own thread.  Up to MAX_WORKERS threads execute
simultaneously, so the total wall-clock time is roughly:

    ceil(num_ports / MAX_WORKERS) × CONNECTION_TIMEOUT   (worst case)

Results are always returned sorted by port number regardless of the order
in which threads finish.
"""

import socket
import concurrent.futures
from typing import List, Dict

# ── Constants ──────────────────────────────────────────────────────────────────

# How long (seconds) to wait for a TCP handshake before giving up.
CONNECTION_TIMEOUT: float = 1.0

# How long (seconds) to wait for banner data after a successful connection.
# Kept shorter than CONNECTION_TIMEOUT so slow banners don't stall the scan.
BANNER_TIMEOUT: float = 2.0

# Maximum number of bytes to read from a banner response.
BANNER_MAX_BYTES: int = 1024

# Maximum number of threads scanning in parallel.
# Raising this value speeds up large scans but increases resource usage.
MAX_WORKERS: int = 100

# ── Well-known service registry ────────────────────────────────────────────────
# Maps TCP port numbers to their conventional service names.
# Used by _lookup_service() to annotate scan results.
WELL_KNOWN_SERVICES: Dict[int, str] = {
    # ── File Transfer ──────────────────────────────────────────────────────────
    20:    "FTP Data",
    21:    "FTP Control",
    # ── Remote Access ──────────────────────────────────────────────────────────
    22:    "SSH",
    23:    "Telnet",
    # ── Email ──────────────────────────────────────────────────────────────────
    25:    "SMTP",
    110:   "POP3",
    143:   "IMAP",
    465:   "SMTPS",
    587:   "SMTP Submission",
    993:   "IMAPS",
    995:   "POP3S",
    # ── Web ────────────────────────────────────────────────────────────────────
    80:    "HTTP",
    443:   "HTTPS",
    8080:  "HTTP Alternate",
    8443:  "HTTPS Alternate",
    # ── DNS & Directory ────────────────────────────────────────────────────────
    53:    "DNS",
    389:   "LDAP",
    636:   "LDAPS",
    # ── Network Services ───────────────────────────────────────────────────────
    67:    "DHCP Server",
    68:    "DHCP Client",
    69:    "TFTP",
    123:   "NTP",
    161:   "SNMP",
    162:   "SNMP Trap",
    # ── File Sharing ───────────────────────────────────────────────────────────
    139:   "NetBIOS Session",
    445:   "SMB",
    2049:  "NFS",
    # ── Databases ──────────────────────────────────────────────────────────────
    1433:  "MSSQL",
    1521:  "Oracle DB",
    3306:  "MySQL",
    5432:  "PostgreSQL",
    6379:  "Redis",
    27017: "MongoDB",
    # ── Remote Desktop & VNC ──────────────────────────────────────────────────
    3389:  "RDP",
    5900:  "VNC",
    5901:  "VNC-1",
    # ── Messaging & Streaming ──────────────────────────────────────────────────
    1883:  "MQTT",
    5672:  "AMQP (RabbitMQ)",
    9092:  "Kafka",
    # ── Proxies & Tunnels ──────────────────────────────────────────────────────
    1080:  "SOCKS Proxy",
    3128:  "HTTP Proxy (Squid)",
    # ── Misc / Developer ──────────────────────────────────────────────────────
    179:   "BGP",
    194:   "IRC",
    5000:  "Flask / UPnP",
    6000:  "X11",
    8888:  "Jupyter Notebook",
    9200:  "Elasticsearch HTTP",
    9300:  "Elasticsearch Transport",
}


# ── Core helpers ───────────────────────────────────────────────────────────────

def _resolve_target(target: str) -> str:
    """
    Resolve a hostname or dotted-decimal IP string to an IP address.

    Parameters
    ----------
    target : str
        A domain name (e.g. "example.com") or an IPv4/IPv6 address string.

    Returns
    -------
    str
        The resolved IP address as a string.

    Raises
    ------
    ValueError
        If the hostname cannot be resolved.
    """
    try:
        return socket.gethostbyname(target)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve target '{target}': {exc}") from exc


def _lookup_service(port: int) -> str:
    """
    Return the well-known service name for *port*, or ``"Unknown"``.

    Looks up the port in the module-level ``WELL_KNOWN_SERVICES`` dictionary
    first.  Falls back to Python's ``socket.getservbyport()`` for any port
    not explicitly listed there, and finally returns ``"Unknown"`` if neither
    source recognises the port.

    Parameters
    ----------
    port : int
        TCP port number to look up.

    Returns
    -------
    str
        Human-readable service name (e.g. ``"HTTP"``, ``"SSH"``) or
        ``"Unknown"``.
    """
    # Primary lookup – our curated dictionary with friendly names.
    if port in WELL_KNOWN_SERVICES:
        return WELL_KNOWN_SERVICES[port]

    # Secondary lookup – OS-level services database (/etc/services on Unix).
    try:
        return socket.getservbyport(port, "tcp").upper()
    except OSError:
        return "Unknown"


def _grab_banner(sock: socket.socket) -> str | None:
    """
    Attempt to read a banner from an already-connected socket.

    Many services (SSH, FTP, SMTP, POP3, IMAP) push a greeting banner
    immediately upon connection.  HTTP-like services are silent until they
    receive a request, so a minimal ``HEAD`` probe is sent first.

    The socket's timeout is temporarily changed to ``BANNER_TIMEOUT`` so
    the caller isn't blocked for longer than necessary.

    Parameters
    ----------
    sock : socket.socket
        A connected TCP socket.  The caller retains ownership; this function
        does **not** close it.

    Returns
    -------
    str or None
        The decoded banner string (whitespace-stripped), or ``None`` if no
        data was received or an error occurred.
    """
    try:
        # Some services only respond after receiving a request (e.g. HTTP).
        # Sending a lightweight HEAD request encourages them to reply.
        # Services that don't expect input will simply ignore it.
        try:
            sock.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
        except OSError:
            # The service may not accept inbound data before sending its own
            # greeting (e.g. SSH); ignore the send error and try recv anyway.
            pass

        # Switch to the banner-specific timeout before blocking on recv.
        sock.settimeout(BANNER_TIMEOUT)

        # Receive up to BANNER_MAX_BYTES of banner data.
        raw: bytes = sock.recv(BANNER_MAX_BYTES)

        if not raw:
            return None

        # Decode with errors="replace" so non-UTF-8 bytes (common in older
        # protocol banners) never cause a UnicodeDecodeError crash.
        return raw.decode(errors="replace").strip() or None

    except OSError:
        # Covers socket.timeout, ConnectionResetError, and other I/O errors.
        return None


def _probe_port(ip: str, port: int) -> Dict[str, object]:
    """
    Attempt a TCP connection to *ip*:*port*, grab the banner if open, and
    return a result dict.

    This function is designed to be called from worker threads inside a
    ``ThreadPoolExecutor``.  It is fully self-contained and thread-safe:
    every call creates and closes its own socket, and all exceptions are
    caught internally so that a single failing thread never aborts the scan.

    Parameters
    ----------
    ip : str
        Resolved IP address of the target host.
    port : int
        TCP port number to probe (1–65535).

    Returns
    -------
    dict
        ``{"port": <int>, "status": "open"|"closed",
           "service": <str>, "banner": <str|None>}``
    """
    status = "closed"
    banner: str | None = None

    try:
        # AF_INET  → IPv4 address family
        # SOCK_STREAM → TCP (connection-oriented) socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            # Set the initial handshake timeout.
            sock.settimeout(CONNECTION_TIMEOUT)

            # connect_ex returns 0 on success; non-zero errno on failure.
            # Unlike connect(), it never raises on a refused connection.
            result_code = sock.connect_ex((ip, port))

            if result_code == 0:
                status = "open"
                # Reuse the same connected socket for banner grabbing so we
                # avoid a second TCP handshake on the open port.
                banner = _grab_banner(sock)
            # else: port is closed/filtered – banner stays None.

    except OSError:
        # Catch unexpected socket-level errors (e.g. network unreachable,
        # too many open files) so this thread always returns a safe result.
        status = "closed"

    # Resolve service name for every port so the result dict is always uniform.
    service = _lookup_service(port)

    return {"port": port, "status": status, "service": service, "banner": banner}


# ── Public API ─────────────────────────────────────────────────────────────────

def scan_ports(
    target: str,
    start_port: int,
    end_port: int,
    max_workers: int = MAX_WORKERS,
) -> List[Dict[str, object]]:
    """
    Concurrently scan TCP ports in the inclusive range [start_port, end_port]
    on *target* using a thread pool.

    Up to *max_workers* ports are probed simultaneously.  Each thread runs
    ``_probe_port`` independently; results are collected safely via
    ``Future.result()`` after all threads finish, then sorted by port number.

    Parameters
    ----------
    target : str
        IPv4 address or hostname to scan (e.g. ``"192.168.1.1"`` or
        ``"example.com"``).
    start_port : int
        First port in the range to scan (1–65535).
    end_port : int
        Last port in the range to scan (1–65535, must be ≥ start_port).
    max_workers : int, optional
        Maximum number of concurrent threads (default: ``MAX_WORKERS = 100``).
        Increase for faster scans on well-resourced machines; decrease to
        reduce load on the target or local OS.

    Returns
    -------
    list[dict]
        A list of result dicts – one per port – sorted by port number.
        Each dict contains:

        * ``"port"``    (int)       – the port number
        * ``"status"``  (str)       – ``"open"`` or ``"closed"``
        * ``"service"`` (str)       – well-known service name, or ``"Unknown"``
        * ``"banner"``  (str|None)  – banner text from the port, or ``None``

    Raises
    ------
    ValueError
        * If *target* cannot be resolved.
        * If the port range is logically invalid.

    Examples
    --------
    >>> results = scan_ports("127.0.0.1", 20, 25)
    >>> for r in results:
    ...     print(r["port"], r["status"])
    20 closed
    21 closed
    22 open
    ...
    """
    # ── Input validation ───────────────────────────────────────────────────────
    if not (1 <= start_port <= 65535):
        raise ValueError(f"start_port must be between 1 and 65535, got {start_port}.")
    if not (1 <= end_port <= 65535):
        raise ValueError(f"end_port must be between 1 and 65535, got {end_port}.")
    if end_port < start_port:
        raise ValueError(
            f"end_port ({end_port}) must be >= start_port ({start_port})."
        )
    if max_workers < 1:
        raise ValueError(f"max_workers must be at least 1, got {max_workers}.")

    # ── Resolve hostname once so every thread reuses the same IP ───────────────
    ip = _resolve_target(target)

    ports = range(start_port, end_port + 1)

    # ── Concurrent scan ────────────────────────────────────────────────────────
    # ThreadPoolExecutor manages a pool of up to max_workers threads.
    # submit() schedules _probe_port(ip, port) for each port and immediately
    # returns a Future without blocking.  We keep a mapping of Future → port
    # so we can associate each result back to its port if needed.
    results: List[Dict[str, object]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all probe tasks to the thread pool up-front.
        future_to_port = {
            executor.submit(_probe_port, ip, port): port for port in ports
        }

        # as_completed() yields each Future as soon as its thread finishes,
        # regardless of submission order – this is safe because _probe_port
        # catches all exceptions internally and always returns a dict.
        for future in concurrent.futures.as_completed(future_to_port):
            results.append(future.result())

    # Sort by port number so the caller always receives an ordered list,
    # independent of which thread finished first.
    results.sort(key=lambda r: r["port"])
    return results


# ── CLI entry-point ────────────────────────────────────────────────────────────

def _print_results(results: List[Dict[str, object]]) -> None:
    """Pretty-print scan results to stdout, including service names and banners."""
    open_ports = [r for r in results if r["status"] == "open"]
    closed_ports = [r for r in results if r["status"] == "closed"]

    print(f"\n{'Port':<10} {'Status':<10} {'Service':<25} Banner")
    print("-" * 80)
    for r in results:
        # Truncate long banners to keep the table readable; replace newlines
        # with spaces so the output stays single-line per port.
        raw_banner: str | None = r.get("banner")  # type: ignore[assignment]
        if raw_banner:
            banner_display = raw_banner.replace("\n", " ").replace("\r", "")[:60]
        else:
            banner_display = "-"

        marker = " ◀" if r["status"] == "open" else ""
        print(
            f"{r['port']:<10} {r['status']:<10} "
            f"{r['service']:<25} {banner_display}{marker}"
        )

    print("-" * 80)
    print(f"Total scanned : {len(results)}")
    print(f"Open ports    : {len(open_ports)}\n")
    print(f"Closed ports  : {len(closed_ports)}\n")


if __name__ == "__main__":
    import sys

    try:
        if len(sys.argv) == 1:
            _target = input("Enter target IP/hostname: ").strip()
            _start = int(input("Enter start port: ").strip())
            _end = int(input("Enter end port: ").strip())
        elif len(sys.argv) == 4:
            _target = sys.argv[1]
            _start = int(sys.argv[2])
            _end = int(sys.argv[3])
        else:
            print("Usage: python port_scanner.py <target> <start_port> <end_port>")
            sys.exit(1)
    except ValueError:
        print("Error: Start/end ports must be valid numbers.")
        sys.exit(1)

    print(f"Scanning {_target}  ports {_start}–{_end} …")
    try:
        _results = scan_ports(_target, _start, _end)
        _print_results(_results)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
