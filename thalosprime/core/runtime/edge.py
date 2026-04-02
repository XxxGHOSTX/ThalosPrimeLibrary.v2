"""
Edge Runtime — Section 11 of the TPL.v2 specification.

Runs local inference and retrieval on available hardware.  The runtime
is an optional adapter layer; the core system operates independently of
any specific backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class BackendType(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    NPU = "npu"
    ACCELERATOR = "accelerator"


@dataclass
class Workload:
    """Represents a unit of computation for edge execution."""

    workload_id: str
    operation: str
    payload: dict
    backend_hint: BackendType = BackendType.CPU


@dataclass
class WorkloadResult:
    workload_id: str
    success: bool
    output: dict
    backend_used: BackendType
    latency_ms: float


class EdgeRuntime(ABC):
    """Abstract contract for edge-native execution."""

    @abstractmethod
    def execute(self, workload: Workload) -> WorkloadResult:
        """Execute *workload* on the locally available backend."""

    @abstractmethod
    def available_backends(self) -> list[BackendType]:
        """Return list of available backend types."""


class LocalCPURuntime(EdgeRuntime):
    """
    Minimal CPU-only edge runtime.

    Executes workloads in-process.  This satisfies the offline-continuity
    and sovereignty-preserving requirements of Section 11.
    """

    def available_backends(self) -> list[BackendType]:
        return [BackendType.CPU]

    def execute(self, workload: Workload) -> WorkloadResult:
        import time
        start = time.monotonic()
        output = self._dispatch(workload)
        elapsed_ms = (time.monotonic() - start) * 1000
        return WorkloadResult(
            workload_id=workload.workload_id,
            success=True,
            output=output,
            backend_used=BackendType.CPU,
            latency_ms=elapsed_ms,
        )

    def _dispatch(self, workload: Workload) -> dict:
        """Route to operation handler."""
        handlers = {
            "echo": self._op_echo,
            "hash": self._op_hash,
        }
        handler = handlers.get(workload.operation, self._op_unknown)
        return handler(workload.payload)

    @staticmethod
    def _op_echo(payload: dict) -> dict:
        return {"echo": payload}

    @staticmethod
    def _op_hash(payload: dict) -> dict:
        import hashlib
        import json
        data = json.dumps(payload, sort_keys=True).encode()
        return {"sha256": hashlib.sha256(data).hexdigest()}

    @staticmethod
    def _op_unknown(payload: dict) -> dict:
        return {"error": "unknown operation", "payload": payload}
