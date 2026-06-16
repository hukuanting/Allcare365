"""
Lazy Include Resolver — Resolves _include references at Bundle assembly time.

During projection, projectors call ``context.include_tracker.add(type, id)``.
After all primary resources are projected, the BundleBuilder calls this resolver
to batch-fetch and project included resources.  This prevents recursive explosion.
"""
from __future__ import annotations

from typing import Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext, IncludeTracker


class IncludeResolver:
    """
    Resolves lazily-tracked _include references into FHIR resource dicts.

    Currently supports:
      - MedicationRequest:medication  → project referenced Medication
      - MedicationDispense:medication → project referenced Medication
    """

    @staticmethod
    def resolve(tracker: "IncludeTracker", context: "FHIRContext") -> List[dict]:
        """
        Resolve all pending includes in the tracker.

        Returns a list of FHIR resource dicts with ``search.mode = "include"``.
        """
        if not tracker.pending:
            return []

        from ..projectors.registry import ProjectorRegistry

        # Group by resource type to batch-resolve
        grouped: Dict[str, List[str]] = {}
        for resource_type, resource_id in tracker.pending:
            grouped.setdefault(resource_type, []).append(resource_id)

        resolved = []
        for resource_type, ids in grouped.items():
            if not ProjectorRegistry.has(resource_type):
                continue
            projector = ProjectorRegistry.get(resource_type)
            tracked_ids = set(ids)
            # Use the projector's query to fetch by patient context
            # For Medication, we project from the same source (PatientMedication)
            try:
                items = projector.query(
                    patient_id=context.patient_id,
                    search_params={},
                    context=context,
                )
                resources = projector.project_batch(items, context)
                # Deduplicate by ID and only include those that were tracked
                seen = set()
                for r in resources:
                    rid = r.get("id", "")
                    if rid in tracked_ids and rid not in seen:
                        seen.add(rid)
                        resolved.append(r)
            except Exception:
                continue

        tracker.mark_resolved(resolved)
        return resolved
