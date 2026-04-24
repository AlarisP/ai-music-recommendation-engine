const MOOD_MAP = {
  sad: [-1.0, -0.4],
  chill: [0.0, -0.8],
  happy: [0.8, 0.2],
  excited: [0.9, 0.9],
  angry: [-0.7, 0.8],
  intense: [0.7, 0.95],
  relaxed: [0.2, -0.7],
  moody: [-0.3, 0.2],
  focused: [0.3, -0.1]
};

const state = {
  songs: [],
  profiles: [],
  songById: new Map(),
  learnedModel: null,
  activeProfile: null,
  logs: []
};

const TARGET_VALENCE_BY_MOOD = {
  happy: 0.80,
  excited: 0.85,
  chill: 0.60,
  focused: 0.55,
  intense: 0.45,
  moody: 0.35,
  relaxed: 0.65,
  sad: 0.20,
  angry: 0.20
};

const TARGET_DANCEABILITY_BY_MOOD = {
  happy: 0.80,
  excited: 0.85,
  chill: 0.60,
  focused: 0.58,
  relaxed: 0.52,
  moody: 0.50,
  intense: 0.62,
  sad: 0.35,
  angry: 0.65
};

const profileSelect = document.getElementById("profileSelect");
const moodSelect = document.getElementById("moodSelect");
const genreSelect = document.getElementById("genreSelect");
const energyInput = document.getElementById("energyInput");
const tempoInput = document.getElementById("tempoInput");
const acousticInput = document.getElementById("acousticInput");
const energyValue = document.getElementById("energyValue");
const tempoValue = document.getElementById("tempoValue");
const recommendButton = document.getElementById("recommendButton");
const resetButton = document.getElementById("resetButton");
const resultsContainer = document.getElementById("resultsContainer");
const statusText = document.getElementById("statusText");
const logList = document.getElementById("logList");

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function normalizedSimilarity(a, b, span) {
  if (span <= 0) {
    return 0;
  }
  return clamp(1 - Math.abs(a - b) / span, 0, 1);
}

function moodSimilarity(targetMood, songMood) {
  const a = MOOD_MAP[(targetMood || "").toLowerCase()];
  const b = MOOD_MAP[(songMood || "").toLowerCase()];
  if (!a || !b) {
    return targetMood === songMood ? 0.8 : 0.35;
  }
  const dist = Math.hypot(a[0] - b[0], a[1] - b[1]);
  return clamp(1 - dist / 2.83, 0, 1);
}

function genreMatchScore(targetGenre, songGenre, favorites) {
  if ((targetGenre || "").toLowerCase() === (songGenre || "").toLowerCase()) {
    return 1;
  }
  const idx = favorites.findIndex((g) => g.toLowerCase() === (songGenre || "").toLowerCase());
  if (idx >= 0) {
    return clamp(0.75 - idx * 0.08, 0.3, 0.75);
  }
  return 0;
}

function getProfileEvents(profile) {
  const seed = Array.isArray(profile.feedback_events) ? profile.feedback_events : [];
  const localKey = "music_demo_feedback_" + profile.id;
  const localRaw = localStorage.getItem(localKey);
  if (!localRaw) {
    return [...seed];
  }

  try {
    const localEvents = JSON.parse(localRaw);
    if (!Array.isArray(localEvents)) {
      return [...seed];
    }
    return [...seed, ...localEvents];
  } catch {
    return [...seed];
  }
}

function setLocalProfileEvents(profile, localEvents) {
  const localKey = "music_demo_feedback_" + profile.id;
  localStorage.setItem(localKey, JSON.stringify(localEvents));
}

function recordFeedback(profile, songId, action) {
  const localKey = "music_demo_feedback_" + profile.id;
  let localEvents = [];

  try {
    localEvents = JSON.parse(localStorage.getItem(localKey) || "[]");
  } catch {
    localEvents = [];
  }

  localEvents.push({
    song_id: songId,
    action,
    source: "live"
  });

  setLocalProfileEvents(profile, localEvents);
}

