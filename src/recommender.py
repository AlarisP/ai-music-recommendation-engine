from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
import csv
import logging
from pathlib import Path

try:
    from .scorers import SimpleScorer, AdvancedScorer
    from .ai_model import load_default_model
except ImportError:
    from scorers import SimpleScorer, AdvancedScorer
    from ai_model import load_default_model


REQUIRED_USER_KEYS = ("genre", "mood", "energy", "likes_acoustic")


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("music_recommender")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logs_dir = Path(__file__).resolve().parents[1] / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "recommender.log"

    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


LOGGER = _setup_logger()

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song], mode: str = "advanced"):
        self.songs = songs
        self.mode = mode
        _get_scorer(mode)
        self.learned_model = load_default_model()

    def recommend(self, user: UserProfile, k: int = 5, mode: str | None = None) -> List[Song]:
        scored: List[Tuple[Song, float]] = []
        scorer = _get_scorer(mode or self.mode)
        user_payload = _user_payload(user)
        _validate_user_prefs(user_payload, context="Recommender.recommend")

        for song in self.songs:
            song_payload = _sanitize_song(_song_payload(song))
            heuristic_score, _ = scorer.score(user_payload, song_payload)
            learned_score = self.learned_model.predict_probability(user_payload, song_payload)
            score = _blend_scores(heuristic_score, learned_score, mode or self.mode)
            scored.append((song, score))

        ranked = sorted(scored, key=lambda item: item[1], reverse=True)
        diverse = _apply_artist_diversity(ranked)
        return [song for song, _ in diverse[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song, mode: str | None = None) -> str:
        scorer = _get_scorer(mode or self.mode)
        user_payload = _user_payload(user)
        _validate_user_prefs(user_payload, context="Recommender.explain_recommendation")
        song_payload = _sanitize_song(_song_payload(song))
        learned_note = self.learned_model.explain(user_payload, song_payload)
        return scorer.explain(user_payload, song_payload) + f" {learned_note}"

def load_songs(csv_path: str) -> List[Dict]:
    """Read songs.csv and return a list of dicts with numeric fields converted to int or float."""
    songs: List[Dict] = []
    with open(csv_path, "r", newline="", encoding="utf-8") as file:
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

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score one song against user preferences and return a (total_points, reasons) tuple."""
    return SimpleScorer().score(user_prefs, song)


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5, mode: str = "simple") -> List[Tuple[Dict, float, str]]:
    """Score every song, rank by score, and return the top k results with explanations.

    mode="simple"   — additive weighted sum (genre×2, mood×1.5, energy×1, …)
    mode="advanced" — grouped FEEL/INTENSITY/STYLE/GROOVE weights with mood gate penalty
    """
    if not songs:
        LOGGER.warning("recommend_songs received an empty song catalog")
        return []

    _validate_user_prefs(user_prefs, context="recommend_songs")

    scorer = _get_scorer(mode)
    learned_model = load_default_model()

    recent_artists = _extract_recent_artists(user_prefs)

    scored: List[Tuple[Dict, float]] = []
    for song in songs:
        sanitized_song = _sanitize_song(song)
        try:
            heuristic_score, _ = scorer.score(user_prefs, sanitized_song)
            learned_score = learned_model.predict_probability(user_prefs, sanitized_song)
        except Exception as exc:
            LOGGER.warning("Skipping song due to scoring error: %s | song=%s", exc, song.get("title", "unknown"))
            continue

        score = _blend_scores(heuristic_score, learned_score, mode)

        if recent_artists and sanitized_song.get("artist") not in recent_artists:
            score += 0.1

        scored.append((sanitized_song, score))

    if not scored:
        LOGGER.warning("No songs were scored successfully")
        return []

    ranked = sorted(scored, key=lambda item: item[1], reverse=True)

    artist_counts: Dict[str, int] = {}
    genre_counts: Dict[str, int] = {}
    reranked: List[Tuple[Dict, float]] = []
    for song, score in ranked:
        artist = str(song.get("artist", ""))
        genre = str(song.get("genre", ""))
        artist_seen = artist_counts.get(artist, 0)
        genre_seen = genre_counts.get(genre, 0)
        diversity_penalty = 0.05 * artist_seen + 0.03 * genre_seen
        adjusted = max(0.0, score - diversity_penalty)
        artist_counts[artist] = artist_seen + 1
        genre_counts[genre] = genre_seen + 1
        reranked.append((song, adjusted))

    reranked.sort(key=lambda item: item[1], reverse=True)
    top = reranked[:k]

    results: List[Tuple[Dict, float, str]] = []
    for song, score in top:
        explanation = scorer.explain(user_prefs, song) + f" {learned_model.explain(user_prefs, song)}"
        results.append((song, round(score, 4), explanation))
    return results


def _user_payload(user: UserProfile) -> Dict:
    return {
        "genre": user.favorite_genre,
        "mood": user.favorite_mood,
        "energy": user.target_energy,
        "likes_acoustic": user.likes_acoustic,
    }


def _song_payload(song: Song) -> Dict:
    return {
        "genre": song.genre,
        "mood": song.mood,
        "energy": song.energy,
        "tempo_bpm": song.tempo_bpm,
        "valence": song.valence,
        "danceability": song.danceability,
        "acousticness": song.acousticness,
        "artist": song.artist,
    }


def _extract_recent_artists(user_prefs: Dict) -> set[str]:
    recent = user_prefs.get("recent_songs") or []
    artists: set[str] = set()
    for item in recent:
        if isinstance(item, dict):
            artist = item.get("artist")
            if isinstance(artist, str) and artist:
                artists.add(artist)
    return artists


def _validate_user_prefs(user_prefs: Dict[str, Any], context: str) -> None:
    missing = [key for key in REQUIRED_USER_KEYS if key not in user_prefs or user_prefs.get(key) is None]
    if missing:
        LOGGER.error("Missing required user preference fields in %s: %s", context, ", ".join(missing))
        raise ValueError(f"Missing required user preference fields: {', '.join(missing)}")

    try:
        energy = float(user_prefs["energy"])
    except (TypeError, ValueError) as exc:
        LOGGER.error("Invalid energy value in %s: %s", context, user_prefs.get("energy"))
        raise ValueError("User energy must be numeric") from exc

    if not 0.0 <= energy <= 1.0:
        LOGGER.error("Out-of-range energy value in %s: %s", context, energy)
        raise ValueError("User energy must be between 0.0 and 1.0")

    if "tempo_bpm" in user_prefs and user_prefs.get("tempo_bpm") is not None:
        try:
            float(user_prefs["tempo_bpm"])
        except (TypeError, ValueError) as exc:
            LOGGER.error("Invalid tempo_bpm value in %s: %s", context, user_prefs.get("tempo_bpm"))
            raise ValueError("User tempo_bpm must be numeric when provided") from exc


def _sanitize_song(song: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(song, dict):
        LOGGER.warning("Song payload was not a dict. Using safe defaults.")
        song = {}

    return {
        "id": song.get("id", -1),
        "title": str(song.get("title", "Unknown Title")),
        "artist": str(song.get("artist", "Unknown Artist")),
        "genre": str(song.get("genre", "unknown")),
        "mood": str(song.get("mood", "unknown")),
        "energy": _safe_float(song.get("energy"), 0.5, "energy", song),
        "tempo_bpm": _safe_float(song.get("tempo_bpm"), 100.0, "tempo_bpm", song),
        "valence": _safe_float(song.get("valence"), 0.5, "valence", song),
        "danceability": _safe_float(song.get("danceability"), 0.5, "danceability", song),
        "acousticness": _safe_float(song.get("acousticness"), 0.5, "acousticness", song),
    }


def _safe_float(value: Any, default: float, field: str, song: Dict[str, Any]) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        LOGGER.warning(
            "Invalid %s for song '%s'. Falling back to %s",
            field,
            song.get("title", "Unknown Title"),
            default,
        )
        return default


def _get_scorer(mode: str):
    if mode == "simple":
        return SimpleScorer()
    if mode == "advanced":
        return AdvancedScorer()
    raise ValueError(f"Unknown scoring mode: {mode}")


def _blend_scores(heuristic_score: float, learned_score: float, mode: str) -> float:
    heuristic_max = 5.5 if mode == "simple" else 1.0
    heuristic_normalized = max(0.0, min(1.0, heuristic_score / heuristic_max))
    return round(0.65 * learned_score + 0.35 * heuristic_normalized, 4)


def _apply_artist_diversity(scored: List[Tuple[Song, float]]) -> List[Tuple[Song, float]]:
    artist_counts: Dict[str, int] = {}
    adjusted: List[Tuple[Song, float]] = []
    for song, score in scored:
        seen = artist_counts.get(song.artist, 0)
        penalty = 0.05 * seen
        adjusted.append((song, max(0.0, score - penalty)))
        artist_counts[song.artist] = seen + 1
    adjusted.sort(key=lambda item: item[1], reverse=True)
    return adjusted
