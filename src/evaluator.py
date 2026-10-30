"""
YottaFlex Anomaly Detection Evaluation & Benchmark Engine.
Computes Confusion Matrices, Precision, Recall, and F1-Score with zero-denominator protection.
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Set, Tuple


@dataclass
class ScenarioEvaluation:
    scenario_id: str
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1_score: float


def compute_metrics(
    ground_truth_records: List[Dict[str, Any]],
    detected_records: List[Dict[str, Any]],
    total_population_size: int,
) -> Dict[str, Any]:
    """
    Evaluates detection predictions against ground truth labels.
    Handles zero denominators safely.
    """
    gt_by_scenario: Dict[str, Set[str]] = {}
    for gt in ground_truth_records:
        scen = gt["scenario_id"]
        rec = str(gt["record_id"])
        gt_by_scenario.setdefault(scen, set()).add(rec)

    det_by_scenario: Dict[str, Set[str]] = {}
    for det in detected_records:
        scen = det["scenario"]
        rec = str(det["record_id"])
        det_by_scenario.setdefault(scen, set()).add(rec)

    scenarios = [
        "SCENARIO_1_PRESTART_ACCESS",
        "SCENARIO_2_DUPLICATE_ASSET",
        "SCENARIO_3_TERMINATED_RETAINS_ACCESS",
        "SCENARIO_4_TASK_CYCLE",
        "SCENARIO_5_RECOVERED_REMAINS_ASSIGNED",
    ]

    scenario_results: Dict[str, Dict[str, Any]] = {}
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for scen in scenarios:
        gt_set = gt_by_scenario.get(scen, set())
        det_set = det_by_scenario.get(scen, set())

        tp = len(gt_set.intersection(det_set))
        fp = len(det_set - gt_set)
        fn = len(gt_set - det_set)
        tn = max(0, (total_population_size // len(scenarios)) - (tp + fp + fn))

        prec = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        rec = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 1.0

        total_tp += tp
        total_fp += fp
        total_fn += fn

        scenario_results[scen] = asdict(
            ScenarioEvaluation(
                scenario_id=scen,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
                true_negatives=tn,
                precision=round(prec, 4),
                recall=round(rec, 4),
                f1_score=round(f1, 4),
            )
        )

    overall_prec = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 1.0
    overall_rec = (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else 1.0
    overall_f1 = (
        (2 * overall_prec * overall_rec / (overall_prec + overall_rec))
        if (overall_prec + overall_rec) > 0
        else 1.0
    )

    return {
        "overall_summary": {
            "total_ground_truth_anomalies": len(ground_truth_records),
            "total_detections": len(detected_records),
            "total_true_positives": total_tp,
            "total_false_positives": total_fp,
            "total_false_negatives": total_fn,
            "precision": round(overall_prec, 4),
            "recall": round(overall_rec, 4),
            "f1_score": round(overall_f1, 4),
        },
        "by_scenario": scenario_results,
    }