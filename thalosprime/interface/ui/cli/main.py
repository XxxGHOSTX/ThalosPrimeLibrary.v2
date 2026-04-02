"""
CLI — command-line interface for TPL.v2 (Section 24.10).

Usage:
    python -m thalosprime.interface.ui.cli.main

Interaction modes supported:
    query     — ask a question and get a grounded response
    ingest    — inject a new artifact into the archive
    audit     — display the current audit trail
    quit / exit — end the session
"""

from __future__ import annotations

import json
import sys


def run_cli() -> None:
    from thalosprime.interface.chat.response_orchestrator import ResponseOrchestrator
    from thalosprime.interface.chat.session_manager import SessionManager
    from thalosprime.interface.adapters.input_normalizer import InputNormalizer
    from thalosprime.interface.adapters.output_formatter import OutputFormatter

    orchestrator = ResponseOrchestrator()
    session_mgr = SessionManager()
    session = session_mgr.create_session()
    normalizer = InputNormalizer()
    formatter = OutputFormatter()

    print("ThalosPrimeLibrary.v2 — Epistemic Operating System")
    print(f"Session: {session.session_id}")
    print("Commands: query <text> | ingest <json> | audit | quit\n")

    while True:
        try:
            line = input("tpl> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if not line:
            continue

        cmd, _, rest = line.partition(" ")
        cmd = cmd.lower()

        if cmd in ("quit", "exit", "q"):
            print("Session ended.")
            break

        elif cmd == "query":
            if not rest.strip():
                print("[ERROR] query requires text")
                continue
            try:
                normalized = normalizer.normalize(rest)
                output = orchestrator.handle_query(
                    normalized,
                    session_id=session.session_id,
                    context=session.context,
                )
                session.record_query(normalized)
                print("\n" + formatter.to_text(output))
                print()
            except Exception as exc:
                print(f"[ERROR] {exc}")

        elif cmd == "ingest":
            if not rest.strip():
                print("[ERROR] ingest requires a JSON artifact")
                continue
            try:
                from thalosprime.core.artifact.canonical import CanonicalArtifact
                data = json.loads(rest)
                artifact = CanonicalArtifact.create(
                    artifact_id=data["artifact_id"],
                    canonical_content=data["canonical_content"],
                    source_set=data.get("source_set", []),
                    provenance_path=data.get("provenance_path", []),
                    timestamp=data.get("timestamp", 0),
                    confidence=data.get("confidence", 0.5),
                    status=data.get("status", "provisional"),
                    metadata=data.get("metadata", {}),
                )
                orchestrator.ingest(artifact)
                print(f"[OK] Artifact {artifact.artifact_id} ingested")
            except Exception as exc:
                print(f"[ERROR] {exc}")

        elif cmd == "audit":
            events = orchestrator.audit_trail.events()
            if not events:
                print("(no audit events)")
            else:
                for ev in events:
                    print(f"  [{ev.kind}] {ev.description}")
            print()

        else:
            print(f"[ERROR] Unknown command: {cmd!r}")


if __name__ == "__main__":
    run_cli()
