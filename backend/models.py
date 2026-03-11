from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class ScanRequest(BaseModel):
    target: str = Field(..., description="IP address or domain name to scan")
    start_port: int = Field(..., ge=1, le=65535, description="Starting port number (1-65535)")
    end_port: int = Field(..., ge=1, le=65535, description="Ending port number (1-65535)")

    @field_validator("end_port")
    @classmethod
    def end_port_must_be_gte_start(cls, end_port: int, info) -> int:
        start = info.data.get("start_port")
        if start is not None and end_port < start:
            raise ValueError("end_port must be greater than or equal to start_port")
        return end_port

    @field_validator("end_port")
    @classmethod
    def port_range_limit(cls, end_port: int, info) -> int:
        start = info.data.get("start_port")
        if start is not None and (end_port - start) > 9999:
            raise ValueError("Port range cannot exceed 10000 ports per request")
        return end_port


class PortResult(BaseModel):
    port: int
    status: str                         # "open" or "closed"
    service: str                        # Detected service name (e.g., "http", "ssh")
    banner: Optional[str] = None        # Banner text grabbed from the open port


class ScanResponse(BaseModel):
    target: str
    resolved_ip: str
    start_port: int
    end_port: int
    open_ports: int
    total_scanned: int
    scan_duration_seconds: float
    results: List[PortResult]


class ErrorResponse(BaseModel):
    detail: str
