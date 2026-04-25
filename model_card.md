# Model Card: AI Music Recommendation Engine

## 1. Model Name

**AI Music Recommendation Engine** (extended from MusicRecommender 1.0)

---

## 2. Intended Use

This system recommends the next song to play based on a user's stated preferences and listening feedback. It is designed for classroom exploration of the full applied AI loop: feature engineering → trained model → ranked output → human feedback → model improvement.

- **What it generates:** A ranked top-5 list of songs with a score, feature breakdown, and plain-language reason for each pick.
- **What it assumes about the user:** That the user wants songs similar to what they already like. It has no discovery mechanism — it will not intentionally surface unfamiliar styles.
- **Two modes:** Demo profiles (Alex, Maya, Jordan, Sam, Riley) load a per-profile trained logistic regression model. Custom ("My Profile") users get heuristic-only scoring so no pre-existing bias influences a blank-slate listener.
- **Production gap:** To deploy this for real users you would need a database, collaborative filtering (what similar users liked), and a feedback loop that re-trains the model over time rather than using a static export.

---

## 3. How the Model Works

Each song gets a score built from two signals blended 50/50:

**Heuristic scorer** — hand-crafted feature weights: mood (30%), energy (25%), genre (20%), tempo (15%), acoustic preference (10%). A mood gate maps each mood to a position on a valence/arousal grid and penalizes songs that are emotionally opposite to what the user wants. Feedback events (likes and skips) adjust the score by up to ±0.35. Recently played songs receive a small recency penalty to reduce repetition.

**Learned model** — a logistic regression trained separately for each demo profile using only that profile's liked vs skipped songs as the training set. The model learns 7 feature weights (genre match, mood similarity, tempo similarity, energy similarity, acoustic similarity, valence similarity, danceability similarity) from 8–10 labeled examples per profile. The trained weights are exported to JSON and re-run in the browser as a sigmoid function — no server required.

The final score is `0.5 × learned_probability + 0.5 × heuristic_score`. Custom users get `1.0 × heuristic_score` (no model loaded).

A guardrail in `rankSongs()` checks the top-5 after scoring. If average confidence drops below 0.34 or score spread collapses below 0.04, feedback influence is reduced and the event is logged.

---

## 4. Data

- **Catalog:** 50 songs across 16 genres and 9 moods
- **Genres represented:** pop (5), lofi (5), k-pop (4), rock (3), ambient (3), jazz (3), indie pop (3), folk (3), edm (3), r&b (3), classical (3), hip-hop (3), blues (3), synthwave (2), metal (2), electronic (2)
- **Moods represented:** happy, sad, angry, chill, excited, intense, relaxed, moody, focused
- **Song features:** genre, mood, energy (0–1), tempo (BPM), valence (0–1), danceability (0–1), acousticness (0–1)
- **Training data:** 5 demo profiles, each with 8–10 seed feedback events (likes and skips), hand-authored to reflect distinct listening tastes
- **What is missing:** lyrics, language, release decade, subgenre detail (e.g. death metal vs classic rock), artist reputation, and real listener diversity — all five profiles were designed by one developer

---

## 5. Strengths

- Per-profile training fixed the original same-5-songs bug. Alex (lofi/chill) and Maya (pop/excited) now share 0 songs; all 10 pairwise profile comparisons return ≤2 shared songs.
- The mood gate correctly suppresses emotionally wrong songs for adversarial profiles. Riley (high energy + sad mood) gets folk/blues results rather than EDM, because the mood gate overrides the energy signal.
- Scores are fully explainable — every number in the UI traces back to a specific feature, and the "Why" column names the dominant signals including when the learned model is the deciding factor.
- Runs entirely in the browser with no backend. The logistic regression is exported to JSON and re-implemented as a sigmoid function in JavaScript.

---

## 6. Limitations and Biases

**Filter bubble effect.** The system rewards songs closest to what the user already likes. There is no discovery mechanism — a lofi listener will only ever see lofi and adjacent genres. Real platforms partially address this with collaborative filtering, which this system does not implement.

**Mood coordinate simplification.** Emotions like "sad" or "angry" are mapped to two numbers on a valence/arousal grid. This erases cultural, personal, and contextual variation — someone listening to sad music to feel understood is in a different emotional state than someone who wants to cheer up, but the system treats both identically.

**Synthetic training data.** All five profiles were designed by one developer. The learned models reflect those design choices, not real listener diversity. A system trained on actual user feedback would likely produce very different patterns.

