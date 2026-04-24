"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

try:
    from .recommender import load_songs, recommend_songs
except ImportError:
    from recommender import load_songs, recommend_songs

from tabulate import tabulate

# Change ACTIVE_USER to any name below to switch profiles.
ACTIVE_USER = "alex"

# Scoring mode:
#   "simple"   — additive weighted sum (genre×2, mood×1.5, energy×1, acoustic×0.5, valence×0.5)
#   "advanced" — grouped FEEL/INTENSITY/STYLE/GROOVE weights with mood gate penalty
SCORING_MODE = "advanced"

USER_PROFILES = {
    "maya": {
        "genre": "pop",
        "favorite_genres": ["pop", "hip-hop", "edm"],
        "mood": "excited",
        "energy": 0.92,
        "tempo_bpm": 132,
        "likes_acoustic": False,
        "recent_songs": [],
    },
    "alex": {
        "genre": "lofi",
        "favorite_genres": ["lofi", "ambient", "jazz"],
        "mood": "chill",
        "energy": 0.35,
        "tempo_bpm": 75,
        "likes_acoustic": True,
        "recent_songs": [],
    },
    "jordan": {
        "genre": "rock",
        "favorite_genres": ["rock", "metal", "blues"],
        "mood": "intense",
        "energy": 0.93,
        "tempo_bpm": 155,
        "likes_acoustic": False,
        "recent_songs": [],
    },
    "sam": {
        "genre": "k-pop",
        "favorite_genres": ["k-pop", "rock", "pop", "metal"],
        "mood": "excited",
        "energy": 0.88,
        "tempo_bpm": 138,
        "likes_acoustic": False,
        "recent_songs": [],
    },
    # Adversarial profile: contradictory signals designed to stress-test scoring.
    # High energy + sad mood triggers the mood gate penalty.
    # EDM genre + likes_acoustic=True conflicts on texture.
    # Favorite genres span opposite ends of the spectrum (EDM vs classical).
    # Expected behavior: no song scores cleanly — reveals how the scorer handles
    # a user it was never designed for.
    "riley": {
        "genre": "edm",
        "favorite_genres": ["edm", "classical"],
        "mood": "sad",
        "energy": 0.95,
        "tempo_bpm": 140,
        "likes_acoustic": True,
        "recent_songs": [],
    },
}


def _wrap(text: str, width: int = 45) -> str:
    """Hard-wrap a string at word boundaries for table cell display."""
    words = text.split()
    lines, current = [], []
    length = 0
    for word in words:
        if length + len(word) + bool(current) > width:
            lines.append(" ".join(current))
            current, length = [word], len(word)
        else:
            current.append(word)
            length += len(word) + bool(current) - 1
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def main() -> None:
    songs = load_songs("data/songs.csv")
    user_prefs = USER_PROFILES[ACTIVE_USER]

    recommendations = recommend_songs(user_prefs, songs, k=5, mode=SCORING_MODE)

    score_scale = "AI-assisted 0-1 blended score"
    print(f"\n{'='*70}")
    print(f"  TOP RECOMMENDATIONS FOR: {ACTIVE_USER.capitalize()}  [{SCORING_MODE.upper()} scoring | {score_scale}]")
    print(f"{'='*70}\n")

    rows = []
    for idx, (song, score, explanation) in enumerate(recommendations, 1):
        rows.append([
            idx,
            song["title"],
            song["artist"],
            song["genre"],
            f"{score:.2f}",
            _wrap(explanation),
        ])

    print(tabulate(
        rows,
        headers=["#", "Title", "Artist", "Genre", "Score", "Why"],
        tablefmt="outline",
        colalign=("center", "left", "left", "left", "center", "left"),
    ))
    print()


if __name__ == "__main__":
    main()
