from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django

django.setup()

from services.disease_risk_engine.source_asset_inventory import write_source_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a read-only evidence manifest for disease-risk source files."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "docs" / "Examplar excel files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "risk_model_source_manifest.json",
    )
    args = parser.parse_args()
    manifest = write_source_manifest(args.source, args.output)
    summary = manifest["summary"]
    print(
        "Risk source manifest written: "
        f"assets={summary['asset_count']} "
        f"xlsx_formula_cells={summary['xlsx_formula_cells']} "
        f"runtime_algorithms={summary['runtime_algorithm_count']} "
        f"output={args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
