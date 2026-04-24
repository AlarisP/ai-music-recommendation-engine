import pytest

from src.recommender import Song, UserProfile, Recommender, recommend_songs

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_defaults_to_advanced_mode():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()

    results = rec.recommend(user, k=1)

    assert len(results) == 1
    assert results[0].genre == "pop"


def test_recommend_supports_simple_mode():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()

    results = rec.recommend(user, k=1, mode="simple")

    assert len(results) == 1
    assert results[0].genre == "pop"


def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_invalid_mode_raises_value_error():
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )

    rec = Recommender([], mode="advanced")

    with pytest.raises(ValueError):
        rec.recommend(user, mode="not-a-real-mode")


def test_recommend_songs_missing_required_user_fields_raises_value_error():
    songs = [
        {
            "id": 1,
            "title": "Minimal Track",
            "artist": "Sample Artist",
            "genre": "pop",
            "mood": "happy",
            "energy": 0.7,
            "tempo_bpm": 118.0,
            "valence": 0.8,
            "danceability": 0.75,
            "acousticness": 0.2,
        }
    ]

    invalid_user_profile = {
        "genre": "pop",
        "energy": 0.8,
        "likes_acoustic": False,
    }

    with pytest.raises(ValueError):
        recommend_songs(invalid_user_profile, songs, k=1, mode="advanced")
