from pathlib import Path
import csv
import json
import subprocess
import sys

from firstresearch.benchmark.report import generate_report
from firstresearch.benchmark.baselines import get_baselines
from firstresearch.benchmark.runners import run_benchmark
from firstresearch.agents.core import GateAgent
from firstresearch.orchestrator import ResearchOrchestrator, _certificate_rank_key
from firstresearch.schemas import ResearchTopic


def test_single_topic_pipeline_has_experiment_plan():
    package = ResearchOrchestrator().run(ResearchTopic(topic="When should an agent discover a new skill?"))
    assert package.experiment_plans
    assert package.review is not None
    assert package.self_improvement_update is not None
    assert "gate_repair_count" in package.metadata


def test_benchmark_and_report(tmp_path: Path):
    topics = tmp_path / "topics.jsonl"
    topics.write_text('{"topic_id":"T1","topic":"Agent skill discovery","domain":"LLM agents"}\n', encoding="utf-8")
    csv_path = tmp_path / "results.csv"
    jsonl_path = tmp_path / "results.jsonl"
    results = run_benchmark(
        topics_path=topics,
        output_csv=csv_path,
        output_jsonl=jsonl_path,
        systems=["firstresearch", "single_prompt"],
        package_dir=tmp_path / "packages",
    )
    assert len(results) == 2
    assert csv_path.exists()
    report_path = tmp_path / "report.md"
    table_path = tmp_path / "table.csv"
    text = generate_report(csv_path, report_path, table_path)
    assert "Average Scores" in text
    assert "Comparison Table" in text
    assert "Delta vs Full" in text
    assert table_path.exists()


def test_run_benchmark_cli_accepts_artifact_paths(tmp_path: Path):
    topics = tmp_path / "topics.jsonl"
    topics.write_text('{"topic_id":"T1","topic":"Agent skill discovery","domain":"LLM agents"}\n', encoding="utf-8")
    csv_path = tmp_path / "custom.csv"
    jsonl_path = tmp_path / "custom.jsonl"
    package_dir = tmp_path / "custom_packages"
    metadata_path = tmp_path / "custom_metadata.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark.py",
            "--config",
            "configs/does_not_exist.yaml",
            "--topics",
            str(topics),
            "--llm",
            "mock",
            "--max-topics",
            "1",
            "--systems",
            "firstresearch",
            "certificate_only_ablation",
            "--repeats",
            "2",
            "--output",
            str(csv_path),
            "--output-jsonl",
            str(jsonl_path),
            "--package-dir",
            str(package_dir),
            "--metadata-output",
            str(metadata_path),
            "--run-id",
            "test-run-001",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert str(csv_path) in completed.stdout
    assert csv_path.exists()
    assert jsonl_path.exists()
    assert (package_dir / "r01_T1_firstresearch.json").exists()
    assert (package_dir / "r02_T1_firstresearch.json").exists()
    assert (package_dir / "r01_T1_certificate_only_ablation.json").exists()
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "replicate" in csv_text.splitlines()[0]
    assert "run_id" in csv_text.splitlines()[0]
    rows = list(csv.DictReader(csv_text.splitlines()))
    assert sum(row["system"] == "certificate_only_ablation" for row in rows) == 2
    assert {row["run_id"] for row in rows} == {"test-run-001"}
    assert metadata_path.exists()
    assert '"run_id": "test-run-001"' in metadata_path.read_text(encoding="utf-8")