**Uneven genre coverage.** Pop and lofi have 5 songs each, but synthwave, metal, and electronic have only 2. A genre match in an underrepresented category carries less weight than it would in a larger, balanced catalog.

**Potential misuse.** The `feedback_events` in `profiles.json` are unsealed — anyone with file access could seed artificial likes to guarantee specific songs always appear in the top-5. A commercial platform could exploit the same mechanism to promote sponsored content while appearing organic. The per-profile model files in `docs/data/models/` are also loaded by the browser with no integrity check; a malicious actor who replaced those files on the server could silently alter what any user sees. Prevention measures in place: feature breakdowns are visible in the UI (transparency), the "why" column explains every ranking (explainability), users can reset feedback at any time (user control). The missing safeguard is model file signature verification.

---

## 7. Evaluation

**Automated tests:** 19/19 pytest tests passing — per-profile model quality, valid probability range, determinism, profile differentiation.

**Consistency checker** (`check_consistency.py`) — 10/10 checks passing:
- Determinism: all 5 profiles return identical top-5 on repeated runs
- Model quality: every per-profile model scores liked songs above skipped songs (margins +0.41 to +0.88)
- Differentiation: all 10 pairwise profile comparisons return ≤2 shared songs

**Confidence:** Average model confidence across evaluated recommendations: 0.9408. These high values almost certainly reflect the small, clean synthetic dataset rather than genuine model quality — real user behavior would be far noisier.

**Guardrail validation:** The guardrail correctly reduces feedback influence when average top-5 confidence drops below 0.34 or score spread collapses below 0.04, and logs the event without crashing.

**Human evaluation:** All five demo profiles and the custom profile mode were manually tested in the browser to verify that profile switching produces visibly different recommendations and that like/skip feedback updates rankings in real time.

**Most surprising finding:** Maya and Sam initially shared all 5 top recommendations despite being labelled "pop" and "k-pop." The root cause was in the data, not the labels — both had liked the same 4 songs and their energy/mood values were nearly identical. Fixing it required three changes together: expanding the catalog, separating their feedback histories, and removing "pop" from Sam's favorite_genres. No single change was sufficient.

---

## 8. Future Work

- **Collaborative filtering:** incorporate what similar users liked, which is one of the most powerful real-world recommendation signals
- **Discover mode:** intentionally surface songs outside the user's normal pattern to break the filter bubble
- **Finer mood options and context modes:** workout, focus, wind-down — tastes are contextual, not fixed
- **Richer explanations:** replace raw score breakdowns with natural language — "Because you loved the low-key vibe of X, here's Y"
- **Model file integrity verification:** sign exported JSON weights and verify the signature in the browser before loading
- **Larger and more balanced catalog:** more songs per genre, subgenre tagging, release decade, lyrics/language metadata

---

## 9. Reflection and AI Collaboration

**What this project taught me about recommender systems:**
A recommender is not making deep inferences about what a person enjoys — it is computing distances between numbers. The interesting engineering challenge is deciding *which* distances matter, how to weight them, and how to stop one strong signal (energy) from completely drowning out a weaker but important one (mood). The mood gate was the clearest example: without it, the system confidently recommended emotionally wrong songs because the numeric signals pointed the other way.

The per-profile model work showed that training data scope is a design decision, not just a data collection problem. The global model was technically correct — it learned real patterns from real feedback — but the scope of that training (all users combined) made it answer the wrong question. Splitting by profile made the models less statistically robust but more semantically correct. That tradeoff — statistical power vs specificity — comes up in almost every real ML system.

**Collaboration with AI:**
This project was built with significant AI assistance for scoring logic, model architecture, test generation, and debugging.

- **Helpful:** When diagnosing why all profiles returned the same recommendations, the AI identified the root cause without being told where to look — the 0.7/0.3 global model weight meant the learned signal dominated regardless of which profile was active, and the global model had been trained on all profiles combined so it had no per-user signal at all. That was a non-obvious architectural bug.
- **Flawed:** When asked to make the "Recommend Top 5" button do something noticeable, the AI proposed adding random noise (±0.15 offsets) to scores on each click. This would have made the button *appear* active by shuffling results randomly, but would have actively degraded recommendation quality — introducing noise into a system designed to be deterministic and explainable. The button was removed instead. The AI's suggestion prioritized visible activity over actual quality, which is a common failure mode worth watching for.
