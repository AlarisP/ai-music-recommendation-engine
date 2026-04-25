from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional
import csv
import json

from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .scorers import _song_score_details


@dataclass(frozen=True)
class PreferenceModel:
    """Small learned model that predicts how much a user will like a song."""

    pipeline: Pipeline
    feature_names: List[str]
    test_accuracy: float
    training_examples: int

    def predict_probability(self, user_prefs: Dict, song: Dict) -> float:
        features = _feature_vector(user_prefs, song)
        probability = self.pipeline.predict_proba([features])[0][1]
        return float(probability)

    def explain(self, user_prefs: Dict, song: Dict) -> str:
        probability = self.predict_probability(user_prefs, song)
        if probability >= 0.75:
            verdict = "strong learned match"
        elif probability >= 0.5:
            verdict = "moderate learned match"
        else:
            verdict = "weak learned match"
        return f"Feedback-trained model confidence {probability:.2f} ({verdict})."

    def to_export_dict(self) -> Dict[str, object]:
        scaler: StandardScaler = self.pipeline.named_steps["scaler"]
        model: LogisticRegression = self.pipeline.named_steps["model"]
        return {
            "feature_names": self.feature_names,
            "means": scaler.mean_.tolist(),
            "scales": scaler.scale_.tolist(),
            "coefficients": model.coef_[0].tolist(),
            "intercept": float(model.intercept_[0]),
            "test_accuracy": self.test_accuracy,
            "training_examples": self.training_examples,
        }


FEATURE_NAMES = [
    "genre_score",
    "mood_score",
    "tempo_score",
    "energy_score",
    "acoustic_score",
    "valence_score",
    "danceability_score",
]

MODELS_DIR = Path(__file__).resolve().parents[1] / "docs" / "data" / "models"


@lru_cache(maxsize=1)
def load_default_model() -> PreferenceModel:
    """Train the model once from the repo's synthetic feedback data (all profiles combined)."""
    return _train_model()


def train_model_for_profile(profile: Dict) -> PreferenceModel:
    """Train a logistic regression model using only one profile's feedback events."""
    songs = _load_songs()
    song_lookup = {song["id"]: song for song in songs}
    user_prefs = _profile_to_user_prefs(profile)

    features: List[List[float]] = []
    labels: List[int] = []

    for event in profile.get("feedback_events", []):
        song_id = event.get("song_id")
        action = event.get("action")
        song = song_lookup.get(song_id)
        if not song or action not in {"like", "skip"}:
            continue
        features.append(_feature_vector(user_prefs, song))
        labels.append(1 if action == "like" else 0)

    if len(set(labels)) < 2:
        raise ValueError(
            f"Profile '{profile.get('id')}' needs both positive and negative examples."
        )

    # With small datasets skip the hold-out split to use every example for training.
    if len(features) >= 10:
        x_train, x_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.25, random_state=42, stratify=labels
        )
        use_test = True
    else:
        x_train, y_train = features, labels
        x_test, y_test = features, labels
        use_test = False

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )
    pipeline.fit(x_train, y_train)
    test_accuracy = float(pipeline.score(x_test, y_test)) if use_test else None

    return PreferenceModel(
        pipeline=pipeline,
        feature_names=FEATURE_NAMES,
        test_accuracy=test_accuracy,
        training_examples=len(features),
    )


def export_all_models(output_dir: Optional[Path] = None) -> None:
    """Train and export one JSON model file per demo profile plus a neutral default model."""
    out = output_dir or MODELS_DIR
    out.mkdir(parents=True, exist_ok=True)

    profiles = _load_profiles()
    for profile in profiles:
        profile_id = profile.get("id")
        model = train_model_for_profile(profile)
        model_dict = model.to_export_dict()
        model_dict["profile_id"] = profile_id
        dest = out / f"{profile_id}_model.json"
        dest.write_text(json.dumps(model_dict, indent=2), encoding="utf-8")
        print(f"Saved {dest.name}  (examples={model_dict['training_examples']}, "
              f"accuracy={model_dict.get('test_accuracy')})")

    # Neutral default model: zero coefficients → sigmoid(0) = 0.5 for every song.
    # The JS falls back to heuristic-only when this model is absent (null), but
    # keeping a file makes the slot explicit for future per-user retraining.
    n = len(FEATURE_NAMES)
    default_dict = {
        "profile_id": "default",
        "feature_names": FEATURE_NAMES,
        "means": [0.5] * n,
        "scales": [1.0] * n,
        "coefficients": [0.0] * n,
        "intercept": 0.0,
        "test_accuracy": None,
        "training_examples": 0,
    }
    (out / "default_model.json").write_text(json.dumps(default_dict, indent=2), encoding="utf-8")
    print("Saved default_model.json  (neutral — heuristic will dominate)")


def _train_model() -> PreferenceModel:
    songs = _load_songs()
    profiles = _load_profiles()
    song_lookup = {song["id"]: song for song in songs}

    features: List[List[float]] = []
    labels: List[int] = []

    for profile in profiles:
        for event in profile.get("feedback_events", []):
            song_id = event.get("song_id")
            action = event.get("action")
            song = song_lookup.get(song_id)
            if not song or action not in {"like", "skip"}:
                continue
            user_prefs = _profile_to_user_prefs(profile)
            features.append(_feature_vector(user_prefs, song))
            labels.append(1 if action == "like" else 0)

    if len(set(labels)) < 2:
        raise ValueError("Need both positive and negative examples to train the preference model.")

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=0.25,
        random_state=42,
        stratify=labels,
    )

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    test_accuracy = float(pipeline.score(x_test, y_test))

    return PreferenceModel(
        pipeline=pipeline,
        feature_names=FEATURE_NAMES,
        test_accuracy=test_accuracy,
        training_examples=len(features),
    )


def _feature_vector(user_prefs: Dict, song: Dict) -> List[float]:
    details = _song_score_details(user_prefs, song)
    return [
        details["genre_score"],
        details["mood_score"],
        details["tempo_score"],
        details["energy_score"],
        details["acoustic_score"],
        details["valence_score"],
        details["danceability_score"],
    ]


def _profile_to_user_prefs(profile: Dict) -> Dict:
    return {
        "genre": profile.get("genre"),
        "favorite_genres": profile.get("favorite_genres") or [],
        "mood": profile.get("mood"),
        "energy": profile.get("energy"),
        "tempo_bpm": profile.get("tempo_bpm"),
        "likes_acoustic": profile.get("likes_acoustic", False),
        "recent_songs": profile.get("recent_songs") or [],
    }


def _load_profiles() -> List[Dict]:
    profiles_path = Path(__file__).resolve().parents[1] / "docs" / "data" / "profiles.json"
    with open(profiles_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _load_songs() -> List[Dict]:
    songs_path = Path(__file__).resolve().parents[1] / "data" / "songs.csv"
    songs: List[Dict] = []
    with open(songs_path, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            songs.append(
                {
                    "id": int(row["id"]),
                    "title": row["title"],
                    "artist": row["artist"],
                    "genre": row["genre"],
                    "mood": row["mood"],
                    "energy": float(row["energy"]),
                    "tempo_bpm": float(row["tempo_bpm"]),
                    "valence": float(row["valence"]),
                    "danceability": float(row["danceability"]),
                    "acousticness": float(row["acousticness"]),
                }
            )
    return songs