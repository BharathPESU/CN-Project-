#!/usr/bin/env python3
"""
Concurrent TLS Port Status Server
================================

Run this script on the server laptop. Multiple clients can connect over SSL/TLS
and request how many ports are open on the server.

Protocol (line-delimited JSON):
Client request:
    {
      "start_port": 1,
      "end_port": 1024,
      "target": "127.0.0.1"   # optional, defaults to server host
    }

Server response:
    {
      "ok": true,
      "request_id": "...",
      "target": "127.0.0.1",
      "resolved_ip": "127.0.0.1",
      "start_port": 1,
      "end_port": 1024,
      "open_ports": 5,
      "total_scanned": 1024,
      "scan_duration_seconds": 1.23,
      "results": [{"port": 22, "status": "open"}, ...]
    }
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import os
import signal
import socket
import socketserver
import ssl
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

CONNECT_TIMEOUT = 0.8
BANNER_TIMEOUT = 1.5
BANNER_MAX_BYTES = 1024
MAX_SCAN_WORKERS = 300
MAX_REQUEST_BYTES = 65536
DEFAULT_BIND_HOST = "0.0.0.0"
DEFAULT_BIND_PORT = 9443
DEFAULT_START_PORT = 1
DEFAULT_END_PORT = 1024


def build_logger(log_file: Path, verbose: bool) -> logging.Logger:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ssl-port-status-server")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    return logger


def ensure_certificates(cert_file: Path, key_file: Path, logger: logging.Logger) -> None:
    cert_file.parent.mkdir(parents=True, exist_ok=True)

    if cert_file.exists() and key_file.exists():
        logger.info("TLS certificates found: cert=%s key=%s", cert_file, key_file)
        return

    openssl_path = shutil_which("openssl")
    if not openssl_path:
        raise RuntimeError(
            "TLS cert/key files are missing and OpenSSL is not available. "
            "Install OpenSSL or provide --cert-file and --key-file."
        )

    logger.info("Generating self-signed TLS certificate at %s", cert_file.parent)
    command = [
        openssl_path,
        "req",
        "-x509",
        "-nodes",
        "-newkey",
        "rsa:2048",
        "-keyout",
        str(key_file),
        "-out",
        str(cert_file),
        "-days",
        "365",
        "-subj",
        "/CN=localhost",
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info("Generated self-signed TLS certificate and key")


def shutil_which(binary: str) -> str | None:
    for path in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(path) / binary
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def resolve_target(target: str) -> str:
    try:
        return socket.gethostbyname(target)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve target '{target}': {exc}") from exc


def scan_single_port(ip: str, port: int) -> dict[str, Any]:
    status = "closed"
    service = get_service_name(port)
    banner = None
    try:
        with socket.create_connection((ip, port), timeout=CONNECT_TIMEOUT) as sock:
            status = "open"
            banner = grab_banner(sock)
    except (ConnectionRefusedError, socket.timeout, OSError):
        status = "closed"
    return {"port": port, "status": status, "service": service, "banner": banner}


def scan_port_range(target: str, start_port: int, end_port: int) -> dict[str, Any]:
    resolved_ip = resolve_target(target)
    start_time = time.perf_counter()
    ports = range(start_port, end_port + 1)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_SCAN_WORKERS) as executor:
        futures = [executor.submit(scan_single_port, resolved_ip, port) for port in ports]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    results.sort(key=lambda item: item["port"])
    open_ports = sum(1 for item in results if item["status"] == "open")
    duration = round(time.perf_counter() - start_time, 4)

    return {
        "target": target,
        "resolved_ip": resolved_ip,
        "start_port": start_port,
        "end_port": end_port,
        "open_ports": open_ports,
        "total_scanned": len(results),
        "scan_duration_seconds": duration,
        "results": results,
    }


def get_service_name(port: int) -> str:
    try:
        return socket.getservbyport(port, "tcp")
    except OSError:
        return "unknown"


def grab_banner(sock: socket.socket) -> str | None:
    try:
        try:
            sock.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
        except OSError:
            pass

        sock.settimeout(BANNER_TIMEOUT)
        raw = sock.recv(BANNER_MAX_BYTES)
        return raw.decode(errors="replace").strip() or None
    except OSError:
        return None


class ThreadedTLSMixIn(socketserver.ThreadingMixIn):
    daemon_threads = True
    allow_reuse_address = True


class TLSPortServer(ThreadedTLSMixIn, socketserver.TCPServer):
    def __init__(self, server_address: tuple[str, int], handler_cls: type[socketserver.BaseRequestHandler], context: ssl.SSLContext, logger: logging.Logger):
        self.ssl_context = context
        self.logger = logger
        super().__init__(server_address, handler_cls)

    def get_request(self) -> tuple[socket.socket, tuple[str, int]]:
        sock, addr = super().get_request()
        tls_sock = self.ssl_context.wrap_socket(sock, server_side=True)
        return tls_sock, addr


class PortRequestHandler(socketserver.BaseRequestHandler):
    server: TLSPortServer

    def handle(self) -> None:
        logger = self.server.logger
        request_id = str(uuid.uuid4())[:8]
        client_ip, client_port = self.client_address

        tls_version = "unknown"
        cipher_name = "unknown"
        session_reused = False
        peer_cert_present = False
        if isinstance(self.request, ssl.SSLSocket):
            tls_version = self.request.version() or "unknown"
            cipher = self.request.cipher()
            if cipher:
                cipher_name = cipher[0]
            session_reused = bool(getattr(self.request, "session_reused", False))
            peer_cert_present = bool(self.request.getpeercert())

        logger.info(
            "[%s] connect client=%s:%s tls=%s cipher=%s session_reused=%s client_cert=%s",
            request_id,
            client_ip,
            client_port,
            tls_version,
            cipher_name,
            session_reused,
            "present" if peer_cert_present else "absent",
        )

        try:
            self.request.settimeout(10)
            payload = self._read_json_payload()
            target = str(payload.get("target", "127.0.0.1")).strip() or "127.0.0.1"
            start_port = int(payload.get("start_port", DEFAULT_START_PORT))
            end_port = int(payload.get("end_port", DEFAULT_END_PORT))

            self._validate_ports(start_port, end_port)

            logger.info(
                "[%s] request client=%s:%s target=%s range=%s-%s",
                request_id,
                client_ip,
                client_port,
                target,
                start_port,
                end_port,
            )

            result = scan_port_range(target=target, start_port=start_port, end_port=end_port)
            response = {"ok": True, "request_id": request_id, **result}
            self._send_json(response)

            logger.info(
                "[%s] response client=%s:%s open_ports=%s scanned=%s duration=%ss",
                request_id,
                client_ip,
                client_port,
                result["open_ports"],
                result["total_scanned"],
                result["scan_duration_seconds"],
            )
        except Exception as exc:
            logger.exception("[%s] request_failed client=%s:%s error=%s", request_id, client_ip, client_port, exc)
            self._send_json(
                {
                    "ok": False,
                    "request_id": request_id,
                    "error": str(exc),
                }
            )
        finally:
            logger.info("[%s] disconnect client=%s:%s", request_id, client_ip, client_port)

    def _read_json_payload(self) -> dict[str, Any]:
        chunks: list[bytes] = []
        total_read = 0

        while True:
            data = self.request.recv(4096)
            if not data:
                break
            chunks.append(data)
            total_read += len(data)

            if total_read > MAX_REQUEST_BYTES:
                raise ValueError("Request is too large.")

            if b"\n" in data:
                break

        if not chunks:
            raise ValueError("Empty request payload.")

        raw = b"".join(chunks).split(b"\n", maxsplit=1)[0].decode("utf-8", errors="replace").strip()
        if not raw:
            raise ValueError("Request payload is empty after decoding.")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON payload: {exc.msg}") from exc

        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object.")

        return payload

    def _validate_ports(self, start_port: int, end_port: int) -> None:
        if start_port < 1 or start_port > 65535:
            raise ValueError("start_port must be between 1 and 65535.")
        if end_port < 1 or end_port > 65535:
            raise ValueError("end_port must be between 1 and 65535.")
        if end_port < start_port:
            raise ValueError("end_port must be greater than or equal to start_port.")
        if (end_port - start_port) > 20000:
            raise ValueError("Port range is too large. Maximum allowed width is 20000.")

    def _send_json(self, payload: dict[str, Any]) -> None:
        encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        self.request.sendall(encoded)


def create_ssl_context(cert_file: Path, key_file: Path) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20")
    context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    return context


def parse_args() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]
    default_cert = project_root / "server" / "certs" / "server-cert.pem"
    default_key = project_root / "server" / "certs" / "server-key.pem"
    default_log = project_root / "server" / "logs" / "connections.log"

    parser = argparse.ArgumentParser(description="Concurrent TLS server for open port checks")
    parser.add_argument("--host", default=DEFAULT_BIND_HOST, help="Host/IP to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=DEFAULT_BIND_PORT, help="Port to bind (default: 9443)")
    parser.add_argument("--cert-file", type=Path, default=default_cert, help="TLS certificate path")
    parser.add_argument("--key-file", type=Path, default=default_key, help="TLS private key path")
    parser.add_argument("--log-file", type=Path, default=default_log, help="Connection log file path")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger = build_logger(args.log_file, args.verbose)

    ensure_certificates(cert_file=args.cert_file, key_file=args.key_file, logger=logger)
    ssl_context = create_ssl_context(cert_file=args.cert_file, key_file=args.key_file)

    server = TLSPortServer((args.host, args.port), PortRequestHandler, ssl_context, logger)
    shutdown_event = threading.Event()

    def handle_shutdown(signum: int, _frame: Any) -> None:
        logger.info("Received signal=%s. Initiating shutdown...", signum)
        if not shutdown_event.is_set():
            shutdown_event.set()
            threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("TLS Port Status Server started at %s:%s", args.host, args.port)
    logger.info("Connection logs file: %s", args.log_file)

    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        logger.info("Server stopped.")


if __name__ == "__main__":
    main()