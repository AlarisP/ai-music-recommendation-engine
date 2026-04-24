from src.ai_model import load_default_model


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
