"""
Evaluation runner — measures pipeline performance against ground-truth NL/SQL pairs.
"""
import asyncio
import json
import time
from pathlib import Path

import sqlglot

DATASET_PATH = Path(__file__).parent / "eval_dataset.json"


def normalize_sql(sql: str) -> str:
    """Normalize SQL for exact-match comparison."""
    try:
        parsed = sqlglot.parse_one(sql, dialect="postgres")
        return parsed.sql(dialect="postgres", pretty=False).upper().strip()
    except Exception:
        return sql.upper().strip()


async def run_evaluation():
    """
    Runs the NL2SQL pipeline against every item in eval_dataset.json
    and prints a summary report.
    """
    from backend.core.schema_loader import schema_loader
    from backend.core.embedder import schema_embedder
    from backend.core.correction_loop import run_pipeline, MaxRetriesExceeded
    from backend.monitoring.metrics_tracker import init_log_db

    await init_log_db()
    schema = await schema_loader.load()
    schema_embedder.build_index(schema)

    dataset = json.loads(DATASET_PATH.read_text())

    results = {
        "total": 0,
        "valid_sql_count": 0,
        "exact_match_count": 0,
        "correction_triggered": 0,
        "failures": 0,
        "total_latency_ms": 0.0,
        "details": [],
    }

    print(f"\n🧪 Running evaluation on {len(dataset)} queries...\n")
    print("-" * 80)

    for item in dataset:
        qid = item["id"]
        nl_query = item["nl_query"]
        ground_truth = item["ground_truth_sql"]

        start = time.monotonic() * 1000
        status = "❌"
        generated_sql = ""
        correction = False

        try:
            pipeline = await run_pipeline(nl_query)
            generated_sql = pipeline.final_sql
            correction = pipeline.correction_triggered
            latency = time.monotonic() * 1000 - start
            status = "✅"
            results["valid_sql_count"] += 1

            # Exact match
            if normalize_sql(generated_sql) == normalize_sql(ground_truth):
                results["exact_match_count"] += 1

            if correction:
                results["correction_triggered"] += 1

        except MaxRetriesExceeded:
            latency = time.monotonic() * 1000 - start
            results["failures"] += 1
        except Exception as e:
            latency = time.monotonic() * 1000 - start
            results["failures"] += 1
            print(f"  [{qid}] Unexpected error: {e}")

        results["total"] += 1
        results["total_latency_ms"] += latency
        results["details"].append({
            "id": qid,
            "nl_query": nl_query,
            "generated_sql": generated_sql,
            "ground_truth": ground_truth,
            "status": status,
            "correction_triggered": correction,
            "latency_ms": round(latency, 1),
        })
        print(f"  [{qid:2d}] {status} {nl_query[:60]:<60} {latency:6.0f}ms")

    print("-" * 80)

    total = results["total"]
    valid = results["valid_sql_count"]
    exact = results["exact_match_count"]
    corrections = results["correction_triggered"]
    failures = results["failures"]
    avg_latency = results["total_latency_ms"] / total if total else 0

    print(f"\n📊 Evaluation Results")
    print(f"   Total Queries    : {total}")
    print(f"   Valid SQL        : {valid}/{total} = {100*valid/total:.1f}%")
    print(f"   Exact Match      : {exact}/{total} = {100*exact/total:.1f}%")
    print(f"   Correction Rate  : {corrections}/{total} = {100*corrections/total:.1f}%")
    print(f"   Failure Rate     : {failures}/{total} = {100*failures/total:.1f}%")
    print(f"   Avg Latency      : {avg_latency:.0f} ms\n")

    # Save detailed results
    out_path = Path(__file__).parent / "eval_results.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"✅ Full results saved to: {out_path}\n")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
