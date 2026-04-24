from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
import math


class BaseScorer(ABC):
    @abstractmethod
    def score(self, user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
        raise NotImplementedError

    @abstractmethod
    def explain(self, user_prefs: Dict, song: Dict) -> str:
        raise NotImplementedError


class SimpleScorer(BaseScorer):
    def score(self, user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
        details = _song_score_details(user_prefs, song)
        reasons = _build_reasons(details, song, include_near_genre=False)
        score = 0.0

        genre_pts = round(details["genre_score"] * 2.0, 2)
        if genre_pts > 0:
            reasons.append(f"genre match (+{genre_pts})")
        score += genre_pts

        mood_pts = round(details["mood_score"] * 1.5, 2)
        if mood_pts >= 1.0:
            reasons.append(f"mood match (+{mood_pts})")
        score += mood_pts

        energy_pts = round(details["energy_score"] * 1.0, 2)
        if energy_pts >= 0.7:
            reasons.append(f"energy match (+{energy_pts})")
        score += energy_pts

        acoustic_pts = round(details["acoustic_score"] * 0.5, 2)
        if acoustic_pts >= 0.35:
            reasons.append(f"acoustic style match (+{acoustic_pts})")
        score += acoustic_pts

        valence_pts = round(details["valence_score"] * 0.5, 2)
        if valence_pts >= 0.35:
            reasons.append(f"emotional tone match (+{valence_pts})")
        score += valence_pts

        return round(score, 4), reasons

    def explain(self, user_prefs: Dict, song: Dict) -> str:
        details = _song_score_details(user_prefs, song)
        return "Recommended because " + ", ".join(_build_reasons(details, song, include_near_genre=False)) + "."


class AdvancedScorer(BaseScorer):
    def score(self, user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
        details = _song_score_details(user_prefs, song)
        score = details["final_score"]
        reasons = _build_reasons(details, song, include_near_genre=True)

        return round(score, 4), reasons

    def explain(self, user_prefs: Dict, song: Dict) -> str:
        details = _song_score_details(user_prefs, song)
        return "Recommended because " + ", ".join(_build_reasons(details, song, include_near_genre=True)) + "."


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

    feel_score = 0.65 * mood_score + 0.35 * valence_score
    intensity_score = 0.70 * energy_score + 0.30 * tempo_score
    style_score = 0.55 * acoustic_score + 0.45 * genre_score
    groove_score = danceability_score

    final_score = (
        0.38 * feel_score
        + 0.30 * intensity_score
        + 0.22 * style_score
        + 0.10 * groove_score
    )

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


def _build_reasons(details: Dict[str, float], song: Dict, include_near_genre: bool) -> List[str]:
    reasons: List[str] = []
    if details["genre_score"] > 0.95:
        reasons.append(f"genre matches your preference ({song.get('genre')})")
    elif include_near_genre and details["genre_score"] >= 0.5:
        reasons.append(f"genre is close to your taste ({song.get('genre')})")

    if details["mood_score"] > 0.80:
        reasons.append(f"mood aligns well ({song.get('mood')})" if include_near_genre else f"mood is close to your target ({song.get('mood')})")
    if details["energy_score"] > 0.80:
        reasons.append("energy level fits your vibe")
    if details["acoustic_score"] > 0.80:
        reasons.append("acoustic style matches your profile" if include_near_genre else "acoustic style fits your profile")
    if details["valence_score"] > 0.80:
        reasons.append("emotional tone aligns with what you're after")
    if not reasons:
        reasons.append("overall feature similarity is strong")
    return reasons