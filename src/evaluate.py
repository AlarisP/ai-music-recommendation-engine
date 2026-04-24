"""Evaluation harness for reliability and guardrail checks.

Run with:
    python -m src.evaluate
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean
import json

try:
    from .ai_model import load_default_model
    from .main import USER_PROFILES
    from .recommender import load_songs, recommend_songs
except ImportError:
    from ai_model import load_default_model
    from main import USER_PROFILES
    from recommender import load_songs, recommend_songs


@dataclass
class EvalResult:
    name: str
    passed: bool
    detail: str


def run_evaluation() -> dict:
    songs = load_songs("data/songs.csv")
    model = load_default_model()
    results: list[EvalResult] = []
    confidence_values: list[float] = []

    scenarios = [
        ("alex", "advanced", 5),
        ("maya", "simple", 5),
        ("riley", "advanced", 5),
    ]

    for profile_name, mode, top_k in scenarios:
        profile = USER_PROFILES[profile_name]
        recs = recommend_songs(profile, songs, k=top_k, mode=mode)

        passed_count = len(recs) == top_k
        score_range_ok = all(0.0 <= item[1] <= 1.1 for item in recs)
        has_explanations = all("Feedback-trained model confidence" in item[2] for item in recs)

        for song, _, _ in recs:
            confidence_values.append(model.predict_probability(profile, song))

        passed = passed_count and score_range_ok and has_explanations
        detail = (
            f"{profile_name}/{mode}: returned={len(recs)}, "
            f"score_range_ok={score_range_ok}, explanations_with_confidence={has_explanations}"
        )
        results.append(EvalResult(name=f"scenario_{profile_name}_{mode}", passed=passed, detail=detail))

    # Learned model sanity check.
    liked_probability = model.predict_probability(
        USER_PROFILES["alex"],
        {
            "genre": "lofi",
            "mood": "chill",
            "energy": 0.35,
            "tempo_bpm": 72,
            "valence": 0.60,
            "danceability": 0.58,
            "acousticness": 0.86,
        },
    )
    skipped_probability = model.predict_probability(
        USER_PROFILES["alex"],
        {
            "genre": "metal",
            "mood": "angry",
            "energy": 0.96,
            "tempo_bpm": 168,
            "valence": 0.22,
            "danceability": 0.55,
            "acousticness": 0.06,
        },
    )
    results.append(
        EvalResult(
            name="learned_model_preference_order",
            passed=liked_probability > skipped_probability,
            detail=(
                f"liked_probability={liked_probability:.3f}, "
                f"skipped_probability={skipped_probability:.3f}"
            ),
        )
    )

    # Guardrail check: required fields validation.
    guardrail_triggered = False
    try:
        recommend_songs({"genre": "pop", "energy": 0.8, "likes_acoustic": False}, songs, k=3, mode="advanced")
    except ValueError:
        guardrail_triggered = True

    results.append(
        EvalResult(
            name="guardrail_missing_required_fields",
            passed=guardrail_triggered,
            detail="ValueError raised when mood was missing from user profile",
        )
    )

    passed_total = sum(1 for result in results if result.passed)
    failed_total = len(results) - passed_total
    avg_confidence = mean(confidence_values) if confidence_values else 0.0

    summary = {
        "total_checks": len(results),
        "passed": passed_total,
        "failed": failed_total,
        "average_confidence": round(avg_confidence, 4),
        "checks": [
            {"name": result.name, "passed": result.passed, "detail": result.detail}
            for result in results
        ],
    }
    return summary


def _write_report(summary: dict) -> Path:
    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    report_path = logs_dir / "evaluation_report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return report_path


def main() -> None:
    summary = run_evaluation()
    report_path = _write_report(summary)

    print("\n=== Evaluation Summary ===")
    print(f"Checks passed: {summary['passed']}/{summary['total_checks']}")
    print(f"Checks failed: {summary['failed']}")
    print(f"Average model confidence: {summary['average_confidence']:.3f}")
    print("\nPer-check details:")
    for check in summary["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"- [{status}] {check['name']}: {check['detail']}")
    print(f"\nSaved report: {report_path}")


if __name__ == "__main__":
    main()
