from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit manuscript claims against the evidence artifact audit.")
    parser.add_argument("--registry", default="papers/claim_evidence_registry.yaml")
    parser.add_argument("--evidence-audit", default="outputs/reports/paper_evidence_audit.json")
    parser.add_argument("--manuscript", default="papers/firstresearch_draft.md")
    parser.add_argument("--output", default="outputs/reports/claim_evidence_audit.md")
    parser.add_argument("--json-output", default="outputs/reports/claim_evidence_audit.json")
    parser.add_argument(
        "--submission-ready",
        action="store_true",
        help="Require every registered claim to have its evidence satisfied.",
    )
    parser.add_argument("--strict", action="store_true", help="Exit nonzero on failed required checks.")
    args = parser.parse_args()

    registry = yaml.safe_load(Path(args.registry).read_text(encoding="utf-8"))
    evidence = _load_evidence(Path(args.evidence_audit))
    manuscript = Path(args.manuscript).read_text(encoding="utf-8")
    results = [_audit_claim(claim, evidence, manuscript, args.submission_ready) for claim in registry["claims"]]
    report = _render_report(results, args.submission_ready)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    if args.json_output:
        json_output = Path(args.json_output)
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(output)

    if args.strict and any(not result["passed"] for result in results):
        raise SystemExit(1)


def _load_evidence(path: Path) -> dict[str, bool]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["id"]: bool(row["passed"]) for row in data}


def _audit_claim(
    claim: dict[str, object],
    evidence: dict[str, bool],
    manuscript: str,
    submission_ready: bool,
) -> dict[str, object]:
    required = [str(item) for item in claim.get("required_evidence", [])]
    missing = [item for item in required if not evidence.get(item, False)]
    terms = [str(item) for item in claim.get("manuscript_terms", [])]
    missing_terms = [term for term in terms if term.lower() not in manuscript.lower()]
    status = str(claim.get("status", ""))
    allowed_without_submission_ready = bool(claim.get("allowed_without_submission_ready", False))

    if submission_ready:
        evidence_ok = not missing
    elif status == "not_supported_yet":
        evidence_ok = bool(missing) or not missing
    else:
        evidence_ok = not missing or allowed_without_submission_ready

    if status == "not_supported_yet":
        status_ok = bool(missing) or submission_ready
    else:
        status_ok = not missing

    terms_ok = not missing_terms
    passed = evidence_ok and status_ok and terms_ok
    if submission_ready and missing:
        passed = False

    return {
        "id": claim["id"],
        "claim": claim["claim"],
        "status": status,
        "required_evidence": required,
        "missing_evidence": missing,
        "missing_manuscript_terms": missing_terms,
        "passed": passed,
        "submission_ready_mode": submission_ready,
    }


def _render_report(results: list[dict[str, object]], submission_ready: bool) -> str:
    lines = [
        "# Claim-Evidence Audit",
        "",
        f"Submission-ready mode: `{str(submission_ready).lower()}`",
        "",
        "| Claim ID | Status | Audit | Missing Evidence | Missing Manuscript Terms |",
        "|---|---|---|---|---|",
    ]
    for result in results:
        audit = "PASS" if result["passed"] else "FAIL"
        missing_evidence = ", ".join(result["missing_evidence"]) if result["missing_evidence"] else ""
        missing_terms = ", ".join(result["missing_manuscript_terms"]) if result["missing_manuscript_terms"] else ""
        lines.append(
            f"| {result['id']} | {result['status']} | {audit} | {missing_evidence} | {missing_terms} |"
        )
    lines.extend(
        [
            "",
            "Supported-current claims must have current evidence and limiting language.",
            "Not-supported-yet claims are allowed in the draft only when the required evidence is still missing and the manuscript marks them as future or unsupported.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
