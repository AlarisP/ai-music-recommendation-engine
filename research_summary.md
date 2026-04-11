# Research Summary: How Streaming Platforms Predict What You'll Love Next

## The Two Core Filtering Approaches

### 1. Collaborative Filtering — "People like you also liked..."

Collaborative filtering ignores the song's audio content entirely. It finds patterns in **how users collectively behave** across the platform.

**How it works:**
- The system identifies users with similar listening histories and assumes their future tastes will also align
- If many users play Song X right after Song Y, the algorithm links those two songs — even if they sound completely different
- Spotify builds a massive user-song interaction matrix, then applies techniques like matrix factorization and Word2Vec-style embeddings to discover hidden taste clusters

**Strengths:**
- Enables serendipitous, surprising recommendations outside a user's existing bubble
- Can surface songs that are culturally linked but hard to describe by audio features alone
- Gets more accurate as more users interact with the platform

**Weaknesses — the Cold Start Problem:**
- New users have no history, so there is no useful signal to work from
- Newly uploaded songs have no listeners, making them effectively invisible to the algorithm
- Sparsity is extreme: in large catalogs, most users have heard less than **0.1%** of all available songs, making the interaction matrix very sparse and less reliable

---

### 2. Content-Based Filtering — "This song sounds like what you like..."

Content-based filtering analyzes the **attributes of the song itself** and matches them to a profile of the user's demonstrated preferences.

**How it works:**
- Audio analysis extracts measurable features: tempo (BPM), key, energy, danceability, valence (musical positivity), acousticness, and more
- A user profile is built by averaging or weighting the attributes of songs they have historically enjoyed
- Candidate songs are scored by how closely their attributes match that profile

**Pandora's Music Genome Project** is the classic industry example: human analysts tagged every song across ~450 musical attributes, and recommendations stayed within that attribute space.

**Strengths:**
- Works for brand-new users as long as they provide some initial taste signal (onboarding questionnaire, seed song, etc.)
- Transparent and explainable — a recommendation can be justified with specific attributes
- Not affected by the behavior of other users; immune to manipulation by coordinated listening campaigns

**Weaknesses:**
- Filter bubble: you only get recommendations similar to what you already know you like
- Misses emergent cultural context — no audio feature captures "this song blew up at Coachella"
- Struggles with subjective or abstract qualities like humor, irony, or cultural meaning

---

## How Major Platforms Combine Both

Modern platforms use **hybrid systems** that run multiple methods in parallel and blend their outputs.

### Spotify's Three-Layer Stack

| Layer | Method | Data Source |
|---|---|---|
| Collaborative Filtering | User behavior clustering | Play counts, skips, saves, playlist adds |
| Content-Based Filtering | Audio + metadata analysis | BPM, energy, mood, genre, key |
| NLP / Semantic Analysis | Text surrounding songs | Blog posts, reviews, playlist names |

Spotify introduced **Semantic IDs** in 2024–2025: compact AI-generated codes that link a song to a user's listening intent, bridging the gap between audio features and contextual meaning.

Recent Spotify features powered by this hybrid stack include:
- **Spotify DJ** — a generative AI that narrates a personalized radio stream
- **Generative Mix Playlists** — e.g., "your sad acoustic punk mix," created on demand
- **Intent-Based Search** — the search bar now understands mood and context queries, not just song titles

### YouTube Music

YouTube Music layers music-specific recommendation logic on top of signals from the broader YouTube platform — watch time, search queries, and engagement on music videos all feed the model, giving it behavioral data far beyond listening sessions alone.

---

## Connection to This Project

The recommender in this repo ([src/recommender.py](src/recommender.py)) is a **content-based filtering system**. It scores each song using:

1. Mood similarity
2. Tempo similarity
3. Genre match
4. Artist and length preferences

This directly mirrors one of the two pillars that real platforms like Spotify use. The key difference: this simulation has only one user, so there is no crowd signal to draw from. Real platforms gain enormous recommendation power from collaborative signals — especially for nudging users toward music they would not have found on their own.

---

## Sources

- [Inside Spotify's Recommendation System: A Complete Guide (2025)](https://www.music-tomorrow.com/blog/how-spotify-recommendation-system-works-complete-guide)
- [The Inner Workings of Spotify's AI-Powered Music Recommendations (Medium)](https://medium.com/beyond-the-build/the-inner-workings-of-spotifys-ai-powered-music-recommendations-how-spotify-shapes-your-playlist-a10a9148ee8d)
- [Content-Based vs Collaborative Filtering: Difference — GeeksforGeeks](https://www.geeksforgeeks.org/machine-learning/content-based-vs-collaborative-filtering-difference/)
- [Content Filtering Methods for Music Recommendation: A Review (arXiv, 2025)](https://arxiv.org/abs/2507.02282)
- [Collaborative Filtering: How to Build a Recommender System — Redis](https://redis.io/blog/collaborative-filtering-how-to-build-a-recommender-system/)
- [What is Content-Based Filtering? — Redis](https://redis.io/blog/what-is-content-based-filtering/)
- [Recommender System — Wikipedia](https://en.wikipedia.org/wiki/Recommender_system)
