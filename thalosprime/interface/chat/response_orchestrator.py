"""
Response Orchestrator — the main pipeline coordinator for the chat interface.

Implements Section 24.2 and 24.3 of the TPL.v2 specification.

Pipeline:
    user input → query artifact → indexing → retrieval → reasoning
              → validation → belief interaction → presentation

Every step is logged to the audit trail.  No shortcuts allowed.
"""

from __future__ import annotations

from thalosprime.archive.coordinate_space.babel import InMemoryBabelArchive, PolicyContext
from thalosprime.audit.trail import AuditEvent, AuditEventKind, InMemoryAuditTrail
from thalosprime.core.artifact.canonical import CanonicalArtifact
from thalosprime.core.belief.base import InMemoryBeliefBase
from thalosprime.core.indexing.deterministic import SimpleDeterministicIndexer
from thalosprime.core.presentation.engine import DefaultPresentationEngine, EpistemicOutput
from thalosprime.core.reasoning.reasoner import PassthroughReasoner
from thalosprime.core.validation.validator import BasicValidator
from thalosprime.interface.chat.context_tracker import ContextTracker
from thalosprime.interface.chat.query_parser import QueryParser


class ResponseOrchestrator:
    """
    Wires every subsystem together to handle a user query.

    Injection: all dependencies (archive, belief base, etc.) may be supplied
    externally.  Defaults create local in-memory instances so the orchestrator
    works out of the box with zero external infrastructure.
    """

    def __init__(
        self,
        archive: InMemoryBabelArchive | None = None,
        belief_base: InMemoryBeliefBase | None = None,
        audit_trail: InMemoryAuditTrail | None = None,
    ) -> None:
        self._archive = archive or InMemoryBabelArchive()
        self._belief = belief_base or InMemoryBeliefBase()
        self._audit = audit_trail or InMemoryAuditTrail()
        self._indexer = SimpleDeterministicIndexer()
        self._reasoner = PassthroughReasoner()
        self._validator = BasicValidator()
        self._presenter = DefaultPresentationEngine()
        self._parser = QueryParser()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def handle_query(
        self,
        user_input: str,
        session_id: str = "",
        context: ContextTracker | None = None,
        policy_context: PolicyContext | None = None,
    ) -> EpistemicOutput:
        """
        Full pipeline execution for a single user query.

        Returns an EpistemicOutput (dual-channel) or a suspension notice.
        """
        policy_context = policy_context or PolicyContext()

        # 1. Parse user input into a query artifact
        self._audit.append(AuditEvent(
            kind=AuditEventKind.QUERY_RECEIVED,
            artifact_id=None,
            description=f"Query received: {user_input[:80]}",
        ))
        query_artifact = self._parser.parse(user_input, session_id=session_id)

        # 2. Store query artifact in archive → generates coordinate
        bundle = self._archive.store(query_artifact)
        self._audit.append(AuditEvent(
            kind=AuditEventKind.COORDINATE_GENERATED,
            artifact_id=query_artifact.artifact_id,
            description="Query artifact stored and coordinate generated",
            payload={"identity_coord": bundle.identity_coord[:16]},
        ))

        # 3. Retrieve relevant artifacts from archive (query mode: self + neighbours)
        stored = self._archive.resolve(bundle.identity_coord)
        neighbours = self._archive.semantic_neighbourhood(bundle.identity_coord)
        candidates_raw = [stored.artifact] if stored else [query_artifact]
        for n in neighbours:
            if n.artifact.artifact_id != query_artifact.artifact_id:
                candidates_raw.append(n.artifact)

        # 4. Reason over candidates
        indexed = [(a, self._indexer.encode(a)) for a in candidates_raw]
        propositions = self._reasoner.derive(indexed, self._belief)

        # 5. Validate each proposition
        admitted: list[CanonicalArtifact] = []
        for prop in propositions:
            vr = self._validator.validate(prop.proposition)
            self._audit.append(AuditEvent(
                kind=AuditEventKind.VALIDATION_OUTCOME,
                artifact_id=prop.proposition.artifact_id,
                description=f"Validation {'passed' if vr.passed else 'failed'} at stage {vr.stage_reached}",
                payload=vr.to_dict(),
            ))
            if vr.passed:
                admitted.append(prop.proposition)
                if context is not None:
                    context.add_reference(prop.proposition)
            else:
                self._belief.suspend(prop.proposition)
                self._audit.append(AuditEvent(
                    kind=AuditEventKind.CLAIM_REJECTED,
                    artifact_id=prop.proposition.artifact_id,
                    description="Claim failed validation; suspended",
                ))

        # 6. Present result
        if not admitted:
            suspension_artifact = CanonicalArtifact.create(
                artifact_id=query_artifact.artifact_id + ":suspended",
                canonical_content=(
                    "Insufficient evidence to admit a claim. "
                    "Evidence withheld or validation failed."
                ),
                source_set=["system"],
                provenance_path=["response_orchestrator", "suspension"],
                timestamp=query_artifact.timestamp,
                confidence=0.0,
                status="suspended",
            )
            result = self._presenter.render(suspension_artifact)
        else:
            primary = admitted[0]
            result = self._presenter.render(primary)

        self._audit.append(AuditEvent(
            kind=AuditEventKind.RESPONSE_RENDERED,
            artifact_id=admitted[0].artifact_id if admitted else None,
            description="Response rendered and returned to caller",
        ))

        return result

    # ------------------------------------------------------------------
    # Direct ingestion (Build Mode — Section 24.4)
    # ------------------------------------------------------------------

    def ingest(self, artifact: CanonicalArtifact) -> None:
        """
        Inject an externally authored artifact into the archive.

        The artifact still passes through validation before being admitted
        to the belief base.
        """
        bundle = self._archive.store(artifact)
        self._audit.append(AuditEvent(
            kind=AuditEventKind.COORDINATE_GENERATED,
            artifact_id=artifact.artifact_id,
            description="External artifact ingested",
            payload={"identity_coord": bundle.identity_coord[:16]},
        ))
        vr = self._validator.validate(artifact)
        if vr.passed:
            self._belief.accept(artifact)
            self._audit.append(AuditEvent(
                kind=AuditEventKind.CLAIM_ADMITTED,
                artifact_id=artifact.artifact_id,
                description="External artifact admitted to belief base",
            ))
        else:
            self._belief.suspend(artifact)

    @property
    def audit_trail(self) -> InMemoryAuditTrail:
        return self._audit

    @property
    def belief_base(self) -> InMemoryBeliefBase:
        return self._belief
