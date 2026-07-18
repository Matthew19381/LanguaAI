"""SCI-5: data-driven 'best time of day to study' analysis.

Instead of assuming a universal peak hour (which ignores individual chronotype —
the synchrony effect; May & Hasher 1998; Goldstein et al. 2007), we look at when
THIS learner actually performs best, using their timestamped test scores.
"""
from typing import Optional

# Time-of-day buckets (local hour). Night wraps midnight.
_BUCKETS = [
    ("morning", range(5, 12)),     # 05:00–11:59
    ("afternoon", range(12, 17)),  # 12:00–16:59
    ("evening", range(17, 22)),    # 17:00–21:59
]
# Minimum scored events needed before we offer a recommendation at all.
MIN_SAMPLES = 8
# Minimum events within a bucket before that bucket can be "the best".
MIN_PER_BUCKET = 3


def bucket_for_hour(hour: int) -> str:
    """Map an hour (0-23) to a named time-of-day bucket."""
    for name, hours in _BUCKETS:
        if hour in hours:
            return name
    return "night"  # 22:00–04:59


def analyze_best_study_time(
    samples: list[tuple[int, float]],
    min_total: int = MIN_SAMPLES,
) -> dict:
    """Aggregate (hour, score) samples into per-bucket average performance.

    Returns a dict with per-bucket stats, whether there is enough data, and the
    best-performing bucket (only among buckets with >= MIN_PER_BUCKET samples).
    """
    buckets: dict[str, dict] = {
        name: {"n": 0, "total_score": 0.0}
        for name, _ in _BUCKETS
    }
    buckets["night"] = {"n": 0, "total_score": 0.0}

    for hour, score in samples:
        b = buckets[bucket_for_hour(hour)]
        b["n"] += 1
        b["total_score"] += score

    for b in buckets.values():
        b["avg_score"] = round(b["total_score"] / b["n"], 1) if b["n"] else None
        b.pop("total_score")

    total = sum(b["n"] for b in buckets.values())
    enough = total >= min_total

    best: Optional[str] = None
    if enough:
        eligible = {
            name: b["avg_score"]
            for name, b in buckets.items()
            if b["n"] >= MIN_PER_BUCKET and b["avg_score"] is not None
        }
        if eligible:
            best = max(eligible, key=eligible.get)

    return {
        "enough_data": enough,
        "samples": total,
        "min_samples": min_total,
        "buckets": buckets,
        "best_bucket": best,
    }
