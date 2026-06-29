from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit manuscript references against a local verified-reference registry.")
    parser.add_argument("--registry", default="papers/reference_registry.yaml")
    parser.add_argument("--manuscript", default="papers/firstresearch_draft.md")
    parser.add_argument("--output", default="outputs/reports/reference_audit.md")
    parser.add_argument("--json-output", default="outputs/reports/reference_audit.json")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    registry = yaml.safe_load(Path(args.registry).read_text(encoding="utf-8"))
    manuscript = Path(args.manuscript).read_text(encoding="utf-8")
    results = [_audit_reference(reference, manuscript) for reference in registry["references"]]
    report = _render_report(results)

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


def _audit_reference(reference: dict[str, object], manuscript: str) -> dict[str, object]:
    title = str(reference["title"])
    arxiv_id = str(reference["arxiv_id"])
    url = str(reference["url"])
    terms = [str(term) for term in reference.get("manuscript_terms", [])]
    missing_terms = [term for term in terms if term.lower() not in manuscript.lower()]
    checks = {
        "title_present": title.lower() in manuscript.lower(),
        "arxiv_present": arxiv_id in manuscript,
        "url_present": url in manuscript,
        "support_terms_present": not missing_terms,
    }
    return {
        "key": reference["key"],
        "title": title,
        "arxiv_id": arxiv_id,
        "url": url,
        "verified_source": reference.get("verified_source", ""),
        "checks": checks,
        "missing_manuscript_terms": missing_terms,
        "passed": all(checks.values()),
    }


def _render_report(results: list[dict[str, object]]) -> str:
    lines = [
        "# Reference Audit",
        "",
        "| Key | arXiv | Source | Status | Missing Terms |",
        "|---|---|---|---|---|",
    ]
    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        missing = ", ".join(result["missing_manuscript_terms"]) if result["missing_manuscript_terms"] else ""
        lines.append(
            f"| {result['key']} | {result['arxiv_id']} | [{result['verified_source']}]({result['url']}) | {status} | {missing} |"
        )
    lines.extend(
        [
            "",
            "This audit checks that each registered reference has its title, arXiv identifier, URL, and expected supporting terms in the manuscript.",
            "The registry is based on primary arXiv records verified during manuscript preparation.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