def test_run_benchmark_cli_resumes_existing_rows(tmp_path: Path):
    topics = tmp_path / "topics.jsonl"
    topics.write_text('{"topic_id":"T1","topic":"Agent skill discovery","domain":"LLM agents"}\n', encoding="utf-8")
    csv_path = tmp_path / "resume.csv"
    jsonl_path = tmp_path / "resume.jsonl"
    package_dir = tmp_path / "packages"

    subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark.py",
            "--config",
            "configs/does_not_exist.yaml",
            "--topics",
            str(topics),
            "--llm",
            "mock",
            "--systems",
            "firstresearch",
            "--output",
            str(csv_path),
            "--output-jsonl",
            str(jsonl_path),
            "--package-dir",
            str(package_dir),
            "--run-id",
            "resume-test-001",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    first_rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    assert len(first_rows) == 1

    subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark.py",
            "--config",
            "configs/does_not_exist.yaml",
            "--topics",
            str(topics),
            "--llm",
            "mock",
            "--systems",
            "firstresearch",
            "single_prompt",
            "--output",
            str(csv_path),
            "--output-jsonl",
            str(jsonl_path),
            "--package-dir",
            str(package_dir),
            "--run-id",
            "resume-test-001",
            "--resume",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    resumed_rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    assert len(resumed_rows) == 2
    assert sum(row["system"] == "firstresearch" for row in resumed_rows) == 1
    assert sum(row["system"] == "single_prompt" for row in resumed_rows) == 1


