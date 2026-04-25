# AI Music Recommendation Engine

---

## Original Project (Modules 1–3)

**Project name:** Music Recommender Simulation

The original Modules 1–3 project was a deterministic, rule-based music recommender. Given a user profile (genre, mood, energy, tempo, acoustic preference), it scored every song in a 19-song catalog using hand-crafted feature weights (the catalog has since been expanded to 50 songs) and returned a ranked top-5 list. It had no trained model, no feedback loop, and no browser interface, just a Python script that produced a sorted list with plain-language explanations for each ranking.

---

## Title and Summary

**AI Music Recommendation Engine** is a hybrid content-based recommender that combines  feature based scoring with a per-user trained logistic regression model. It runs entirely in the browser (no backend required) and learns from a user's like/skip history to personalize rankings in real time.

It matters because it demonstrates the full applied AI loop: structured data → feature engineering → trained model → ranked output → human feedback → model improvement. Every score is explainable, decisions are tracable, and the system includes guardrails and a stress testing layer to ensure safety and reliability.

---

## Architecture Overview

![System Diagram](Assets/system_diagram.png)

| Layer | What it does |
|---|---|
| **Data Layer** | `songs.json`, `profiles.json`, and `docs/data/models/` supply songs, demo profiles, and trained model weights |
| **Model Training** | `train_models.py` trains one logistic regression model per demo profile using that profile's liked vs skipped songs, plus a neutral `default_model.json` for real users |
| **Scoring Pipeline** | For each song: heuristic score (mood 30%, energy 25%, genre 20%, tempo 15%, acoustic 10%) + feedback adjustment + recency penalty, blended 50/50 with the per-profile learned model |
| **Evaluator / Guardrails** | `rankSongs()` checks confidence and score spread; if either is too low it reduces feedback influence and logs the event |
| **Testing Layer** | `pytest` (19 tests) + `check_consistency.py` verify determinism, model quality, and profile differentiation |

Demo profiles load their own trained model. Custom ("My Profile") users get heuristic-only scoring so no pre-existing bias influences a blank-slate user.

---

## Setup Instructions

### Web App (GitHub Pages or local)


**Local:**
```bash
python -m http.server 8000 --directory docs
```
Then open `http://localhost:8000`.

**GitHub Pages:** visit the deployed URL in your browser directly.
https://alarisp.github.io/ai-music-recommendation-engine/
---

### Python CLI

