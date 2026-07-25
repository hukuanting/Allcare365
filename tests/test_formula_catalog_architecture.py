import ast
import inspect
from pathlib import Path

from services.disease_risk_engine import formula_catalog
from services.disease_risk_engine.algorithm_registry import RUNTIME_ALGORITHMS
from services.disease_risk_engine.formula_catalog import FORMULA_CALCULATION_STEPS


ENGINE_ROOT = Path(formula_catalog.__file__).parent


def test_formula_catalog_is_the_single_executable_formula_source():
    bound_ids = [
        algorithm_id
        for step in FORMULA_CALCULATION_STEPS
        for algorithm_id in step.algorithm_ids
    ]

    assert bound_ids == [metadata.algorithm_id for metadata in RUNTIME_ALGORITHMS]
    assert len(bound_ids) == len(set(bound_ids)) == len(RUNTIME_ALGORITHMS)
    assert all(
        inspect.getmodule(step.calculator) is formula_catalog
        for step in FORMULA_CALCULATION_STEPS
    )


def test_formula_catalog_has_no_database_api_or_fhir_dependencies():
    source = Path(formula_catalog.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert imported_roots.isdisjoint({"apps", "django", "rest_framework"})


def test_legacy_formula_modules_do_not_return():
    assert not (ENGINE_ROOT / "calculators.py").exists()
    assert not (ENGINE_ROOT / "formal_calculators.py").exists()
    assert not (ENGINE_ROOT / "prevent.py").exists()
