"""
Reference resolution and projection contract validation.
"""
from __future__ import annotations

from typing import Any, List, Optional

from .projectors.registry import ProjectorRegistry
from .projection_contracts import ProjectionContract, get_projection_contract


def _walk_path(node: Any, parts: List[str]) -> List[Any]:
    if not parts:
        return [node]
    if node is None:
        return []
    if isinstance(node, list):
        out: List[Any] = []
        for item in node:
            out.extend(_walk_path(item, parts))
        return out
    if isinstance(node, dict):
        key = parts[0]
        if key in node:
            return _walk_path(node.get(key), parts[1:])
    return []


def _extract_references(resource: dict, path: str) -> List[str]:
    parts = [segment.split(":")[0] for segment in path.split(".") if segment]
    refs: List[str] = []
    for node in _walk_path(resource, parts):
        if isinstance(node, list):
            for item in node:
                if isinstance(item, dict) and isinstance(item.get("reference"), str):
                    refs.append(item["reference"])
            continue
        if isinstance(node, dict) and isinstance(node.get("reference"), str):
            refs.append(node["reference"])
    return refs


def _coding_systems(node: Any) -> List[str]:
    systems: List[str] = []
    if isinstance(node, list):
        for item in node:
            systems.extend(_coding_systems(item))
        return systems
    if isinstance(node, dict):
        if isinstance(node.get("system"), str):
            systems.append(node["system"])
        if "coding" in node:
            systems.extend(_coding_systems(node["coding"]))
        if "valueQuantity" in node:
            systems.extend(_coding_systems(node["valueQuantity"]))
    return systems


class ReferenceResolutionEngine:
    def resolve(self, reference: str, context) -> Optional[dict]:
        target_type, _, raw_id = reference.partition("/")
        if not target_type or not raw_id or not ProjectorRegistry.has(target_type):
            return None

        projector = ProjectorRegistry.get(target_type)
        search_patient_id = None if target_type == "Patient" else context.patient_id
        items = projector.query(
            patient_id=search_patient_id,
            search_params={"_id": raw_id},
            context=context,
        )
        for resource in self._project_without_recursive_validation(projector, items, context):
            if str(resource.get("id")) == raw_id and resource.get("resourceType") == target_type:
                return resource
        return None

    def _project_without_recursive_validation(self, projector, items, context) -> List[dict]:
        """
        Project resources for reference existence checks without calling
        project_batch(), which performs full contract validation and can recurse
        through cyclic clinical references such as Condition <-> Encounter.
        """
        if isinstance(items, list) and all(isinstance(item, dict) for item in items):
            return list(items)

        try:
            iterable = projector.optimize_queryset(items)
        except AttributeError:
            iterable = items

        resources: List[dict] = []
        for item in iterable:
            normalized = projector.normalize(item)
            resource = projector.project(normalized, context)
            resource = projector.apply_extensions(resource, normalized, context)
            resources.append(resource)
        return resources


class ProjectionContractValidator:
    def __init__(self):
        self.reference_engine = ReferenceResolutionEngine()

    def validate(self, resource: dict, context, contract: Optional[ProjectionContract] = None) -> None:
        contract = contract or get_projection_contract(resource.get("resourceType", ""))
        if contract is None:
            return
        self._validate_profiles(resource, contract)
        self._validate_top_level_elements(resource, contract)
        self._validate_references(resource, context, contract)
        self._validate_terminology(resource, contract)

    def _validate_profiles(self, resource: dict, contract: ProjectionContract) -> None:
        expected = set(contract.supported_profile_urls)
        if not expected:
            return
        actual = set(resource.get("meta", {}).get("profile", []) or [])
        if not {item.split("|")[0] for item in actual}.intersection(expected):
            raise ValueError(
                f"{contract.resource_type} projection missing required US Core profile."
            )

    def _validate_top_level_elements(self, resource: dict, contract: ProjectionContract) -> None:
        missing = [element for element in contract.top_level_must_support_elements if element not in resource]
        if missing:
            raise ValueError(
                f"{contract.resource_type} projection missing Must Support elements: {', '.join(sorted(missing))}"
            )

    def _validate_references(self, resource: dict, context, contract: ProjectionContract) -> None:
        edges = contract.enforced_references or contract.must_support_references
        path_targets: dict[str, list[str]] = {}
        for edge in edges:
            for path in edge["paths"]:
                path_targets.setdefault(path, []).append(edge["target"])

        for path, target_types in path_targets.items():
            refs = _extract_references(resource, path)
            if not refs:
                raise ValueError(
                    f"{contract.resource_type} projection missing required reference at {path}"
                )
            for ref in refs:
                matched_type = next((target for target in target_types if ref.startswith(f"{target}/")), None)
                if matched_type is None:
                    raise ValueError(
                        f"{contract.resource_type} reference {ref} does not target any allowed type for {path}: {target_types}"
                    )
                resolved = self.reference_engine.resolve(ref, context)
                if resolved is None:
                    raise ValueError(f"{contract.resource_type} reference {ref} could not be resolved")
                target_contract = get_projection_contract(matched_type)
                if target_contract is not None:
                    self._validate_profiles(resolved, target_contract)

    def _validate_terminology(self, resource: dict, contract: ProjectionContract) -> None:
        for path, expected_systems in contract.terminology_bindings.items():
            systems: List[str] = []
            for node in _walk_path(resource, path.split(".")):
                systems.extend(_coding_systems(node))
            if expected_systems and not any(system in expected_systems for system in systems):
                raise ValueError(
                    f"{contract.resource_type} projection failed terminology binding at {path}"
                )