function feedbackAdjustment(profile, song) {
  const events = getProfileEvents(profile);
  const liked = new Set();
  const skipped = new Set();

  const artistTally = {};
  const genreTally = {};
  const moodTally = {};

  for (const event of events) {
    const weight = event.action === "like" ? 1 : event.action === "skip" ? -1 : 0;
    const eventSong = state.songById.get(event.song_id);
    if (!eventSong || weight === 0) {
      continue;
    }

    if (event.action === "like") {
      liked.add(event.song_id);
    }
    if (event.action === "skip") {
      skipped.add(event.song_id);
    }

    artistTally[eventSong.artist] = (artistTally[eventSong.artist] || 0) + weight;
    genreTally[eventSong.genre] = (genreTally[eventSong.genre] || 0) + weight;
    moodTally[eventSong.mood] = (moodTally[eventSong.mood] || 0) + weight;
  }

  const direct = liked.has(song.id) ? 0.3 : skipped.has(song.id) ? -0.35 : 0;
  const artist = clamp((artistTally[song.artist] || 0) * 0.07, -0.2, 0.2);
  const genre = clamp((genreTally[song.genre] || 0) * 0.06, -0.18, 0.18);
  const mood = clamp((moodTally[song.mood] || 0) * 0.05, -0.14, 0.14);

  return {
    direct,
    artist,
    genre,
    mood,
    total: clamp(direct + artist + genre + mood, -0.35, 0.35)
  };
}

function buildLearnedFeatureVector(profile, song) {
  return [
    genreMatchScore(profile.genre, song.genre, profile.favorite_genres || []),
    moodSimilarity(profile.mood, song.mood),
    normalizedSimilarity(Number(profile.tempo_bpm || 100), Number(song.tempo_bpm), 80),
    normalizedSimilarity(Number(profile.energy || 0.6), Number(song.energy), 1),
    normalizedSimilarity(profile.likes_acoustic ? 0.8 : 0.2, Number(song.acousticness), 1),
    normalizedSimilarity(TARGET_VALENCE_BY_MOOD[(profile.mood || "").toLowerCase()] ?? 0.55, Number(song.valence), 1),
    normalizedSimilarity(TARGET_DANCEABILITY_BY_MOOD[(profile.mood || "").toLowerCase()] ?? 0.60, Number(song.danceability), 1)
  ];
}

function predictLearnedProbability(model, features) {
  if (!model) {
    return null;
  }

  const standardized = features.map((value, index) => (value - model.means[index]) / model.scales[index]);
  const logit = standardized.reduce((sum, value, index) => sum + value * model.coefficients[index], model.intercept);
  return 1 / (1 + Math.exp(-logit));
}

function scoreSong(profile, song, feedbackCap = 0.35) {
  const targetMood = moodSelect.value;
  const targetGenre = genreSelect.value;
  const targetEnergy = Number(energyInput.value);
  const targetTempo = Number(tempoInput.value);
  const likesAcoustic = acousticInput.checked;

  const moodScore = moodSimilarity(targetMood, song.mood);
  const energyScore = normalizedSimilarity(targetEnergy, Number(song.energy), 1);
  const tempoScore = normalizedSimilarity(targetTempo, Number(song.tempo_bpm), 110);
  const genreScore = genreMatchScore(targetGenre, song.genre, profile.favorite_genres || []);
  const acousticTarget = likesAcoustic ? 0.8 : 0.2;
  const acousticScore = normalizedSimilarity(acousticTarget, Number(song.acousticness), 1);

  const base =
    0.30 * moodScore +
    0.25 * energyScore +
    0.20 * genreScore +
    0.15 * tempoScore +
    0.10 * acousticScore;

  const feedback = feedbackAdjustment(profile, song);
  const cappedFeedback = clamp(feedback.total, -feedbackCap, feedbackCap);
  const heuristicScore = clamp(base + cappedFeedback, 0, 1);

  const learnedFeatures = buildLearnedFeatureVector(
    {
      ...profile,
      genre: targetGenre,
      mood: targetMood,
      energy: targetEnergy,
      tempo_bpm: targetTempo,
      likes_acoustic: likesAcoustic
    },
    song
  );
  const learnedProbability = predictLearnedProbability(state.learnedModel, learnedFeatures);
  const final = learnedProbability === null
    ? heuristicScore
    : clamp(0.7 * learnedProbability + 0.3 * heuristicScore, 0, 1);

  return {
    score: final,
    base,
    learnedProbability,
    components: {
      moodScore,
      energyScore,
      genreScore,
      tempoScore,
      acousticScore,
      feedback: cappedFeedback
    },
    feedbackBreakdown: feedback
  };
}