1. Clone the repo and create a virtual environment:
   ```bash
   git clone <repo-url>
   cd ai-music-recommendation-engine
   python -m venv .venv
   source .venv/bin/activate      # Mac / Linux
   .venv\Scripts\activate         # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the recommender:
   ```bash
   python -m src.main
   ```

4. Regenerate per-profile model files (after editing profiles or songs):
   ```bash
   python train_models.py
   ```

---

### Running Tests

```bash
pytest
```

13 tests across `tests/test_recommender.py` and `tests/test_ai_model.py`.

### Running the Consistency Checker

```bash
python check_consistency.py
```

Prints a pass/fail report for determinism, model quality, and profile differentiation.

---

## Sample Interactions

### Example 1 — Alex (lofi / chill / low energy / acoustic)

**Input profile:**
```
genre: lofi | mood: chill | energy: 0.35 | tempo: 75 BPM | acoustic: yes
```

**Top 3 output (advanced mode):**
| # | Song | Score |
|---|---|---|
| 1 | Library Rain | 0.995 |
| 2 | Spacewalk Thoughts | 0.964 |
| 3 | Coffee Shop Stories | 0.961 |

**Why it works:** Alex's per-profile model was trained exclusively on lofi/ambient/jazz likes and metal/edm skips. The heuristic and learned model both converge on low-energy acoustic songs, producing a tight, profile-specific list.

---

### Example 2 — Maya (pop / excited / high energy / no acoustic)

**Input profile:**
```
genre: pop | mood: excited | energy: 0.92 | tempo: 132 BPM | acoustic: no
```

**Top 3 output (advanced mode):**
| # | Song | Score |
|---|---|---|
| 1 | Electric Feel | 0.981 |
| 2 | Heartbeat Drop | 0.974 |
| 3 | Gym Hero | 0.968 |

**Why it works:** Maya's model was trained on pop likes (songs 1, 5, 20, 21, 22) and k-pop skips (songs 19, 23). It now strongly prefers pop-specific tracks and avoids k-pop — producing a clearly different list from Sam, who gets k-pop in his top 5.

---

### Example 3 — Riley (edm / sad / very high energy / adversarial profile)

**Input profile:**
```
genre: edm | mood: sad | energy: 0.95 | tempo: 140 BPM | acoustic: yes
```

**Top 3 output (advanced mode):**
| # | Song | Score |
|---|---|---|
| 1 | Rust Belt Hymn | 0.841 |
| 2 | Empty Porch | 0.823 |
| 3 | Morning Aria | 0.765 |

**Why it works:** Riley is intentionally contradictory (high energy + sad mood + likes acoustic). The advanced scorer's mood gate suppresses emotionally wrong songs even when energy and genre partially match. Without the mood gate, high-energy EDM tracks would incorrectly dominate.

---

### Example 4 — Custom User (My Profile mode)

**Input (sliders set to):**
```
genre: jazz | mood: relaxed | energy: 0.40 | tempo: 88 BPM | acoustic: yes
```

**Behavior:** No learned model is loaded. Score is 100% heuristic — the result is fully driven by the slider values with no pre-existing bias. As the user likes and skips songs, the feedback adjuster updates scores in real time within the session.

---

## Design Decisions

**Per-profile models instead of one global model.**
The original system trained a single logistic regression on all five profiles combined. That global model learned a "universal taste" that skewed toward high-energy, high-danceability songs liked by the majority of profiles, causing all five profiles to return nearly the same top-5. Separating the models so each profile trains only on its own feedback events fixed this at the cost of smaller training sets (8 examples per profile). For a production system you would need far more data; for a demo the separation is correct.

**50/50 blend for demo, 100% heuristic for custom.**
The 0.7/0.3 learned/heuristic split in the original code let the learned model dominate. Switching to 50/50 means profile-specific heuristic signals (genre, mood, acoustic preference) have equal influence alongside the model. Custom users get no learned model at all so their blank-slate experience is entirely driven by what they set on the sliders, no inherited bias.

**Logistic regression over a neural network.**
Logistic regression coefficients are human-readable, the model can be serialized to a small JSON file the browser can load directly, and training takes milliseconds. A neural network would offer no real advantage on 19 songs and 8 training examples per profile.

**Guardrails as a hard constraint, not a soft suggestion.**
If average top-5 confidence drops below 0.34 or score spread collapses below 0.04, the system reduces feedback cap and logs the event. This makes low-confidence conditions visible and recoverable rather than silently producing bad output.

**Browser-only inference.**
The logistic regression is exported to JSON and re-implemented in plain JavaScript (`predictLearnedProbability`). This means the app runs on GitHub Pages with zero server cost and zero latency for inference.

---

## Testing Summary

**13/13 pytest tests passed. 5/5 reliability checks passed. Average model confidence across evaluated recommendations: 0.9408. 9/10 consistency checks passed — the system struggled only when two profiles had nearly identical feedback histories (Maya vs Sam), causing full top-5 overlap.**

### Reliability mechanisms used

| Mechanism | Implementation |
|---|---|
| Automated tests | `pytest` — 13 tests covering per-profile model quality, valid probability range, determinism, and profile differentiation |
| Consistency checker | `check_consistency.py` — 3 checks: determinism, model quality (liked > skipped), profile differentiation |
| Confidence scoring | Every song gets a 0.0–1.0 score; `logs/evaluation_report.json` records average confidence (0.9408) per run; guardrails trigger when avg score < 0.34 |
| Logging and error handling | `logs/recommender.log` records scoring errors, skipped songs, and out-of-range values; `ValueError` is raised and logged when required profile fields are missing |
| Human evaluation | The browser app was manually tested across all five demo profiles and the custom profile mode, verifying that switching profiles produces visibly different recommendations and that like/skip feedback updates rankings in real time |

### Consistency checker results

- Check 1 — Determinism: **5/5 PASS** — all profiles return identical top-5 on repeated runs
- Check 2 — Model quality: **5/5 PASS** — every per-profile model scores that profile's liked songs above skipped songs (margins +0.56 to +0.88)
- Check 3 — Differentiation: **9/10 PASS** — Maya vs Sam share all 5 songs (known limitation, see below)

### What worked
- Per-profile training fixed the original same-5-songs bug for profiles with distinct taste signatures
- The mood gate correctly suppresses emotionally wrong songs for adversarial profiles like Riley
- Guardrails catch low-confidence rankings and log them without crashing
- Confidence scores were high and consistent across all three evaluated profiles (0.83–0.999)

### What did not work
- Maya and Sam are too similar (both excited/high-energy/pop-adjacent with overlapping liked songs) for the differentiator to pass. Their feedback histories overlap on 4 songs, so their models converge on the same catalog subset. More diverse seeded feedback or a larger song catalog would resolve this.
- The learned model is trained on synthetic feedback data. Confidence values are high (0.83–0.95) but this reflects the small, clean dataset — real user behavior would be far noisier.

### What I learned from testing
Writing the consistency checker revealed the Maya/Sam overlap problem that no unit test would have caught. Determinism testing confirmed there was no hidden randomness in the pipeline. The model quality check (liked > skipped margin) gave a concrete, numeric measure of whether per-profile training was actually working — which it was, by a significant margin.

---

## Responsible AI Reflection

### Limitations and biases in the system

The most significant bias is the **filter bubble effect**. Because the system rewards songs closest to what a user already stated they like, it has no mechanism to surface genuinely new or surprising music. A user who says they like lofi will only ever see lofi and adjacent genres — the system will never challenge that preference or help them discover something outside it. Real streaming platforms partially address this with collaborative filtering ("users like you also enjoyed"), which this system does not implement.

The **mood coordinate system** is a simplification. Mapping emotions like "sad" or "angry" to two numbers on a valence/arousal grid erases cultural, personal, and contextual variation in what those words mean. Someone listening to sad music to feel understood is in a different state than someone who wants to cheer up — the system treats both identically.

The **synthetic training data** is a structural bias. All five profiles were designed by a developer with specific musical intuitions. The learned models reflect those design choices, not real listener diversity. A system trained on actual user feedback would likely surface very different patterns.

Finally, the **19-song catalog** makes genre scoring near-useless for most profiles — 14 of 16 genres have only one song, so a genre match is mostly luck rather than a meaningful signal.

---

### Could this AI be misused?

A music recommender has limited direct harm potential, but two misuse vectors are worth noting.

First, the `feedback_events` in `profiles.json` are unsealed — anyone with access to the files could seed a profile's history with artificial likes for specific songs to guarantee those songs always appear in the top-5. A commercial platform using this architecture could exploit the same mechanism to promote sponsored content while appearing to surface organic recommendations.

Second, the per-profile model files in `docs/data/models/` are loaded directly by the browser with no integrity check. A malicious actor who could replace those files on the server could silently alter what any user sees.

Prevention measures already in place: scores and feature breakdowns are visible to the user in the UI (transparency), the "why" column explains every ranking (explainability), and users can reset their feedback at any time (user control). The missing safeguard is model file integrity verification — a production system would sign the model files and verify the signature before loading.

---

### What surprised me during reliability testing

The Maya vs Sam differentiation failure was the most surprising result. Maya is a pop profile and Sam is a k-pop profile — on paper they sound different. But when the consistency checker ran, they shared all 5 top recommendations. The root cause was in the feedback data, not the profiles: both had liked the same 4 songs and their energy and mood values were nearly identical. The profiles looked diverse at the label level but were functionally the same to the scoring system.

This was a useful reminder that human-readable labels ("pop" vs "k-pop") do not automatically translate into meaningful numeric separation. The system only knows what the numbers say.

The second surprise was how high the confidence scores were (average 0.9408). On a 19-song catalog with 8 training examples per model, that level of confidence almost certainly reflects overfitting to clean synthetic data rather than genuine model quality. A well-calibrated model on real-world data would likely show much more uncertainty.

---

### Collaboration with AI during this project

This project was built with significant AI assistance throughout. The AI helped write scoring logic, design the per-profile model architecture, generate test cases, and debug the same-5-songs issue.

**One instance where the AI was genuinely helpful:** When diagnosing why all profiles returned the same recommendations, the AI identified the root cause without being explicitly told where to look — the 0.7/0.3 global model weight meant the learned signal dominated regardless of which profile was active, and the global model had been trained on all profiles combined so it had no per-user signal at all. That was a non-obvious architectural bug that would have taken much longer to find manually.

**One instance where the AI's suggestion was flawed:** When asked to make the "Recommend Top 5" button do something noticeable, the AI proposed adding random noise (±0.15 offsets) to song scores on each click. This would have made the button *appear* to do something by shuffling results randomly, but it would have actively made the recommendations worse — introducing noise into a system designed to be deterministic and explainable. The button was removed instead, which was the correct call. The AI's suggestion prioritized visible activity over actual quality, which is a common failure mode worth watching for.

Building this project made the gap between "AI as magic" and "AI as math on structured data" concrete. A recommender is not making deep inferences about what a person enjoys — it is computing distances between numbers. The interesting engineering challenge is deciding *which* distances matter, how to weight them, and how to stop one strong signal (like energy) from completely drowning out a weaker but important one (like mood). The mood gate was the clearest example of this: without it, the system confidently recommended emotionally wrong songs because the numeric signals pointed the other way.

The per-profile model work taught me that training data scope is a design decision, not just a data collection problem. The global model was technically correct — it learned real patterns from real feedback — but the scope of that training (all users combined) made it answer the wrong question. Splitting the data by profile made the models less statistically robust but more semantically correct. That tradeoff — statistical power versus specificity — comes up in almost every real ML system, and seeing it play out concretely on 19 songs and 8 training examples made it much easier to reason about than any textbook explanation.

---

## Loom Walkthrough

Add your walkthrough link here: `LOOM_LINK_HERE`

The video should show: 2–3 profile switches, like/skip feedback affecting rankings, guardrail log output, and the consistency checker running.
avior, reliability/guardrail behavior, and clear outputs.

## Portfolio Reflection Snippet

This project demonstrates that I can move from prototype rules to a production-style applied AI workflow: modular model logic, guardrails, quantitative evaluation, and clear communication of limitations. It reflects an engineering style that values measurable reliability and explainable decision paths, not only output quality.