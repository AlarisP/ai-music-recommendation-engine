from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import csv
import math

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
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        scored: List[Tuple[Song, float]] = []
        for song in self.songs:
            score = _score_song_structured(user, song)
            scored.append((song, score))

        ranked = sorted(scored, key=lambda item: item[1], reverse=True)
        diverse = _apply_artist_diversity(ranked)
        return [song for song, _ in diverse[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        details = _song_score_details(
            {
                "genre": user.favorite_genre,
                "mood": user.favorite_mood,
                "energy": user.target_energy,
                "likes_acoustic": user.likes_acoustic,
            },
            {
                "genre": song.genre,
                "mood": song.mood,
                "energy": song.energy,
                "tempo_bpm": song.tempo_bpm,
                "valence": song.valence,
                "danceability": song.danceability,
                "acousticness": song.acousticness,
                "artist": song.artist,
            },
        )
        reasons: List[str] = []
        if details["genre_score"] > 0.95:
            reasons.append(f"genre matches your preference ({song.genre})")
        if details["mood_score"] > 0.80:
            reasons.append(f"mood is close to your target ({song.mood})")
        if details["energy_score"] > 0.80:
            reasons.append("energy level fits your vibe")
        if details["acoustic_score"] > 0.80:
            reasons.append("acoustic style fits your profile")
        if details["valence_score"] > 0.80:
            reasons.append("emotional tone aligns with what you're after")
        if not reasons:
            reasons.append("overall feature similarity is strong")
        return f"Recommended because {', '.join(reasons)}."

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
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

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    """
    if not songs:
        return []

    recent_artists = _extract_recent_artists(user_prefs)

    scored: List[Tuple[Dict, float, Dict[str, float]]] = []
    for song in songs:
        details = _song_score_details(user_prefs, song)
        score = details["final_score"]

        # Soft novelty boost for artists not in recent listening history.
        if recent_artists and song.get("artist") not in recent_artists:
            score += 0.02

        scored.append((song, min(score, 1.0), details))

    ranked = sorted(scored, key=lambda item: item[1], reverse=True)

    artist_counts: Dict[str, int] = {}
    reranked: List[Tuple[Dict, float, Dict[str, float]]] = []
    for song, score, details in ranked:
        artist = str(song.get("artist", ""))
        seen = artist_counts.get(artist, 0)
        diversity_penalty = 0.05 * seen
        adjusted = max(0.0, score - diversity_penalty)
        artist_counts[artist] = seen + 1
        reranked.append((song, adjusted, details))

    reranked.sort(key=lambda item: item[1], reverse=True)
    top = reranked[:k]

    results: List[Tuple[Dict, float, str]] = []
    for song, score, details in top:
        explanation = _build_explanation(user_prefs, song, details)
        results.append((song, round(score, 4), explanation))
    return results


MOOD_MAP: Dict[str, Tuple[float, float]] = {
    "sad": (-1.0, -0.4),
    "chill": (0.0, -0.8),
    "happy": (0.8, 0.2),
    "excited": (0.9, 0.9),
    "angry": (-0.7, 0.8),
    "intense": (0.7, 0.95),
    "relaxed": (0.2, -0.7),
    "moody": (-0.3, 0.2),
    "focused": (0.3, -0.1),
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


def _normalized_similarity(a: float, b: float, span: float) -> float:
    if span <= 0:
        return 0.0
    return max(0.0, 1.0 - abs(a - b) / span)


def _mood_similarity(target_mood: str, song_mood: str) -> float:
    target = MOOD_MAP.get(str(target_mood).lower())
    song = MOOD_MAP.get(str(song_mood).lower())
    if target is None or song is None:
        return 0.6 if str(target_mood).lower() == str(song_mood).lower() else 0.3

    # Max distance in this 2D mood-space is roughly sqrt(8) ~ 2.83.
    distance = math.dist(target, song)
    return max(0.0, 1.0 - distance / 2.83)


def _song_score_details(user_prefs: Dict, song: Dict) -> Dict[str, float]:
    genre_pref = str(user_prefs.get("genre") or user_prefs.get("favorite_genre") or "").lower()
    mood_pref = str(user_prefs.get("mood") or user_prefs.get("favorite_mood") or "").lower()
    target_energy = float(user_prefs.get("energy") or user_prefs.get("target_energy") or 0.6)
    target_tempo = float(user_prefs.get("tempo_bpm") or 100.0)
    likes_acoustic = bool(user_prefs.get("likes_acoustic", False))

    song_genre = str(song.get("genre", "")).lower()
    song_mood = str(song.get("mood", "")).lower()
    song_energy = float(song.get("energy", 0.5))
    song_tempo = float(song.get("tempo_bpm", 100.0))
    song_valence = float(song.get("valence", 0.5))
    song_danceability = float(song.get("danceability", 0.5))
    song_acousticness = float(song.get("acousticness", 0.5))

    favorite_genres = [
        str(g).lower()
        for g in (user_prefs.get("favorite_genres") or [])
        if isinstance(g, str)
    ]

    genre_score = 1.0 if song_genre == genre_pref and genre_pref else 0.0
    if not genre_score and favorite_genres and song_genre in favorite_genres:
        genre_rank = favorite_genres.index(song_genre)
        genre_score = max(0.5, 0.9 - 0.1 * genre_rank)

    mood_score = _mood_similarity(mood_pref, song_mood)
    energy_score = _normalized_similarity(target_energy, song_energy, span=1.0)
    tempo_score = _normalized_similarity(target_tempo, song_tempo, span=80.0)
    acoustic_target = 0.8 if likes_acoustic else 0.2
    acoustic_score = _normalized_similarity(acoustic_target, song_acousticness, span=1.0)

    # Optional refiners: map mood to expected valence and dance feel.
    target_valence = {
        "happy": 0.80,
        "excited": 0.85,
        "chill": 0.60,
        "focused": 0.55,
        "intense": 0.45,
        "moody": 0.35,
        "relaxed": 0.65,
        "sad": 0.20,
        "angry": 0.20,
    }.get(mood_pref, 0.55)
    valence_score = _normalized_similarity(target_valence, song_valence, span=1.0)

    target_danceability = {
        "happy": 0.80,
        "excited": 0.85,
        "chill": 0.60,
        "focused": 0.58,
        "relaxed": 0.52,
        "moody": 0.50,
        "intense": 0.62,
        "sad": 0.35,
        "angry": 0.65,
    }.get(mood_pref, 0.60)
    danceability_score = _normalized_similarity(target_danceability, song_danceability, span=1.0)

    # Group features that measure the same underlying dimension together,
    # then weight the groups — avoids double-counting correlated features.

    # FEEL: what emotion does this evoke? (mood is primary; valence refines)
    feel_score = 0.65 * mood_score + 0.35 * valence_score

    # INTENSITY: how energetic/driving is it? (energy leads; tempo refines)
    intensity_score = 0.70 * energy_score + 0.30 * tempo_score

    # STYLE: what kind of production is it? (texture + genre identity)
    style_score = 0.55 * acoustic_score + 0.45 * genre_score

    # GROOVE: rhythmic drive — the remaining unique signal
    groove_score = danceability_score

    final_score = (
        0.38 * feel_score       # emotion matters most
        + 0.30 * intensity_score  # energy/pace second
        + 0.22 * style_score      # texture/genre third
        + 0.10 * groove_score     # minor refiner
    )

    # Mood gate: if moods are near-opposites, reduce score multiplicatively.
    # Prevents a numerically close song from overcoming a fundamentally wrong vibe.
    user_mood_coords = MOOD_MAP.get(mood_pref)
    song_mood_coords = MOOD_MAP.get(song_mood)
    if user_mood_coords and song_mood_coords:
        mood_distance = math.dist(user_mood_coords, song_mood_coords)
        if mood_distance > 1.8:
            final_score *= max(0.5, 1.0 - (mood_distance - 1.8) / 2.83)

    return {
        "genre_score": genre_score,
        "mood_score": mood_score,
        "tempo_score": tempo_score,
        "energy_score": energy_score,
        "acoustic_score": acoustic_score,
        "valence_score": valence_score,
        "danceability_score": danceability_score,
        "final_score": final_score,
    }


def _build_explanation(user_prefs: Dict, song: Dict, details: Dict[str, float]) -> str:
    reasons: List[str] = []
    if details["mood_score"] > 0.8:
        reasons.append(f"mood matches ({song.get('mood', 'unknown')})")
    if details["energy_score"] > 0.8:
        reasons.append("energy level fits your vibe")
    if details["acoustic_score"] > 0.8:
        reasons.append("acoustic style fits your profile")
    if details["valence_score"] > 0.8:
        reasons.append("emotional tone aligns with what you're after")
    if details["tempo_score"] > 0.8:
        reasons.append("tempo is close to your target")
    if details["genre_score"] > 0.8:
        reasons.append(f"genre aligns ({song.get('genre', 'unknown')})")

    if not reasons:
        reasons.append("it is a strong overall match across multiple features")

    return "Recommended because " + ", ".join(reasons) + "."


def _score_song_structured(user: UserProfile, song: Song) -> float:
    details = _song_score_details(
        {
            "genre": user.favorite_genre,
            "mood": user.favorite_mood,
            "energy": user.target_energy,
            "likes_acoustic": user.likes_acoustic,
        },
        {
            "genre": song.genre,
            "mood": song.mood,
            "energy": song.energy,
            "tempo_bpm": song.tempo_bpm,
            "valence": song.valence,
            "danceability": song.danceability,
            "acousticness": song.acousticness,
        },
    )
    return details["final_score"]


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