function rankSongs(profile) {
  let scored = state.songs.map((song) => ({ song, scored: scoreSong(profile, song) }));
  scored.sort((a, b) => b.scored.score - a.scored.score);

  const topFive = scored.slice(0, 5);
  const avgScore = topFive.reduce((sum, row) => sum + row.scored.score, 0) / Math.max(topFive.length, 1);
  const variance = topFive.reduce((sum, row) => sum + (row.scored.score - avgScore) ** 2, 0) / Math.max(topFive.length, 1);
  const spread = Math.sqrt(variance);

  const guardrailTriggered = avgScore < 0.34 || spread < 0.04;

  if (guardrailTriggered) {
    logEvent("Guardrail activated: low-confidence ranking detected. Feedback influence was reduced.", true);
    scored = state.songs.map((song) => ({ song, scored: scoreSong(profile, song, 0.2) }));
    scored.sort((a, b) => b.scored.score - a.scored.score);
  } else {
    logEvent("Ranking healthy: confidence and score spread passed checks.", false);
  }

  return scored.slice(0, 5);
}

function toPct(value) {
  return (value * 100).toFixed(1) + "%";
}

function recommendationReason(row) {
  const parts = [];
  const c = row.scored.components;

  if (c.moodScore > 0.8) {
    parts.push("mood distance is tight");
  }
  if (c.energyScore > 0.8) {
    parts.push("energy difference is small");
  }
  if (c.genreScore > 0.8) {
    parts.push("genre directly matches");
  }
  if (c.tempoScore > 0.8) {
    parts.push("tempo is close to your target");
  }
  if (c.acousticScore > 0.8) {
    parts.push("acoustic preference aligns");
  }
  if (c.feedback > 0.06) {
    parts.push("feedback history boosts this song");
  }
  if (c.feedback < -0.06) {
    parts.push("feedback history penalizes this song");
  }

  if (typeof row.scored.learnedProbability === "number") {
    if (row.scored.learnedProbability >= 0.75) {
      parts.push("learned model strongly predicts a like");
    } else if (row.scored.learnedProbability >= 0.5) {
      parts.push("learned model sees a moderate fit");
    }
  }

  if (parts.length === 0) {
    return "Balanced match across multiple weak signals.";
  }

  return parts.join(", ") + ".";
}

function renderResults(profile) {
  const rows = rankSongs(profile);
  const confidence = rows[0]?.scored.score || 0;
  statusText.textContent = "Top confidence score: " + confidence.toFixed(3);

  const tableRows = rows.map((row, idx) => {
    const song = row.song;
    const score = row.scored;

    return `
      <tr>
        <td>${idx + 1}</td>
        <td>
          <strong>${song.title}</strong><br>
          <span class="small">${song.artist}</span>
        </td>
        <td>
          <span class="tag">${song.genre}</span>
          <span class="tag">${song.mood}</span>
        </td>
        <td>${score.score.toFixed(3)}</td>
        <td>
          <span class="small">Mood ${toPct(score.components.moodScore)}</span><br>
          <span class="small">Energy ${toPct(score.components.energyScore)}</span><br>
          <span class="small">Genre ${toPct(score.components.genreScore)}</span><br>
          <span class="small">Tempo ${toPct(score.components.tempoScore)}</span><br>
          <span class="small">Acoustic ${toPct(score.components.acousticScore)}</span><br>
          <span class="small">Feedback ${(score.components.feedback >= 0 ? "+" : "") + score.components.feedback.toFixed(3)}</span>
        </td>
        <td>
          ${recommendationReason(row)}
        </td>
        <td>
          <div class="cell-actions">
            <button class="btn btn-primary btn-mini" data-song-id="${song.id}" data-action="like">Like</button>
            <button class="btn btn-secondary btn-mini" data-song-id="${song.id}" data-action="skip">Skip</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  resultsContainer.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Song</th>
            <th>Tags</th>
            <th>Score</th>
            <th>Feature Breakdown</th>
            <th>Why</th>
            <th>Feedback</th>
          </tr>
        </thead>
        <tbody>${tableRows}</tbody>
      </table>
    </div>
  `;

  resultsContainer.querySelectorAll("button[data-song-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const songId = Number(button.getAttribute("data-song-id"));
      const action = button.getAttribute("data-action");
      if (!songId || !action) {
        return;
      }

      recordFeedback(profile, songId, action);
      logEvent("Live feedback added: song " + songId + " -> " + action + ".", false);
      renderResults(profile);
    });
  });
}

