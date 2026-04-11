"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import json

try:
    from .recommender import load_songs, recommend_songs
except ImportError:
    from recommender import load_songs, recommend_songs

# Change this to "jordan" or "sam" to see different recommendations.
ACTIVE_USER = "alex"


def main() -> None:
    songs = load_songs("data/songs.csv")

    with open("data/users.json", "r", encoding="utf-8") as f:
        profiles = json.load(f)

    user_prefs = profiles[ACTIVE_USER]

    recommendations = recommend_songs(user_prefs, songs, k=5)

    print(f"\nTop recommendations for {ACTIVE_USER}:\n")
    for song, score, explanation in recommendations:
        print(f"{song['title']} by {song['artist']} - Score: {score:.2f}")
        print(f"  {explanation}")
        print()


if __name__ == "__main__":
    main()