def test_run_benchmark_cli_target_rows(tmp_path: Path):
    topics = tmp_path / "topics.jsonl"
    topics.write_text(
        '{"topic_id":"T1","topic":"Agent skill discovery","domain":"LLM agents"}\n'
        '{"topic_id":"T2","topic":"Research skill routing","domain":"LLM agents"}\n',
        encoding="utf-8",
    )
    csv_path = tmp_path / "target.csv"
    metadata_path = tmp_path / "target_metadata.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark.py",
            "--config",
            "configs/does_not_exist.yaml",
            "--topics",
            str(topics),
            "--llm",
            "mock",
            "--systems",
            "firstresearch",
            "single_prompt",
            "--target-rows",
            "3",
            "--output",
            str(csv_path),
            "--metadata-output",
            str(metadata_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    assert len(rows) == 3
    assert '"target_rows": 3' in metadata_path.read_text(encoding="utf-8")


def test_run_benchmark_cli_accepts_separate_judge(tmp_path: Path):
    topics = tmp_path / "topics.jsonl"
    topics.write_text('{"topic_id":"T1","topic":"Agent skill discovery","domain":"LLM agents"}\n', encoding="utf-8")
    csv_path = tmp_path / "judged.csv"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark.py",
            "--config",
            "configs/does_not_exist.yaml",
            "--topics",
            str(topics),
            "--llm",
            "mock",
            "--judge-with-llm",
            "--judge-llm",
            "mock",
            "--judge-model",
            "mock-judge",
            "--systems",
            "firstresearch",
            "--output",
            str(csv_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert str(csv_path) in completed.stdout
    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    assert rows[0]["review_score"] == "7"


def test_rescore_packages_accepts_config(tmp_path: Path):
    topics = tmp_path / "topics.jsonl"
    topics.write_text('{"topic_id":"T1","topic":"Agent skill discovery","domain":"LLM agents"}\n', encoding="utf-8")
    source_csv = tmp_path / "source.csv"
    package_dir = tmp_path / "packages"
    run_benchmark(
        topics_path=topics,
        output_csv=source_csv,
        systems=["firstresearch"],
        package_dir=package_dir,
    )
    output_csv = tmp_path / "rescored.csv"
    output_jsonl = tmp_path / "rescored.jsonl"
    metadata_path = tmp_path / "rescored_metadata.json"
    config_path = tmp_path / "rescore.yaml"
    config_path.write_text(
        f"input_results: {source_csv.as_posix()}\n"
        f"output_csv: {output_csv.as_posix()}\n"
        f"output_jsonl: {output_jsonl.as_posix()}\n"
        f"metadata_output: {metadata_path.as_posix()}\n"
        "run_id: rescore-test-001\n"
        "judge_llm: mock\n"
        "judge_model: mock-judge\n",
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, "scripts/rescore_packages.py", "--config", str(config_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert output_csv.exists()
    assert output_jsonl.exists()
    assert metadata_path.exists()
    rows = list(csv.DictReader(output_csv.read_text(encoding="utf-8").splitlines()))
    assert rows[0]["review_score"] == "7"
    assert rows[0]["run_id"] == "rescore-test-001"


def test_export_human_review_packet(tmp_path: Path):
    topics = tmp_path / "topics.jsonl"
    topics.write_text('{"topic_id":"T1","topic":"Agent skill discovery","domain":"LLM agents"}\n', encoding="utf-8")
    csv_path = tmp_path / "results.csv"
    jsonl_path = tmp_path / "results.jsonl"
    package_dir = tmp_path / "packages"
    review_dir = tmp_path / "human_review"
    run_benchmark(
        topics_path=topics,
        output_csv=csv_path,
        output_jsonl=jsonl_path,
        systems=["firstresearch", "no_certificate_ablation"],
        package_dir=package_dir,
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/export_human_review_packet.py",
            "--results",
            str(csv_path),
            "--output-dir",
            str(review_dir),
            "--seed",
            "7",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert (review_dir / "rubric.md").exists()
    assert (review_dir / "assignments_private.json").exists()
    review_files = sorted(review_dir.glob("HR*.md"))
    assert len(review_files) == 2
    review_text = review_files[0].read_text(encoding="utf-8")
    assert "Blinded Review Item" in review_text
    assert "Reviewer Scores" in review_text
    assert "firstresearch" not in review_text.lower()

    scores_path = tmp_path / "human_scores.csv"
    scores_path.write_text(
        "blind_id,reviewer_id,first_principles_derivation,falsifiability,mechanism_clarity,novelty,experimentability,review_score,recommendation\n"
        "HR0001,R1,4,4,4,4,4,8,weak_accept\n"
        "HR0002,R1,2,2,2,2,3,4,weak_reject\n",
        encoding="utf-8",
    )
    report_path = tmp_path / "human_review_report.md"
    table_path = tmp_path / "human_review_summary.csv"
    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_human_review.py",
            "--assignments",
            str(review_dir / "assignments_private.json"),
            "--scores",
            str(scores_path),
            "--output",
            str(report_path),
            "--table-output",
            str(table_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = report_path.read_text(encoding="utf-8")
    assert "Scalar Human Review Report" in report
    assert "Completed scalar reviews: 2" in report
    assert table_path.exists()


def test_export_pairwise_review_packet(tmp_path: Path):
    topics = tmp_path / "topics.jsonl"
    topics.write_text('{"topic_id":"T1","topic":"Agent skill discovery","domain":"LLM agents"}\n', encoding="utf-8")
    csv_path = tmp_path / "results.csv"
    jsonl_path = tmp_path / "results.jsonl"
    package_dir = tmp_path / "packages"
    pairwise_dir = tmp_path / "pairwise"
    run_benchmark(
        topics_path=topics,
        output_csv=csv_path,
        output_jsonl=jsonl_path,
        systems=["firstresearch", "no_certificate_ablation", "certificate_only_ablation"],
        package_dir=package_dir,
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/export_pairwise_review_packet.py",
            "--results",
            str(csv_path),
            "--output-dir",
            str(pairwise_dir),
            "--reference-system",
            "firstresearch",
            "--comparison-systems",
            "no_certificate_ablation",
            "certificate_only_ablation",
            "--seed",
            "11",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert (pairwise_dir / "pairwise_instructions.md").exists()
    assert (pairwise_dir / "pair_assignments_private.json").exists()
    pair_files = sorted(pairwise_dir.glob("PW*.md"))
    assert len(pair_files) == 2
    pair_text = pair_files[0].read_text(encoding="utf-8")
    assert "Package A" in pair_text
    assert "Package B" in pair_text
    assert "Decision: prefer A / prefer B / tie / cannot judge" in pair_text
    assert "firstresearch" not in pair_text.lower()

    decisions_path = tmp_path / "pairwise_decisions.csv"
    decisions_path.write_text("pair_id,decision\nPW0001,prefer_a\nPW0002,tie\n", encoding="utf-8")
    report_path = tmp_path / "pairwise_report.md"
    table_path = tmp_path / "pairwise_summary.csv"
    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_pairwise_review.py",
            "--assignments",
            str(pairwise_dir / "pair_assignments_private.json"),
            "--decisions",
            str(decisions_path),
            "--output",
            str(report_path),
            "--table-output",
            str(table_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report_text = report_path.read_text(encoding="utf-8")
    assert "Pairwise Human Review Report" in report_text
    assert "Win Rate" in report_text
    assert "Preference Score" in report_text
    assert table_path.exists()


def test_generate_repro_appendix(tmp_path: Path):
    output = tmp_path / "appendix.md"
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_repro_appendix.py",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    text = output.read_text(encoding="utf-8")
    assert "Reproducibility Appendix" in text
    assert "configs/deepseek_strong_baselines.yaml" in text
    assert "configs/deepseek_ablation_repeated.yaml" in text
    assert "configs/deepseek_ablation_repeated_crossjudge.yaml" in text
    assert "configs/deepseek_stress_generalization.yaml" in text
    assert "firstresearch/prompts/certificate_repairer.md" in text


def test_analyze_repeated_results(tmp_path: Path):
    results = tmp_path / "repeated.csv"
    results.write_text(
        "run_id,topic_id,topic,system,replicate,passed_gate,first_principles_derivation,falsifiability,mechanism_clarity,novelty,experimentability,average_score,review_score,recommendation,output_path\n"
        "r,T1,Topic,firstresearch,1,True,5,5,5,5,5,5.0,9,accept,p1.json\n"
        "r,T1,Topic,baseline,1,True,4,5,4,3,5,4.2,8,weak_accept,p2.json\n"
        "r,T1,Topic,firstresearch,2,True,4,5,5,4,5,4.6,8,weak_accept,p3.json\n"
        "r,T1,Topic,baseline,2,True,3,4,4,3,4,3.6,7,borderline,p4.json\n",
        encoding="utf-8",
    )
    output = tmp_path / "stability.md"
    table = tmp_path / "stability.csv"
    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_repeated_results.py",
            "--results",
            str(results),
            "--output",
            str(output),
            "--table-output",
            str(table),
            "--reference-system",
            "firstresearch",
            "--bootstrap-samples",
            "20",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    text = output.read_text(encoding="utf-8")
    assert "Repeated Benchmark Stability Analysis" in text
    assert "95% Bootstrap CI" in text
    assert "baseline" in text
    table_text = table.read_text(encoding="utf-8")
    assert "average_score_delta_vs_firstresearch" in table_text


def test_analyze_judge_agreement(tmp_path: Path):
    header = (
        "run_id,topic_id,topic,system,replicate,passed_gate,first_principles_derivation,"
        "falsifiability,mechanism_clarity,novelty,experimentability,average_score,review_score,"
        "recommendation,output_path\n"
    )
    primary = tmp_path / "primary.csv"
    secondary = tmp_path / "secondary.csv"
    primary.write_text(
        header
        + "p,T1,Topic,firstresearch,1,True,5,5,5,5,5,5.0,9,accept,p1.json\n"
        + "p,T1,Topic,baseline,1,True,4,4,4,4,4,4.0,7,borderline,p2.json\n",
        encoding="utf-8",
    )
    secondary.write_text(
        header
        + "s,T1,Topic,firstresearch,1,True,4,4,4,4,4,4.0,7,weak_accept,p1.json\n"
        + "s,T1,Topic,baseline,1,True,5,5,5,5,5,5.0,9,accept,p2.json\n",
        encoding="utf-8",
    )
    output = tmp_path / "judge_agreement.md"
    table = tmp_path / "judge_agreement.csv"
    subprocess.run(
        [
            sys.executable,
            "scripts/analyze_judge_agreement.py",
            "--primary-results",
            str(primary),
            "--secondary-results",
            str(secondary),
            "--output",
            str(output),
            "--table-output",
            str(table),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    text = output.read_text(encoding="utf-8")
    assert "Judge Agreement Analysis" in text
    assert "Within-Topic Rank Stability" in text
    assert "Top-System Match Rate" in text
    assert table.exists()


def test_claim_evidence_audit_modes(tmp_path: Path):
    evidence = tmp_path / "evidence.json"
    evidence.write_text(
        '[{"id":"strong_baseline_csv","passed":true},'
        '{"id":"strong_baseline_report","passed":true},'
        '{"id":"strong_baseline_metadata","passed":true},'
        '{"id":"strong_baseline_gemini_csv","passed":true},'
        '{"id":"strong_baseline_gemini_agreement_report","passed":true},'
        '{"id":"ablation_checkpoint_csv","passed":true},'
        '{"id":"ablation_checkpoint_report","passed":true},'
        '{"id":"repeated_ablation_csv","passed":false},'
        '{"id":"repeated_stability_report","passed":false},'
        '{"id":"crossjudge_csv","passed":true},'
        '{"id":"crossjudge_agreement_report","passed":true},'
        '{"id":"stress_generalization_csv","passed":false},'
        '{"id":"stress_generalization_report","passed":false},'
        '{"id":"human_scalar_report","passed":false},'
        '{"id":"human_pairwise_report","passed":false}]',
        encoding="utf-8",
    )
    manuscript = tmp_path / "paper.md"
    manuscript.write_text(
        "This preliminary Gemini-2.5-Flash cross-check uses prompt-level baseline comparisons. "
        "It needs replicates and human review. The one-repeat certificate-only ablation is supported, "
        "but the full three-replicate submission-readiness study is not yet complete. "
        "Reviewer/meta layers are not yet shown to improve. "
        "We include a Gemini independent-judge rescore, a stress benchmark for whether it overfits LLM-agent topics, "
        "and LLM judging is not a substitute for human expert review.",
        encoding="utf-8",
    )
    output = tmp_path / "claim_audit.md"
    json_output = tmp_path / "claim_audit.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/audit_claim_evidence.py",
            "--registry",
            "papers/claim_evidence_registry.yaml",
            "--evidence-audit",
            str(evidence),
            "--manuscript",
            str(manuscript),
            "--output",
            str(output),
            "--json-output",
            str(json_output),
            "--strict",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Claim-Evidence Audit" in output.read_text(encoding="utf-8")

    failed = subprocess.run(
        [
            sys.executable,
            "scripts/audit_claim_evidence.py",
            "--registry",
            "papers/claim_evidence_registry.yaml",
            "--evidence-audit",
            str(evidence),
            "--manuscript",
            str(manuscript),
            "--output",
            str(tmp_path / "claim_audit_submission.md"),
            "--json-output",
            str(tmp_path / "claim_audit_submission.json"),
            "--submission-ready",
            "--strict",
        ],
        capture_output=True,
        text=True,
    )
    assert failed.returncode == 1


def test_generate_submission_readiness_report(tmp_path: Path):
    evidence = tmp_path / "paper_evidence_audit.json"
    evidence.write_text(
        json.dumps(
            [
                {
                    "id": "strong_baseline_csv",
                    "description": "Strong baseline exists.",
                    "path": "outputs/reports/deepseek_strong_baselines_10topics.csv",
                    "required": True,
                    "passed": True,
                    "detail": "40 rows",
                },
                {
                    "id": "repeated_ablation_csv",
                    "description": "Repeated ablation exists.",
                    "path": "outputs/reports/deepseek_ablation_repeated_results.csv",
                    "required": False,
                    "passed": False,
                    "detail": "missing",
                },
            ]
        ),
        encoding="utf-8",
    )
    claims = tmp_path / "claim_evidence_audit.json"
    claims.write_text(
        json.dumps(
            [
                {
                    "id": "strong_baseline_claim",
                    "passed": True,
                    "missing_evidence": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    pipeline = tmp_path / "paper_evidence_pipeline_status.json"
    pipeline.write_text(
        json.dumps(
            {
                "statuses": [
                    {"stage": "repro_appendix", "status": "ran", "detail": "completed"},
                    {"stage": "repeated_ablation", "status": "skipped", "detail": "missing credentials"},
                ]
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "submission_readiness_report.md"
    json_output = tmp_path / "submission_readiness_report.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_submission_readiness_report.py",
            "--evidence-audit",
            str(evidence),
            "--claim-audit",
            str(claims),
            "--pipeline-status",
            str(pipeline),
            "--output",
            str(output),
            "--json-output",
            str(json_output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    text = output.read_text(encoding="utf-8")
    assert "Submission Readiness Report" in text
    assert "Submission ready: `false`" in text
    assert "repeated_ablation_csv" in text
    assert "python scripts/run_paper_evidence_pipeline.py" in text
    data = json.loads(json_output.read_text(encoding="utf-8"))
    assert data["submission_ready"] is False
    assert data["optional_missing"][0]["id"] == "repeated_ablation_csv"


def test_audit_package_artifacts(tmp_path: Path):
    topics = tmp_path / "topics.jsonl"
    topics.write_text('{"topic_id":"T1","topic":"Agent skill discovery","domain":"LLM agents"}\n', encoding="utf-8")
    csv_path = tmp_path / "results.csv"
    package_dir = tmp_path / "packages"
    run_benchmark(
        topics_path=topics,
        output_csv=csv_path,
        systems=["firstresearch", "co_scientist"],
        package_dir=package_dir,
    )

    output = tmp_path / "package_audit.md"
    json_output = tmp_path / "package_audit.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/audit_package_artifacts.py",
            "--results",
            str(csv_path),
            "--output",
            str(output),
            "--json-output",
            str(json_output),
            "--strict",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    text = output.read_text(encoding="utf-8")
    assert "Package Artifact Audit" in text
    assert "Failed rows: 0" in text
    assert json_output.exists()


def test_audit_results_table(tmp_path: Path):
    results = tmp_path / "results.csv"
    results.write_text(
        "topic_id,topic,system,passed_gate,first_principles_derivation,falsifiability,mechanism_clarity,novelty,experimentability,average_score,review_score,recommendation,output_path\n"
        "T1,Topic,firstresearch,True,5,5,5,5,5,5.0,9,accept,p1.json\n"
        "T1,Topic,tree_search_scientist,True,4,5,4,4,5,4.4,8,accept,p2.json\n"
        "T1,Topic,co_scientist,True,4,5,4,4,5,4.4,8,accept,p3.json\n"
        "T1,Topic,agent_lab,True,3,5,4,3,5,4.0,7,borderline,p4.json\n",
        encoding="utf-8",
    )
    manuscript = tmp_path / "paper.md"
    manuscript.write_text(
        "**Table 1: Strong-baseline comparison on ten LLM-agent topics. Higher is better.**\n\n"
        "| System | Derivation | Falsifiability | Mechanism | Novelty | Experimentability | Avg | Review |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|\n"
        "| FirstResearch | **5.00** | 5.00 | **5.00** | **5.00** | 5.00 | **5.00** | **9.00** |\n"
        "| TreeSearchScientist | 4.00 | **5.00** | 4.00 | 4.00 | **5.00** | 4.40 | 8.00 |\n"
        "| CoScientist | 4.00 | 5.00 | 4.00 | 4.00 | 5.00 | 4.40 | 8.00 |\n"
        "| AgentLab | 3.00 | 5.00 | 4.00 | 3.00 | 5.00 | 4.00 | 7.00 |\n\n",
        encoding="utf-8",
    )
    output = tmp_path / "table_audit.md"
    json_output = tmp_path / "table_audit.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/audit_results_table.py",
            "--results",
            str(results),
            "--manuscript",
            str(manuscript),
            "--output",
            str(output),
            "--json-output",
            str(json_output),
            "--strict",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Failures: 0" in output.read_text(encoding="utf-8")

    drifted = manuscript.read_text(encoding="utf-8").replace("| AgentLab | 3.00", "| AgentLab | 4.00")
    manuscript.write_text(drifted, encoding="utf-8")
    failed = subprocess.run(
        [
            sys.executable,
            "scripts/audit_results_table.py",
            "--results",
            str(results),
            "--manuscript",
            str(manuscript),
            "--output",
            str(tmp_path / "table_audit_failed.md"),
            "--strict",
        ],
        capture_output=True,
        text=True,
    )
    assert failed.returncode == 1


def test_generate_baseline_fidelity_report(tmp_path: Path):
    output = tmp_path / "baseline_fidelity.md"
    json_output = tmp_path / "baseline_fidelity.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_baseline_fidelity_report.py",
            "--config",
            "configs/deepseek_strong_baselines.yaml",
            "--output",
            str(output),
            "--json-output",
            str(json_output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    text = output.read_text(encoding="utf-8")
    assert "Baseline Fidelity Report" in text
    assert "controlled prompt-level workflow approximations" in text
    assert "Omitted elements" in text
    assert "co_scientist" in text
    assert "tree_search_scientist" in text
    assert json_output.exists()


def test_audit_references(tmp_path: Path):
    manuscript = tmp_path / "paper.md"
    manuscript.write_text(
        "The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery arXiv:2408.06292 "
        "https://arxiv.org/abs/2408.06292 The AI Scientist executes experiments with an automated reviewer. "
        "Towards an AI co-scientist arXiv:2502.18864 https://arxiv.org/abs/2502.18864 "
        "AI co-scientist uses generation, debate, ranking, and evolution. "
        "Agent Laboratory: Using LLM Agents as Research Assistants arXiv:2501.04227 "
        "https://arxiv.org/abs/2501.04227 Agent Laboratory uses literature review, experimentation, and report writing. "
        "The AI Scientist-v2: Workshop-Level Automated Scientific Discovery via Agentic Tree Search arXiv:2504.08066 "
        "https://arxiv.org/abs/2504.08066 AI Scientist-v2 uses agentic tree search.",
        encoding="utf-8",
    )
    output = tmp_path / "reference_audit.md"
    json_output = tmp_path / "reference_audit.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/audit_references.py",
            "--registry",
            "papers/reference_registry.yaml",
            "--manuscript",
            str(manuscript),
            "--output",
            str(output),
            "--json-output",
            str(json_output),
            "--strict",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    text = output.read_text(encoding="utf-8")
    assert "Reference Audit" in text
    assert "gottweis2025coscientist" in text
    assert json_output.exists()


def test_generate_human_review_protocol(tmp_path: Path):
    output = tmp_path / "human_review_protocol.md"
    json_output = tmp_path / "human_review_protocol.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_human_review_protocol.py",
            "--output",
            str(output),
            "--json-output",
            str(json_output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    text = output.read_text(encoding="utf-8")
    assert "Blinded Human Review Protocol" in text
    assert "Pairwise Decision CSV" in text
    assert "Do not upgrade paper claims" in text
    assert json_output.exists()


def test_paper_evidence_pipeline_dry_run(tmp_path: Path):
    status_path = tmp_path / "pipeline_status.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/run_paper_evidence_pipeline.py",
            "--dry-run",
            "--skip-credentialed",
            "--output-status",
            str(status_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert str(status_path) in completed.stdout
    data = status_path.read_text(encoding="utf-8")
    assert "repeated_ablation" in data
    assert "paper_evidence_audit" in data
    assert '"status": "failed"' not in data


def test_audit_paper_evidence_runs(tmp_path: Path):
    manifest_path = tmp_path / "manifest.json"
    manifest_md = tmp_path / "manifest.md"
    subprocess.run(
        [
            sys.executable,
            "scripts/generate_artifact_manifest.py",
            "--output",
            str(manifest_path),
            "--markdown-output",
            str(manifest_md),
            "--patterns",
            "configs/deepseek_strong_baselines.yaml",
            "papers/reproducibility_appendix.md",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = manifest_path.read_text(encoding="utf-8")
    assert "sha256" in manifest
    assert manifest_md.exists()

    output = tmp_path / "audit.md"
    json_output = tmp_path / "audit.json"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/audit_paper_evidence.py",
            "--output",
            str(output),
            "--json-output",
            str(json_output),
            "--strict",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert str(output) in completed.stdout
    text = output.read_text(encoding="utf-8")
    assert "Paper Evidence Audit" in text
    assert "strong_baseline_csv" in text
    assert json_output.exists()

    help_text = subprocess.run(
        [sys.executable, "scripts/audit_paper_evidence.py", "--help"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "--require-optional" in help_text


def test_co_scientist_baseline_produces_certificate():
    baseline = get_baselines(["co_scientist"], llm_baselines=True)[0]
    package = baseline.run(ResearchTopic(topic="Agent skill discovery"))
    assert package.certificates
    assert package.gate_decisions[0].passed
    assert package.metadata["baseline"] == "co_scientist"


def test_tree_search_scientist_baseline_produces_certificate():
    baseline = get_baselines(["tree_search_scientist"], llm_baselines=True)[0]
    package = baseline.run(ResearchTopic(topic="Agent skill discovery"))
    assert package.certificates
    assert package.gate_decisions[0].passed
    assert package.metadata["baseline"] == "tree_search_scientist"
    assert package.metadata["selection"]["selected_branch_id"]


def test_firstresearch_ablation_systems_are_registered():
    names = [
        "no_gate_repair_ablation",
        "no_novelty_boundary_repair_ablation",
        "no_mechanism_model_ablation",
        "certificate_only_ablation",
        "no_self_improvement_ablation",
        "firstresearch_debate_combo",
    ]
    baselines = get_baselines(names)
    assert [baseline.name for baseline in baselines] == names


def test_no_gate_repair_ablation_disables_repairs():
    baseline = get_baselines(["no_gate_repair_ablation"])[0]
    package = baseline.run(ResearchTopic(topic="Agent skill discovery"))
    assert package.metadata["ablation"] == "gate_repair_removed"
    assert package.metadata["ablation_settings"]["enable_gate_repair"] is False
    assert package.metadata["gate_repair_count"] == 0


def test_no_mechanism_model_ablation_uses_placeholder_mechanism():
    baseline = get_baselines(["no_mechanism_model_ablation"])[0]
    package = baseline.run(ResearchTopic(topic="Agent skill discovery"))
    assert package.metadata["ablation"] == "mechanism_builder_removed"
    assert package.metadata["ablation_settings"]["enable_mechanism_builder"] is False
    assert "Mechanism-builder ablation" in package.mechanism_model.mechanism_summary


def test_firstresearch_debate_combo_refines_questions():
    baseline = get_baselines(["firstresearch_debate_combo"])[0]
    package = baseline.run(ResearchTopic(topic="Agent skill discovery"))
    assert package.metadata["ablation"] == "co_scientist_debate_refinement_added"
    assert package.metadata["ablation_settings"]["enable_question_debate_refinement"] is True
    assert "library-interference threshold" in package.certificates[0].research_question.question


def test_certificate_only_ablation_removes_review_and_meta_steps():
    baseline = get_baselines(["certificate_only_ablation"])[0]
    package = baseline.run(ResearchTopic(topic="Agent skill discovery"))
    assert package.certificates
    assert package.review is None
    assert package.self_improvement_update is None
    assert package.metadata["ablation"] == "reviewer_and_meta_removed"


def test_gate_repair_suggestions_for_low_novelty():
    package = ResearchOrchestrator().run(ResearchTopic(topic="Agent skill discovery"))
    certificate = package.certificates[0].model_copy(
        update={
            "quality_scores": package.certificates[0].quality_scores.model_copy(update={"novelty": 2})
        }
    )
    decision = GateAgent().run(certificate)
    assert decision.passed
    assert any("novelty" in suggestion.lower() for suggestion in decision.repair_suggestions)


def test_gate_repair_suggestions_for_missing_boundary_signal():
    package = ResearchOrchestrator().run(ResearchTopic(topic="Agent skill discovery"))
    certificate = package.certificates[0].model_copy(
        update={
            "research_question": package.certificates[0].research_question.model_copy(
                update={"question": "When should an agent create a new skill?"}
            ),
            "hypothesis": package.certificates[0].hypothesis.model_copy(
                update={"statement": "The agent should create a new skill when it helps performance."}
            ),
            "quality_scores": package.certificates[0].quality_scores.model_copy(update={"novelty": 5}),
        }
    )
    decision = GateAgent().run(certificate)
    assert decision.passed
    assert any("boundary" in suggestion.lower() for suggestion in decision.repair_suggestions)


def test_certificate_rank_prefers_higher_quality_certificate():
    package = ResearchOrchestrator().run(ResearchTopic(topic="Agent skill discovery"))
    lower = package.certificates[0].model_copy(
        update={"quality_scores": package.certificates[0].quality_scores.model_copy(update={"novelty": 3})}
    )
    higher = package.certificates[0].model_copy(
        update={"quality_scores": package.certificates[0].quality_scores.model_copy(update={"novelty": 5})}
    )
    assert _certificate_rank_key(higher) > _certificate_rank_key(lower)