function logEvent(message, isAlert) {
  const timestamp = new Date().toLocaleTimeString();
  state.logs.unshift({ message, isAlert, timestamp });
  state.logs = state.logs.slice(0, 8);

  logList.innerHTML = state.logs
    .map((entry) => {
      const cls = entry.isAlert ? "tag alert" : "tag";
      return `<li><span class="${cls}">${entry.timestamp}</span> ${entry.message}</li>`;
    })
    .join("");
}

function fillMoodSelect() {
  const moods = Object.keys(MOOD_MAP);
  moodSelect.innerHTML = moods.map((mood) => `<option value="${mood}">${mood}</option>`).join("");
}

function fillGenreSelect() {
  const genres = [...new Set(state.songs.map((song) => song.genre))].sort();
  genreSelect.innerHTML = genres.map((genre) => `<option value="${genre}">${genre}</option>`).join("");
}

function setProfile(profileId) {
  const profile = state.profiles.find((p) => p.id === profileId);
  if (!profile) {
    return;
  }

  state.activeProfile = profile;
  moodSelect.value = profile.mood;
  genreSelect.value = profile.genre;
  energyInput.value = profile.energy;
  tempoInput.value = profile.tempo_bpm;
  acousticInput.checked = Boolean(profile.likes_acoustic);
  energyValue.textContent = Number(profile.energy).toFixed(2);
  tempoValue.textContent = String(profile.tempo_bpm);

  logEvent("Profile switched to " + profile.name + ".", false);
  renderResults(profile);
}

function resetFeedbackForActiveProfile() {
  if (!state.activeProfile) {
    return;
  }

  localStorage.removeItem("music_demo_feedback_" + state.activeProfile.id);
  logEvent("Local feedback reset for " + state.activeProfile.name + ".", true);
  renderResults(state.activeProfile);
}

async function loadData() {
  try {
    const [songRes, profileRes, modelRes] = await Promise.all([
      fetch("data/songs.json"),
      fetch("data/profiles.json"),
      fetch("data/preference_model.json")
    ]);

    if (!songRes.ok || !profileRes.ok) {
      throw new Error("Could not load JSON data files.");
    }

    state.songs = await songRes.json();
    state.profiles = await profileRes.json();
    state.songById = new Map(state.songs.map((song) => [song.id, song]));

    if (modelRes && modelRes.ok) {
      state.learnedModel = await modelRes.json();
      logEvent("Learned feedback model loaded successfully.", false);
    } else {
      state.learnedModel = null;
      logEvent("Learned feedback model unavailable; using heuristic fallback.", true);
    }

    profileSelect.innerHTML = state.profiles
      .map((profile) => `<option value="${profile.id}">${profile.name}</option>`)
      .join("");

    fillMoodSelect();
    fillGenreSelect();

    profileSelect.addEventListener("change", () => setProfile(profileSelect.value));
    recommendButton.addEventListener("click", () => {
      if (state.activeProfile) {
        logEvent("Manual rerank triggered.", false);
        renderResults(state.activeProfile);
      }
    });
    resetButton.addEventListener("click", resetFeedbackForActiveProfile);

    energyInput.addEventListener("input", () => {
      energyValue.textContent = Number(energyInput.value).toFixed(2);
    });

    tempoInput.addEventListener("input", () => {
      tempoValue.textContent = String(tempoInput.value);
    });

    [moodSelect, genreSelect, acousticInput, energyInput, tempoInput].forEach((element) => {
      element.addEventListener("change", () => {
        if (state.activeProfile) {
          renderResults(state.activeProfile);
        }
      });
    });

    setProfile(state.profiles[0].id);
    logEvent("App boot complete. Data loaded and recommendations ready.", false);
  } catch (error) {
    console.error(error);
    statusText.textContent = "Failed to load app data. Check file paths and refresh.";
    resultsContainer.innerHTML = "<p>Data loading error.</p>";
    logEvent("Fatal startup error: " + error.message, true);
  }
}

loadData();
