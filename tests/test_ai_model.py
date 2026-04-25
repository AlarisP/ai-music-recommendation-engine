import json
from pathlib import Path

import pytest

from src.ai_model import load_default_model, train_model_for_profile, _load_songs, _profile_to_user_prefs
from src.recommender import load_songs, recommend_songs

_PROFILES_PATH = Path(__file__).resolve().parents[1] / "docs" / "data" / "profiles.json"
_SONGS_CSV = Path(__file__).resolve().parents[1] / "data" / "songs.csv"

with open(_PROFILES_PATH, encoding="utf-8") as _fh:
    _ALL_PROFILES = json.load(_fh)


def test_learned_model_scores_liked_song_higher_than_skipped_song():
    model = load_default_model()

    alex_profile = {
        "genre": "lofi",
        "favorite_genres": ["lofi", "ambient", "jazz"],
        "mood": "chill",
        "energy": 0.35,
        "tempo_bpm": 75,
        "likes_acoustic": True,
        "recent_songs": [],
    }

    liked_song = {
        "genre": "lofi",
        "mood": "chill",
        "energy": 0.35,
        "tempo_bpm": 72,
        "valence": 0.60,
        "danceability": 0.58,
        "acousticness": 0.86,
    }

    skipped_song = {
        "genre": "metal",
        "mood": "angry",
        "energy": 0.96,
        "tempo_bpm": 168,
        "valence": 0.22,
        "danceability": 0.55,
        "acousticness": 0.06,
    }

    liked_probability = model.predict_probability(alex_profile, liked_song)
    skipped_probability = model.predict_probability(alex_profile, skipped_song)

    assert 0.0 <= liked_probability <= 1.0
    assert 0.0 <= skipped_probability <= 1.0
    assert liked_probability > skipped_probability


@pytest.mark.parametrize("profile", _ALL_PROFILES, ids=[p["id"] for p in _ALL_PROFILES])
def test_per_profile_model_scores_liked_above_skipped(profile):
    song_lookup = {s["id"]: s for s in _load_songs()}
    events = profile.get("feedback_events", [])
    liked = [song_lookup[e["song_id"]] for e in events
             if e["action"] == "like" and e["song_id"] in song_lookup]
    skipped = [song_lookup[e["song_id"]] for e in events
               if e["action"] == "skip" and e["song_id"] in song_lookup]

    model = train_model_for_profile(profile)
    user_prefs = _profile_to_user_prefs(profile)

    avg_liked = sum(model.predict_probability(user_prefs, s) for s in liked) / len(liked)
    avg_skipped = sum(model.predict_probability(user_prefs, s) for s in skipped) / len(skipped)

    assert avg_liked > avg_skipped, (
        f"{profile['name']}: avg liked={avg_liked:.3f} not > avg skipped={avg_skipped:.3f}"
    )


@pytest.mark.parametrize("profile", _ALL_PROFILES, ids=[p["id"] for p in _ALL_PROFILES])
def test_per_profile_model_scores_are_valid_probabilities(profile):
    song_lookup = {s["id"]: s for s in _load_songs()}
    model = train_model_for_profile(profile)
    user_prefs = _profile_to_user_prefs(profile)

    for song in song_lookup.values():
        prob = model.predict_probability(user_prefs, song)
        assert 0.0 <= prob <= 1.0, (
            f"{profile['name']}: invalid probability {prob} for song id={song['id']}"
        )


def test_different_profiles_produce_different_top_recommendations():
    songs = load_songs(str(_SONGS_CSV))

    def top1(profile):
        prefs = {
            "genre": profile["genre"],
            "mood": profile["mood"],
            "energy": profile["energy"],
            "tempo_bpm": profile["tempo_bpm"],
            "likes_acoustic": profile["likes_acoustic"],
            "favorite_genres": profile.get("favorite_genres", []),
            "recent_songs": [],
        }
        return recommend_songs(prefs, songs, k=1, mode="advanced")[0][0]["title"]

    top_songs = [top1(p) for p in _ALL_PROFILES]
    unique = set(top_songs)
    assert len(unique) > 1, f"All profiles returned the same #1 song: {top_songs[0]}"


def test_recommendations_are_deterministic():
    songs = load_songs(str(_SONGS_CSV))
    profile = _ALL_PROFILES[0]
    prefs = {
        "genre": profile["genre"],
        "mood": profile["mood"],
        "energy": profile["energy"],
        "tempo_bpm": profile["tempo_bpm"],
        "likes_acoustic": profile["likes_acoustic"],
        "favorite_genres": profile.get("favorite_genres", []),
        "recent_songs": [],
    }

    run_a = [r[0]["title"] for r in recommend_songs(prefs, songs, k=5, mode="advanced")]
    run_b = [r[0]["title"] for r in recommend_songs(prefs, songs, k=5, mode="advanced")]

    assert run_a == run_b, f"Non-deterministic results:\nRun 1: {run_a}\nRun 2: {run_b}"
