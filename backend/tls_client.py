import json
import socket
import ssl
from typing import Any

MAX_RESPONSE_BYTES = 262144


def request_scan_tls(
    server_host: str,
    server_port: int,
    target: str,
    start_port: int,
    end_port: int,
    timeout: float = 10.0,
    verify: bool = False,
    ca_file: str | None = None,
) -> dict[str, Any]:
    context = ssl.create_default_context()
    if not verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    elif ca_file:
        context.load_verify_locations(cafile=ca_file)

    payload = {
        "start_port": start_port,
        "end_port": end_port,
        "target": target,
    }

    with socket.create_connection((server_host, server_port), timeout=timeout) as sock:
        with context.wrap_socket(
            sock,
            server_hostname=server_host if verify else None,
        ) as tls_sock:
            message = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
            tls_sock.sendall(message)

            buffer = bytearray()
            while True:
                data = tls_sock.recv(4096)
                if not data:
                    break
                buffer.extend(data)
                if b"\n" in data or len(buffer) > MAX_RESPONSE_BYTES:
                    break

    raw = bytes(buffer).split(b"\n", maxsplit=1)[0].decode("utf-8", errors="replace").strip()
    if not raw:
        raise ValueError("Empty response from TLS server.")

    response = json.loads(raw)
    if not isinstance(response, dict):
        raise ValueError("Invalid TLS server response.")
    if not response.get("ok", False):
        raise ValueError(response.get("error", "TLS server returned an error."))

    return response
