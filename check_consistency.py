"""
Consistency checker for the AI Music Recommendation Engine.

Run from the project root:
    python check_consistency.py

Exit code 0 = all checks passed
Exit code 1 = one or more checks failed

Checks:
  1. Determinism     — same profile always produces the same top-5 ranking
  2. Model quality   — each per-profile model scores liked songs above skipped songs
  3. Differentiation — different profiles produce meaningfully different top-5 lists
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.ai_model import _load_songs, _profile_to_user_prefs, train_model_for_profile
from src.recommender import load_songs, recommend_songs

SONGS_CSV = Path(__file__).parent / "data" / "songs.csv"
PROFILES_JSON = Path(__file__).parent / "docs" / "data" / "profiles.json"

PASS = "PASS"
FAIL = "FAIL"


def _user_prefs_from_profile(profile: dict) -> dict:
    return {
        "genre": profile["genre"],
        "mood": profile["mood"],
        "energy": profile["energy"],
        "tempo_bpm": profile["tempo_bpm"],
        "likes_acoustic": profile["likes_acoustic"],
        "favorite_genres": profile.get("favorite_genres", []),
        "recent_songs": [],
    }


def _top5_titles(profile: dict, songs: list) -> list[str]:
    results = recommend_songs(_user_prefs_from_profile(profile), songs, k=5, mode="advanced")
    return [r[0]["title"] for r in results]


# -- Check 1 ------------------------------------------------------------------

def check_determinism(profiles: list, songs: list) -> bool:
    """Same inputs must produce identical top-5 on every call."""
    print("\n-- CHECK 1: Determinism -----------------------------------------")
    all_passed = True

    for profile in profiles:
        runs = [_top5_titles(profile, songs) for _ in range(3)]
        passed = runs[0] == runs[1] == runs[2]
        label = PASS if passed else FAIL
        print(f"  [{label}] {profile['name']}: top-5 identical across 3 runs")
        if not passed:
            all_passed = False
            for i, run in enumerate(runs, 1):
                print(f"         Run {i}: {run}")

    return all_passed


# -- Check 2 ------------------------------------------------------------------

def check_model_quality(profiles: list, song_lookup: dict) -> bool:
    """Each profile's per-profile model must score liked songs above skipped songs on average."""
    print("\n-- CHECK 2: Per-Profile Model Quality ---------------------------")
    all_passed = True

    for profile in profiles:
        events = profile.get("feedback_events", [])
        liked = [song_lookup[e["song_id"]] for e in events
                 if e["action"] == "like" and e["song_id"] in song_lookup]
        skipped = [song_lookup[e["song_id"]] for e in events
                   if e["action"] == "skip" and e["song_id"] in song_lookup]

        if not liked or not skipped:
            print(f"  [SKIP] {profile['name']}: not enough feedback events")
            continue

        model = train_model_for_profile(profile)
        user_prefs = _profile_to_user_prefs(profile)

        avg_liked = sum(model.predict_probability(user_prefs, s) for s in liked) / len(liked)
        avg_skipped = sum(model.predict_probability(user_prefs, s) for s in skipped) / len(skipped)

        passed = avg_liked > avg_skipped
        label = PASS if passed else FAIL
        print(f"  [{label}] {profile['name']}: "
              f"avg liked={avg_liked:.3f}  avg skipped={avg_skipped:.3f}  "
              f"margin={avg_liked - avg_skipped:+.3f}")
        if not passed:
            all_passed = False

    return all_passed


# -- Check 3 ------------------------------------------------------------------

def check_differentiation(profiles: list, songs: list) -> bool:
    """Different profiles must not share more than 2 songs in their top-5 (< 40% overlap)."""
    print("\n-- CHECK 3: Profile Differentiation ----------------------------")
    all_passed = True

    top5 = {p["name"]: set(_top5_titles(p, songs)) for p in profiles}
    names = list(top5)

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            shared = top5[a] & top5[b]
            passed = len(shared) <= 2
            label = PASS if passed else FAIL
            overlap_str = ", ".join(sorted(shared)) if shared else "none"
            print(f"  [{label}] {a} vs {b}: {len(shared)}/5 shared  ({overlap_str})")
            if not passed:
                all_passed = False

    return all_passed


# -- Runner --------------------------------------------------------------------

def main() -> None:
    print("=" * 65)
    print("  AI Music Recommender — Consistency & Quality Check")
    print("=" * 65)

    songs_list = load_songs(str(SONGS_CSV))
    with open(PROFILES_JSON, encoding="utf-8") as fh:
        profiles = json.load(fh)

    model_songs = _load_songs()
    song_lookup = {s["id"]: s for s in model_songs}

    results = [
        check_determinism(profiles, songs_list),
        check_model_quality(profiles, song_lookup),
        check_differentiation(profiles, songs_list),
    ]

    passed = sum(results)
    total = len(results)
    overall = PASS if all(results) else FAIL

    print("\n" + "=" * 65)
    print(f"  Overall: [{overall}]  {passed}/{total} checks passed")
    print("=" * 65 + "\n")

    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
