"""
FACS Diagnostic Bundle — Section 8 of the TPL.v2 specification.

Every candidate output generates a FACS bundle that makes epistemic
weakness visible rather than hiding it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FACSBundle:
    """
    Flags, Annotations, Contradiction maps, Suspension logs.

    Attached to every candidate claim and passed through the pipeline so
    that downstream consumers can inspect epistemic quality.
    """

    flags: list[str] = field(default_factory=list)
    annotations: list[str] = field(default_factory=list)
    contradiction_map: dict[str, list[str]] = field(default_factory=dict)
    suspension_logs: list[str] = field(default_factory=list)

    def add_flag(self, flag: str) -> None:
        self.flags.append(flag)

    def add_annotation(self, annotation: str) -> None:
        self.annotations.append(annotation)

    def add_contradiction(self, artifact_id: str, conflicting_ids: list[str]) -> None:
        self.contradiction_map.setdefault(artifact_id, []).extend(conflicting_ids)

    def add_suspension(self, reason: str) -> None:
        self.suspension_logs.append(reason)

    @property
    def has_issues(self) -> bool:
        return bool(self.flags or self.contradiction_map or self.suspension_logs)

    def to_dict(self) -> dict:
        return {
            "flags": self.flags,
            "annotations": self.annotations,
            "contradiction_map": self.contradiction_map,
            "suspension_logs": self.suspension_logs,
        }
