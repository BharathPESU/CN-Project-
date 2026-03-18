from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from models import ScanRequest, ScanResponse, ErrorResponse
from scanner import scan_ports

app = FastAPI(
    title="TCP Port Scanner API",
    description="Scan TCP ports on a target host and retrieve service/banner information.",
    version="1.0.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Adjust origins as needed for your frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "TCP Port Scanner API is running."}


# ── POST /scan  (JSON body) ───────────────────────────────────────────────────
@app.post(
    "/scan",
    response_model=ScanResponse,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Scan a port range on a target host",
    tags=["Scanner"],
)
async def scan_post(request: ScanRequest):
    """
    Scan TCP ports in the range **[start_port, end_port]** on the given **target**.

    - **target** – IPv4 address or hostname (e.g. `192.168.1.1` or `example.com`)
    - **start_port** – first port to scan (1–65535)
    - **end_port** – last port to scan (1–65535, must be ≥ start_port)

    Returns per-port status, service name, and any captured banner.
    """
    return await _run_scan(request.target, request.start_port, request.end_port)


# ── GET /scan  (query parameters) ────────────────────────────────────────────
@app.get(
    "/scan",
    response_model=ScanResponse,
    responses={400: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    summary="Scan a port range on a target host (query params)",
    tags=["Scanner"],
)
async def scan_get(
    target: str = Query(..., description="IP address or hostname to scan"),
    start_port: int = Query(..., ge=1, le=65535, description="First port in range"),
    end_port: int = Query(..., ge=1, le=65535, description="Last port in range"),
):
    """
    Same as **POST /scan** but accepts parameters as URL query strings.

    Example: `/scan?target=127.0.0.1&start_port=20&end_port=100`
    """
    # Manual cross-field validation (FastAPI doesn't run Pydantic validators here)
    if end_port < start_port:
        raise HTTPException(
            status_code=400,
            detail="end_port must be greater than or equal to start_port.",
        )
    if (end_port - start_port) > 9999:
        raise HTTPException(
            status_code=400,
            detail="Port range cannot exceed 10 000 ports per request.",
        )
    return await _run_scan(target, start_port, end_port)


# ── Shared scan logic ─────────────────────────────────────────────────────────
async def _run_scan(target: str, start_port: int, end_port: int) -> ScanResponse:
    """Delegate to the scanner module and package the result."""
    try:
        resolved_ip, results, duration = scan_ports(target, start_port, end_port)
    except ValueError as exc:
        # Covers unresolvable hostnames and other input errors from scanner.py
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    open_count = sum(1 for r in results if r.status == "open")
    closed_count = sum(1 for r in results if r.status == "closed")

    print(
        f"[SCAN] target={target} resolved_ip={resolved_ip} range={start_port}-{end_port} "
        f"total_ports={len(results)} open_ports={open_count} closed_ports={closed_count} "
        f"duration={duration}s"
    )

    return ScanResponse(
        target=target,
        resolved_ip=resolved_ip,
        start_port=start_port,
        end_port=end_port,
        open_ports=open_count,
        total_scanned=len(results),
        scan_duration_seconds=duration,
        results=results,
    )
