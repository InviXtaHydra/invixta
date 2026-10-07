"""Evaluate the RAG pipeline on scripts/eval/rag_eval_dataset.json with real measurements.

    docker compose exec backend python scripts/evaluate_rag.py
    docker compose exec backend python scripts/evaluate_rag.py --output /tmp/report.json

Retrieval metrics always run (local embeddings + pgvector, no API key needed):
  hit@k              an expected document is among the top-k chunks (ranking only, no threshold)
  MRR                mean reciprocal rank of the first chunk from an expected document
  context precision  share of relevant (above-threshold) chunks that come from an expected document
  fact coverage      share of required facts present in the retrieved context — can the LLM answer at all?
  abstention         unanswerable questions where nothing passes the threshold (so we say "not found")
  threshold sweep    coverage of answerable vs. abstention on unanswerable questions per threshold

Answer metrics need ANTHROPIC_API_KEY (otherwise they're reported as skipped):
  answer correctness every required fact appears in the generated answer
  abstention         unanswerable questions answered with the not-found message
  latency            end-to-end p50/p95

The documents in sample_documents/ must be indexed first (scripts/ingest_documents.py).
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.llm import get_llm
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.rag.embeddings import get_embedder
from app.rag.rag_service import RagService, is_not_found
from app.rag.retrieval import KnowledgeBaseSearch

DATASET = Path(__file__).resolve().parent / "eval" / "rag_eval_dataset.json"
TOP_K = 5


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[index]


def contains(text: str, fact: str) -> bool:
    return fact.lower() in text.lower()


def share(rows: list[dict[str, Any]], predicate: Any) -> float | None:
    """Fraction of rows for which predicate(row) is true, rounded; None for an empty list."""
    return round(sum(bool(predicate(r)) for r in rows) / len(rows), 3) if rows else None


def evaluate_retrieval(questions: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    embedder = get_embedder()
    embedder.embed_query("warm-up")  # load the model before timing anything
    rows = []
    with SessionLocal() as db:
        search = KnowledgeBaseSearch(db, embedder)
        for q in questions:
            started = time.perf_counter()
            ranked = search.search(q["question"], top_k=TOP_K, min_score=0.0)  # full ranking, threshold applied below
            latency = (time.perf_counter() - started) * 1000
            relevant = [c for c in ranked if c.score >= threshold]
            expected = set(q["expected_documents"])
            rank = next((i for i, c in enumerate(ranked, start=1) if c.filename in expected), None) if expected else None
            context = " ".join(c.content for c in relevant)
            rows.append(
                {
                    "id": q["id"],
                    "answerable": bool(expected),
                    "best_score": round(ranked[0].score, 3) if ranked else 0.0,
                    "top_document": ranked[0].filename if ranked else None,
                    "rank": rank,
                    "precision": (sum(c.filename in expected for c in relevant) / len(relevant)) if expected and relevant else None,
                    "fact_coverage": (sum(contains(context, f) for f in q["facts"]) / len(q["facts"])) if q["facts"] else None,
                    "abstained": not relevant,
                    "latency_ms": round(latency, 1),
                }
            )

    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]

    def hit(k: int) -> float:
        return float(sum(r["rank"] is not None and r["rank"] <= k for r in answerable) / len(answerable))

    sweep = []
    for t in [0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68, 0.70]:
        sweep.append(
            {
                "threshold": t,
                "answerable_retrieved": share(answerable, lambda r, t=t: r["best_score"] >= t),
                "unanswerable_abstained": share(unanswerable, lambda r, t=t: r["best_score"] < t),
            }
        )
    precisions = [r["precision"] for r in answerable if r["precision"] is not None]
    coverages = [r["fact_coverage"] for r in answerable if r["fact_coverage"] is not None]
    latencies = [r["latency_ms"] for r in rows]
    return {
        "threshold": threshold,
        "top_k": TOP_K,
        "questions": len(rows),
        "answerable": len(answerable),
        "unanswerable": len(unanswerable),
        "hit@1": round(hit(1), 3),
        "hit@3": round(hit(3), 3),
        "hit@5": round(hit(5), 3),
        "mrr": round(sum(1 / r["rank"] for r in answerable if r["rank"]) / len(answerable), 3),
        "context_precision": round(statistics.mean(precisions), 3) if precisions else None,
        "fact_coverage": round(statistics.mean(coverages), 3) if coverages else None,
        "answerable_retrieved": round(sum(not r["abstained"] for r in answerable) / len(answerable), 3),
        "unanswerable_abstained": round(sum(r["abstained"] for r in unanswerable) / len(unanswerable), 3) if unanswerable else None,
        "latency_ms_p50": round(percentile(latencies, 0.5), 1),
        "latency_ms_p95": round(percentile(latencies, 0.95), 1),
        "threshold_sweep": sweep,
        "per_question": rows,
    }


def evaluate_answers(questions: list[dict[str, Any]]) -> dict[str, Any]:
    llm = get_llm()
    if llm is None:
        return {"skipped": "ANTHROPIC_API_KEY is not set, so no answers were generated."}
    rows = []
    with SessionLocal() as db:
        rag = RagService(db, get_embedder(), llm)
        for q in questions:
            started = time.perf_counter()
            result = rag.answer(q["question"])
            latency = (time.perf_counter() - started) * 1000
            if q["expected_documents"]:
                correct = result.answered and all(contains(result.answer, f) for f in q["facts"])
            else:
                correct = (not result.answered) or is_not_found(result.answer)
            rows.append(
                {
                    "id": q["id"],
                    "answerable": bool(q["expected_documents"]),
                    "correct": correct,
                    "answered": result.answered,
                    "cited": sorted({s.filename for s in result.sources}),
                    "latency_ms": round(latency),
                    "answer": result.answer,
                }
            )
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    latencies = [float(r["latency_ms"]) for r in rows]
    return {
        "model": llm.model,
        "answer_correctness": round(sum(r["correct"] for r in answerable) / len(answerable), 3),
        "abstention_accuracy": round(sum(r["correct"] for r in unanswerable) / len(unanswerable), 3) if unanswerable else None,
        "latency_ms_p50": round(percentile(latencies, 0.5)),
        "latency_ms_p95": round(percentile(latencies, 0.95)),
        "per_question": rows,
    }


def print_report(retrieval: dict[str, Any], answers: dict[str, Any]) -> None:
    r = retrieval
    print(f"\nRetrieval — {r['questions']} questions ({r['answerable']} answerable, {r['unanswerable']} unanswerable)")
    print(f"  top_k={r['top_k']}, threshold={r['threshold']}")
    for key in ["hit@1", "hit@3", "hit@5", "mrr", "context_precision", "fact_coverage", "answerable_retrieved", "unanswerable_abstained"]:
        print(f"  {key:<24}{r[key]}")
    print(f"  {'latency p50 / p95':<24}{r['latency_ms_p50']} ms / {r['latency_ms_p95']} ms")
    print("\n  threshold  answerable retrieved  unanswerable abstained")
    for row in r["threshold_sweep"]:
        print(f"  {row['threshold']:<9.2f}  {row['answerable_retrieved']:<20}  {row['unanswerable_abstained']}")
    misses = [q for q in r["per_question"] if q["answerable"] and (q["rank"] != 1 or q["abstained"])]
    if misses:
        print("\n  Answerable questions not retrieved at rank 1, or below the threshold:")
        for q in misses:
            print(f"    {q['id']:<6} rank={q['rank']} best_score={q['best_score']} top={q['top_document']}")
    leaks = [q for q in r["per_question"] if not q["answerable"] and not q["abstained"]]
    if leaks:
        print("\n  Unanswerable questions above the threshold (the LLM must then say it doesn't know):")
        for q in leaks:
            print(f"    {q['id']:<6} best_score={q['best_score']} top={q['top_document']}")
    print("\nAnswers")
    if "skipped" in answers:
        print(f"  skipped: {answers['skipped']}")
        return
    for key in ["model", "answer_correctness", "abstention_accuracy"]:
        print(f"  {key:<24}{answers[key]}")
    print(f"  {'latency p50 / p95':<24}{answers['latency_ms_p50']} ms / {answers['latency_ms_p95']} ms")
    for q in answers["per_question"]:
        if not q["correct"]:
            print(f"    wrong: {q['id']:<6} {q['answer'][:110]!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--threshold", type=float, default=get_settings().rag_min_score)
    parser.add_argument("--skip-answers", action="store_true", help="only run the retrieval part")
    parser.add_argument("--output", type=Path, help="write the full JSON report here")
    args = parser.parse_args()

    questions = json.loads(DATASET.read_text())["questions"]
    retrieval = evaluate_retrieval(questions, args.threshold)
    answers = {"skipped": "--skip-answers"} if args.skip_answers else evaluate_answers(questions)
    print_report(retrieval, answers)
    if args.output:
        args.output.write_text(json.dumps({"retrieval": retrieval, "answers": answers}, indent=2))
        print(f"\nFull report written to {args.output}")


if __name__ == "__main__":
    main()
