#!/usr/bin/env python
"""
Inferno preflight validator for US Core STU7 single-patient server runs.

Scope:
1. Failure routing: classify Inferno failures into 5 categories.
2. Single Patient Truth Model checks (Patient/onc-patient-1).
3. Deterministic search checks for key chaining queries.
4. Basic ONC synthetic dataset preflight report.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


CANONICAL_PATIENT_ID = "00000000-0000-4000-a000-000000000001"


@dataclass
class RoutedFailure:
    test_id: str
    title: str
    message: str
    category: str


class InfernoFailureRouter:
    """Route Inferno failure messages into actionable categories."""

    CATEGORIES = (
        "reference_traversal_failure",
        "must_support_presence_failure",
        "terminology_expectation_mismatch",
        "search_interaction_mismatch",
        "conditional_test_trigger_failure",
    )

    def classify(self, title: str, message: str) -> str:
        blob = f"{title}\n{message}".lower()

        if (
            "mustsupport references" in blob
            or "must support references" in blob
            or "could not resolve and validate any must support references" in blob
            or "reference(" in blob
            or "did not resolve" in blob
        ):
            return "reference_traversal_failure"

        if (
            "all must support elements are provided" in blob
            and "could not find" in blob
        ) or "missing must support" in blob:
            return "must_support_presence_failure"

        if (
            "did not match the search parameters" in blob
            and "expected:" in blob
            and "found:" in blob
        ) or "value set" in blob or "code system" in blob:
            return "terminology_expectation_mismatch"

        if (
            "no resources were returned when searching" in blob
            or "unexpected response status" in blob
            or "server returns valid results for" in blob
            or "did not match the search parameters" in blob
        ):
            return "search_interaction_mismatch"

        if (
            "skip" in blob
            or "please use patients with more information" in blob
            or "appears to be available" in blob
            or "not triggered" in blob
        ):
            return "conditional_test_trigger_failure"

        return "search_interaction_mismatch"

    def route(self, failures: Iterable[Dict[str, str]]) -> List[RoutedFailure]:
        routed: List[RoutedFailure] = []
        for row in failures:
            title = row.get("title", "")
            message = row.get("message", "")
            routed.append(
                RoutedFailure(
                    test_id=row.get("test_id", ""),
                    title=title,
                    message=message,
                    category=self.classify(title, message),
                )
            )
        return routed


def _extract_failures_from_text(text: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    current: Optional[Dict[str, str]] = None
    pattern = re.compile(r"^\s*(\d+\.\d+\.\d+)\s+(.*)$")

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            if current:
                rows.append(current)
            current = {"test_id": m.group(1), "title": m.group(2), "message": ""}
            continue
        if current is None:
            continue
        if current["message"]:
            current["message"] += "\n" + line
        else:
            current["message"] = line

    if current:
        rows.append(current)
    return rows


def _extract_failures_from_json(payload: Any) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            status = str(node.get("result") or node.get("status") or "").lower()
            title = str(node.get("title") or node.get("name") or "")
            test_id = str(node.get("id") or node.get("short_id") or "")
            message = str(
                node.get("message")
                or node.get("output")
                or node.get("details")
                or node.get("description")
                or ""
            )
            if status in {"fail", "failed", "error"} or "could not" in message.lower():
                if title or message:
                    rows.append({"test_id": test_id, "title": title, "message": message})
            for value in node.values():
                walk(value)
            return
        if isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return rows


def load_inferno_failures(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _extract_failures_from_text(raw)
    return _extract_failures_from_json(payload)


class FHIRClient:
    def __init__(self, base_url: str, bearer_token: Optional[str] = None, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"Accept": "application/fhir+json"}
        if bearer_token:
            self.headers["Authorization"] = f"Bearer {bearer_token}"

    def get(self, path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        query = ""
        if params:
            query = "?" + urllib.parse.urlencode(params, doseq=True)
        url = f"{self.base_url}{path}{query}"
        req = urllib.request.Request(url, headers=self.headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return {"status": resp.status, "json": json.loads(body) if body else {}}
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if hasattr(e, "read") else ""
            parsed: Dict[str, Any] = {}
            if body:
                try:
                    parsed = json.loads(body)
                except json.JSONDecodeError:
                    parsed = {"raw": body}
            return {"status": e.code, "json": parsed}
        except Exception as e:  # pragma: no cover
            return {"status": 0, "json": {"error": str(e)}}


def _bundle_ids(bundle: Dict[str, Any]) -> List[str]:
    ids: List[str] = []
    for entry in bundle.get("entry", []) or []:
        res = entry.get("resource") or {}
        rid = res.get("id")
        if rid:
            ids.append(str(rid))
    return sorted(ids)


def _collect_patient_references(node: Any, refs: List[str]) -> None:
    if isinstance(node, dict):
        ref = node.get("reference")
        if isinstance(ref, str) and ref.startswith("Patient/"):
            refs.append(ref)
        for v in node.values():
            _collect_patient_references(v, refs)
    elif isinstance(node, list):
        for item in node:
            _collect_patient_references(item, refs)


def run_preflight(base_url: str, token: Optional[str]) -> Dict[str, Any]:
    client = FHIRClient(base_url, token)
    report: Dict[str, Any] = {"checks": [], "ok": True}

    # Step 3: Single Patient Truth Model
    patient_read = client.get(f"/Patient/{CANONICAL_PATIENT_ID}")
    patient_ok = patient_read["status"] == 200
    report["checks"].append(
        {
            "name": "single_patient_read",
            "ok": patient_ok,
            "status": patient_read["status"],
            "target": f"Patient/{CANONICAL_PATIENT_ID}",
        }
    )
    report["ok"] = report["ok"] and patient_ok

    # Step 4: Deterministic key chaining searches.
    search_cases = [
        ("Condition", {"patient": CANONICAL_PATIENT_ID}),
        ("Observation", {"patient": CANONICAL_PATIENT_ID, "category": "laboratory"}),
        ("DiagnosticReport", {"patient": CANONICAL_PATIENT_ID, "category": "laboratory"}),
    ]
    for resource_type, params in search_cases:
        first = client.get(f"/{resource_type}", params)
        second = client.get(f"/{resource_type}", params)
        first_ids = _bundle_ids(first.get("json") or {})
        second_ids = _bundle_ids(second.get("json") or {})
        has_results = first["status"] == 200 and len(first_ids) >= 1
        deterministic = first["status"] == 200 and second["status"] == 200 and first_ids == second_ids
        ok = has_results and deterministic
        report["checks"].append(
            {
                "name": f"deterministic_search_{resource_type.lower()}",
                "ok": ok,
                "status_first": first["status"],
                "status_second": second["status"],
                "params": params,
                "first_ids": first_ids,
                "second_ids": second_ids,
            }
        )
        report["ok"] = report["ok"] and ok

    # Verify projected resources reference canonical patient.
    for resource_type in ("Condition", "Observation", "DiagnosticReport", "DocumentReference", "Encounter"):
        res = client.get(f"/{resource_type}", {"patient": CANONICAL_PATIENT_ID})
        refs: List[str] = []
        _collect_patient_references(res.get("json", {}), refs)
        wrong_refs = sorted({r for r in refs if r != f"Patient/{CANONICAL_PATIENT_ID}"})
        ok = res["status"] == 200 and len(wrong_refs) == 0
        report["checks"].append(
            {
                "name": f"single_patient_reference_{resource_type.lower()}",
                "ok": ok,
                "status": res["status"],
                "wrong_refs": wrong_refs,
            }
        )
        report["ok"] = report["ok"] and ok

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Inferno preflight validator")
    parser.add_argument("--inferno-results", help="Path to Inferno result file (json or txt)")
    parser.add_argument("--base-url", help="FHIR base URL, e.g. https://host/fhir")
    parser.add_argument("--token", help="Bearer token")
    parser.add_argument("--output", help="Optional output JSON path")
    args = parser.parse_args()

    final_report: Dict[str, Any] = {}

    if args.inferno_results:
        failures = load_inferno_failures(args.inferno_results)
        routed = InfernoFailureRouter().route(failures)
        counts: Dict[str, int] = {k: 0 for k in InfernoFailureRouter.CATEGORIES}
        for row in routed:
            counts[row.category] = counts.get(row.category, 0) + 1
        final_report["failure_router"] = {
            "total_failures": len(routed),
            "category_counts": counts,
            "failures": [row.__dict__ for row in routed],
        }

    if args.base_url:
        final_report["preflight"] = run_preflight(args.base_url, args.token)

    if not final_report:
        parser.print_help()
        return 2

    rendered = json.dumps(final_report, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(rendered)
    print(rendered)

    if "preflight" in final_report and not final_report["preflight"]["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
