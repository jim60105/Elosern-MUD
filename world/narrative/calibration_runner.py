"""Offline calibration runner and metrics evaluation for Fast Recall.

Evaluates:
- Recall@1
- Recall@2
- False Positive Rate
- Latency (p50, p95, max in milliseconds)
Generates a calibrated calibration report.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any

from world.narrative.calibration_corpus import (
    CALIBRATION_TEST_CASES,
    SYNTHETIC_CALIBRATION_CORPUS,
    LabeledTestCase,
)
from world.narrative.memory import (
    MemoryRecord,
    MemoryRevision,
    record_memory,
    revise_memory,
    supersede_memory,
)
from world.narrative.ranker import (
    DEFAULT_B,
    DEFAULT_K1,
    MIN_LEXICAL_THRESHOLD,
    RANKER_VERSION,
)
from world.narrative.recall import fast_recall
from world.narrative.tokenizer import TOKENIZER_VERSION


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    query: str
    owner_id: str
    recalled_source_ids: tuple[str, ...]
    expected_top_source_ids: tuple[str, ...]
    hit_top1: bool
    hit_top2: bool
    false_positive: bool
    latency_ms: float
    notes: str


@dataclass(frozen=True)
class CalibrationMetrics:
    total_cases: int
    positive_cases: int
    negative_cases: int
    recall_at_1: float
    recall_at_2: float
    false_positive_count: int
    false_positive_rate: float
    min_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    max_latency_ms: float


@dataclass(frozen=True)
class CalibrationReport:
    report_version: str
    tokenizer_version: str
    ranker_version: str
    min_lexical_threshold: float
    bm25_k1: float
    bm25_b: float
    corpus_size: int
    environment: dict[str, str]
    metrics: CalibrationMetrics
    calibrated_gates: dict[str, float]
    cases: list[CaseResult]


def populate_synthetic_corpus() -> None:
    """Load the synthetic calibration corpus into the test/in-memory database."""
    supersede_pairs: list[tuple[str, str]] = []
    inactive_sources: list[str] = []

    for item in SYNTHETIC_CALIBRATION_CORPUS:
        source_id = item["source_id"]
        # Check if already exists
        if MemoryRecord.objects.filter(source_id=source_id).exists():
            continue

        rec, rev, _ = record_memory(
            owner_id=item["owner_id"],
            tick=item["tick"],
            category=item["category"],
            content=item["content"],
            salience=item["salience"],
            knowledge_scope=item.get("knowledge_scope", "witnessed"),
            confidence=item.get("confidence", 1.0),
            subjects=item.get("subjects", [item["owner_id"]]),
            tier=item.get("tier", "working"),
            source_id=source_id,
        )

        if item.get("superseded", False):
            supersede_pairs.append((source_id, item.get("superseded_by", "corpus:courier:active:new")))
        if item.get("inactive", False):
            inactive_sources.append(source_id)

    for old_src, new_src in supersede_pairs:
        old_rec = MemoryRecord.objects.filter(source_id=old_src).first()
        new_rec = MemoryRecord.objects.filter(source_id=new_src).first()
        if old_rec and new_rec and old_rec.effective_availability != "superseded":
            supersede_memory(old_record=old_rec, new_record=new_rec)

    for inact_src in inactive_sources:
        rec = MemoryRecord.objects.filter(source_id=inact_src).first()
        if rec and rec.effective_availability != "inactive":
            revise_memory(record=rec, availability="inactive")


def run_calibration() -> CalibrationReport:
    """Run calibration over all labeled test cases and calculate metrics."""
    populate_synthetic_corpus()

    case_results: list[CaseResult] = []
    latencies: list[float] = []

    for tc in CALIBRATION_TEST_CASES:
        t0 = time.monotonic()
        res = fast_recall(
            owner_id=tc.owner_id,
            query=tc.query,
            include_superseded=tc.include_superseded,
            include_inactive=tc.include_inactive,
            limit=5,
        )
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        latencies.append(elapsed_ms)

        recalled_ids = tuple(sm.view.source_id for sm in res.recalled)

        # Check hits
        hit_top1 = False
        hit_top2 = False
        if tc.expected_top_source_ids:
            target = tc.expected_top_source_ids[0]
            if len(recalled_ids) >= 1 and recalled_ids[0] == target:
                hit_top1 = True
            if target in recalled_ids[:2]:
                hit_top2 = True

        # Check false positive: returned forbidden or returned results when should be empty
        false_positive = False
        if tc.should_be_empty and len(recalled_ids) > 0:
            false_positive = True
        for fid in tc.forbidden_source_ids:
            if fid in recalled_ids:
                false_positive = True

        case_results.append(
            CaseResult(
                case_id=tc.case_id,
                query=tc.query,
                owner_id=tc.owner_id,
                recalled_source_ids=recalled_ids,
                expected_top_source_ids=tc.expected_top_source_ids,
                hit_top1=hit_top1,
                hit_top2=hit_top2,
                false_positive=false_positive,
                latency_ms=round(elapsed_ms, 3),
                notes=tc.notes,
            )
        )

    # Compute aggregate metrics
    latencies.sort()
    total_cases = len(case_results)
    pos_cases = [c for c in case_results if c.expected_top_source_ids]
    neg_cases = [c for c in case_results if not c.expected_top_source_ids]

    r1 = (sum(1 for c in pos_cases if c.hit_top1) / len(pos_cases)) if pos_cases else 1.0
    r2 = (sum(1 for c in pos_cases if c.hit_top2) / len(pos_cases)) if pos_cases else 1.0
    fp_count = sum(1 for c in case_results if c.false_positive)
    fp_rate = fp_count / total_cases if total_cases else 0.0

    p50_idx = int(0.50 * (len(latencies) - 1))
    p95_idx = int(0.95 * (len(latencies) - 1))

    metrics = CalibrationMetrics(
        total_cases=total_cases,
        positive_cases=len(pos_cases),
        negative_cases=len(neg_cases),
        recall_at_1=round(r1, 4),
        recall_at_2=round(r2, 4),
        false_positive_count=fp_count,
        false_positive_rate=round(fp_rate, 4),
        min_latency_ms=round(latencies[0], 3) if latencies else 0.0,
        p50_latency_ms=round(latencies[p50_idx], 3) if latencies else 0.0,
        p95_latency_ms=round(latencies[p95_idx], 3) if latencies else 0.0,
        max_latency_ms=round(latencies[-1], 3) if latencies else 0.0,
    )

    # Calibrated gates based on measured performance:
    # - Recall@1 >= 0.95 (we expect 1.0 on positive cases)
    # - Recall@2 >= 1.0
    # - False Positive Rate == 0.0
    # - p95 Latency <= 50.0 ms
    calibrated_gates = {
        "min_recall_at_1": 0.95,
        "min_recall_at_2": 1.00,
        "max_false_positive_rate": 0.00,
        "max_p95_latency_ms": 50.0,
    }

    env_info = {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "arch": platform.machine(),
    }

    return CalibrationReport(
        report_version="1.0.0",
        tokenizer_version=TOKENIZER_VERSION,
        ranker_version=RANKER_VERSION,
        min_lexical_threshold=MIN_LEXICAL_THRESHOLD,
        bm25_k1=DEFAULT_K1,
        bm25_b=DEFAULT_B,
        corpus_size=len(SYNTHETIC_CALIBRATION_CORPUS),
        environment=env_info,
        metrics=metrics,
        calibrated_gates=calibrated_gates,
        cases=case_results,
    )


def save_calibration_report(report: CalibrationReport, filepath: str) -> None:
    """Serialize calibration report to JSON file."""
    data = asdict(report)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    report = run_calibration()
    out_path = os.path.join(
        os.path.dirname(__file__), "calibration_report.json"
    )
    save_calibration_report(report, out_path)
    print(f"Calibration completed: Recall@1={report.metrics.recall_at_1}, FP={report.metrics.false_positive_count}")
    print(f"Report saved to {out_path}")
