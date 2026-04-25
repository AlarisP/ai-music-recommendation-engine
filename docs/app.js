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

const STORAGE = {
  customProfile: "music_demo_custom_profile_v1",
  mode: "music_demo_mode_v1"
};

const state = {
  songs: [],
  profiles: [],
  songById: new Map(),
  learnedModel: null,
  profileModels: {},
  activeProfile: null,
  activeMode: "demo",
  customProfile: null,
  currentRows: [],
  lastActionBySong: new Map(),
  currentSelectionSongId: null,
  logs: []
};

const TARGET_VALENCE_BY_MOOD = {
  happy: 0.8,
  excited: 0.85,
  chill: 0.6,
  focused: 0.55,
  intense: 0.45,
  moody: 0.35,
  relaxed: 0.65,
  sad: 0.2,
  angry: 0.2
};

const TARGET_DANCEABILITY_BY_MOOD = {
  happy: 0.8,
  excited: 0.85,
  chill: 0.6,
  focused: 0.58,
  relaxed: 0.52,
  moody: 0.5,
  intense: 0.62,
  sad: 0.35,
  angry: 0.65
};

const demoProfileLabel = document.getElementById("demoProfileLabel");
const customNameLabel = document.getElementById("customNameLabel");
const customGenresLabel = document.getElementById("customGenresLabel");
const profileSelect = document.getElementById("profileSelect");
const customNameInput = document.getElementById("customNameInput");
const customGenresInput = document.getElementById("customGenresInput");
const useCustomButton = document.getElementById("useCustomButton");
const saveCustomButton = document.getElementById("saveCustomButton");
const moodSelect = document.getElementById("moodSelect");
const genreSelect = document.getElementById("genreSelect");
const energyInput = document.getElementById("energyInput");
const tempoInput = document.getElementById("tempoInput");
const acousticInput = document.getElementById("acousticInput");
const energyValue = document.getElementById("energyValue");
const tempoValue = document.getElementById("tempoValue");
const resetButton = document.getElementById("resetButton");
const resultsContainer = document.getElementById("resultsContainer");
const statusText = document.getElementById("statusText");
const logList = document.getElementById("logList");
const nowPlayingText = document.getElementById("nowPlayingText");
const sessionStatsText = document.getElementById("sessionStatsText");
const recentActivityList = document.getElementById("recentActivityList");

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function safeParseJSON(raw, fallback) {
  if (!raw) {
    return fallback;
  }
  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function normalizeGenres(text) {
  return String(text || "")
    .split(",")
    .map((g) => g.trim())
    .filter(Boolean)
    .slice(0, 6);
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
  const idx = (favorites || []).findIndex((g) => g.toLowerCase() === (songGenre || "").toLowerCase());
  if (idx >= 0) {
    return clamp(0.75 - idx * 0.08, 0.3, 0.75);
  }
  return 0;
}

function profileKey(profile) {
  return String(profile.id || "custom_you");
}

function feedbackStorageKey(profile) {
  return "music_demo_feedback_" + profileKey(profile);
}

function activityStorageKey(profile) {
  return "music_demo_activity_" + profileKey(profile);
}

function getProfileEvents(profile) {
  const seed = Array.isArray(profile.feedback_events) ? profile.feedback_events : [];
  const localEvents = safeParseJSON(localStorage.getItem(feedbackStorageKey(profile)), []);
  if (!Array.isArray(localEvents)) {
    return [...seed];
  }
  return [...seed, ...localEvents];
}

function setLocalProfileEvents(profile, localEvents) {
  localStorage.setItem(feedbackStorageKey(profile), JSON.stringify(localEvents));
}

function getProfileActivity(profile) {
  const activity = safeParseJSON(localStorage.getItem(activityStorageKey(profile)), []);
  return Array.isArray(activity) ? activity : [];
}

function setProfileActivity(profile, activity) {
  localStorage.setItem(activityStorageKey(profile), JSON.stringify(activity.slice(0, 60)));
}

function pushActivity(profile, action, song) {
  const activity = getProfileActivity(profile);
  activity.unshift({
    action,
    song_id: song.id,
    title: song.title,
    artist: song.artist,
    at: Date.now()
  });
  setProfileActivity(profile, activity);
}

function recordFeedback(profile, songId, action) {
  const localEvents = safeParseJSON(localStorage.getItem(feedbackStorageKey(profile)), []);
  const normalized = Array.isArray(localEvents) ? localEvents : [];

  const lastForSong = [...normalized].reverse().find((event) => event.song_id === songId && event.source === "live");
  if (lastForSong && lastForSong.action === action) {
    return false;
  }

  normalized.push({
    song_id: songId,
    action,
    source: "live"
  });
  setLocalProfileEvents(profile, normalized);
  return true;
}

function latestFeedbackActionBySong(profile) {
  const map = new Map();
  for (const event of getProfileEvents(profile)) {
    if (!event || typeof event.song_id === "undefined") {
      continue;
    }
    if (event.action === "like" || event.action === "skip") {
      map.set(Number(event.song_id), event.action);
    }
  }
  return map;
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

function recencyAdjustment(profile, song) {
  const activity = getProfileActivity(profile).filter((item) => item.action === "play").slice(0, 8);
  if (activity.length === 0) {
    return 0;
  }

  const exactRecent = activity.slice(0, 3).some((item) => item.song_id === song.id);
  if (exactRecent) {
    return -0.1;
  }

  const sameArtistRecent = activity.slice(0, 4).some((item) => item.artist === song.artist);
  if (sameArtistRecent) {
    return -0.05;
  }

  return 0;
}

function buildLearnedFeatureVector(profile, song) {
  return [
    genreMatchScore(profile.genre, song.genre, profile.favorite_genres || []),
    moodSimilarity(profile.mood, song.mood),
    normalizedSimilarity(Number(profile.tempo_bpm || 100), Number(song.tempo_bpm), 80),
    normalizedSimilarity(Number(profile.energy || 0.6), Number(song.energy), 1),
    normalizedSimilarity(profile.likes_acoustic ? 0.8 : 0.2, Number(song.acousticness), 1),
    normalizedSimilarity(TARGET_VALENCE_BY_MOOD[(profile.mood || "").toLowerCase()] ?? 0.55, Number(song.valence), 1),
    normalizedSimilarity(TARGET_DANCEABILITY_BY_MOOD[(profile.mood || "").toLowerCase()] ?? 0.6, Number(song.danceability), 1)
  ];
}

function predictLearnedProbability(model, features) {
  if (!model) {
    return null;
  }
  if (features.some((v) => !Number.isFinite(v))) {
    return null;
  }
  const standardized = features.map((value, index) => (value - model.means[index]) / model.scales[index]);
  const logit = standardized.reduce((sum, value, index) => sum + value * model.coefficients[index], model.intercept);
  return 1 / (1 + Math.exp(-logit));
}

function currentControlProfile(baseProfile) {
  return {
    ...baseProfile,
    mood: moodSelect.value,
    genre: genreSelect.value,
    energy: Number(energyInput.value),
    tempo_bpm: Number(tempoInput.value),
    likes_acoustic: acousticInput.checked,
    favorite_genres: normalizeGenres(customGenresInput.value).length > 0
      ? normalizeGenres(customGenresInput.value)
      : (baseProfile.favorite_genres || [genreSelect.value])
  };
}

function scoreSong(profile, song, feedbackCap = 0.35) {
  const runtimeProfile = currentControlProfile(profile);
  const moodScore = moodSimilarity(runtimeProfile.mood, song.mood);
  const energyScore = normalizedSimilarity(runtimeProfile.energy, Number(song.energy), 1);
  const tempoScore = normalizedSimilarity(runtimeProfile.tempo_bpm, Number(song.tempo_bpm), 110);
  const genreScore = genreMatchScore(runtimeProfile.genre, song.genre, runtimeProfile.favorite_genres || []);
  const acousticTarget = runtimeProfile.likes_acoustic ? 0.8 : 0.2;
  const acousticScore = normalizedSimilarity(acousticTarget, Number(song.acousticness), 1);

  const base =
    0.3 * moodScore +
    0.25 * energyScore +
    0.2 * genreScore +
    0.15 * tempoScore +
    0.1 * acousticScore;

  const feedback = feedbackAdjustment(profile, song);
  const cappedFeedback = clamp(feedback.total, -feedbackCap, feedbackCap);
  const recency = recencyAdjustment(profile, song);
  const heuristicScore = clamp(base + cappedFeedback + recency, 0, 1);

  const learnedFeatures = buildLearnedFeatureVector(runtimeProfile, song);
  const learnedProbability = predictLearnedProbability(state.learnedModel, learnedFeatures);
  // For demo profiles the per-profile model is meaningful → 0.5/0.5 blend.
  // null model (custom user) → heuristic only.
  let final = learnedProbability === null
    ? clamp(heuristicScore, 0, 1)
    : clamp(0.5 * learnedProbability + 0.5 * heuristicScore, 0, 1);

  const latestAction = state.lastActionBySong.get(song.id);
  if (latestAction === "skip") {
    final = clamp(final - 0.35, 0, 1);
  }
  if (latestAction === "like") {
    final = clamp(final + 0.12, 0, 1);
  }

  return {
    score: final,
    learnedProbability,
    components: {
      moodScore,
      energyScore,
      genreScore,
      tempoScore,
      acousticScore,
      feedback: cappedFeedback,
      recency
    }
  };
}

function rankSongs(profile) {
  state.lastActionBySong = latestFeedbackActionBySong(profile);
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
  if (c.recency < -0.01) {
    parts.push("recent-play penalty reduces repeats");
  }

  if (typeof row.scored.learnedProbability === "number") {
    if (row.scored.learnedProbability >= 0.75) {
      parts.push("learned model strongly predicts a like");
    } else if (row.scored.learnedProbability >= 0.5) {
      parts.push("learned model sees a moderate fit");
    }
  }

  return parts.length === 0
    ? "Balanced match across multiple weak signals."
    : parts.join(", ") + ".";
}

function updateSessionWidgets(profile) {
  const activity = getProfileActivity(profile);
  const plays = activity.filter((item) => item.action === "play").length;
  const likes = activity.filter((item) => item.action === "like").length;
  const skips = activity.filter((item) => item.action === "skip").length;
  const lastPlay = activity.find((item) => item.action === "play");

  sessionStatsText.textContent = `${plays} plays • ${likes} likes • ${skips} skips`;
  nowPlayingText.textContent = lastPlay
    ? `${lastPlay.title} by ${lastPlay.artist}`
    : "No selection yet.";

  const recent = activity.slice(0, 6);
  recentActivityList.innerHTML = recent.length === 0
    ? "<li class='muted'>No personal activity yet.</li>"
    : recent.map((item) => `<li>${item.action.toUpperCase()} • ${item.title} <span class='small'>${item.artist}</span></li>`).join("");
}

function handleSongAction(profile, songId, action) {
  const song = state.songById.get(songId);
  if (!song) {
    return;
  }

  if (action === "play") {
    state.currentSelectionSongId = songId;
    pushActivity(profile, "play", song);
    logEvent(`Selected: ${song.title} - ${song.artist}`, false);
  }

  if (action === "like" || action === "skip") {
    const wasRecorded = recordFeedback(profile, songId, action);
    if (!wasRecorded) {
      logEvent(`Ignored duplicate ${action} on ${song.title}.`, true);
      renderResults(profile);
      return;
    }
    pushActivity(profile, action, song);
    logEvent(`Feedback added: ${song.title} -> ${action}.`, false);

    if (action === "skip") {
      const nextCandidate = state.currentRows.find((row) => {
        if (row.song.id === songId) {
          return false;
        }
        return state.lastActionBySong.get(row.song.id) !== "skip";
      });
      if (nextCandidate) {
        state.currentSelectionSongId = nextCandidate.song.id;
        pushActivity(profile, "play", nextCandidate.song);
        logEvent(`Auto-selected next recommendation: ${nextCandidate.song.title}.`, false);
      }
    }
  }

  renderResults(profile);
}

function renderResults(profile) {
  const rows = rankSongs(profile);
  state.currentRows = rows;

  if (!state.currentSelectionSongId && rows[0]) {
    state.currentSelectionSongId = rows[0].song.id;
  }

  const rowSongIds = new Set(rows.map((row) => row.song.id));
  if (state.currentSelectionSongId && !rowSongIds.has(state.currentSelectionSongId) && rows[0]) {
    state.currentSelectionSongId = rows[0].song.id;
  }

  const feedbackMap = latestFeedbackActionBySong(profile);
  const confidence = rows[0]?.scored.score || 0;
  const profileName = state.activeMode === "custom"
    ? (state.customProfile?.name || "You")
    : (profile.name || "Demo User");
  const selectedSong = rows.find((row) => row.song.id === state.currentSelectionSongId)?.song;
  statusText.textContent = `${profileName} • Top confidence ${confidence.toFixed(3)} • Selection: ${selectedSong ? selectedSong.title : "None"}`;

  const tableRows = rows.map((row, idx) => {
    const song = row.song;
    const score = row.scored;
    const latestAction = feedbackMap.get(song.id);
    const isSelected = state.currentSelectionSongId === song.id;
    const likeDisabled = latestAction === "like" ? "disabled" : "";
    const skipDisabled = latestAction === "skip" ? "disabled" : "";

    return `
      <tr${isSelected ? " class='is-selected'" : ""}>
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
          <span class="small">Feedback ${(score.components.feedback >= 0 ? "+" : "") + score.components.feedback.toFixed(3)}</span><br>
          <span class="small">Recency ${(score.components.recency >= 0 ? "+" : "") + score.components.recency.toFixed(3)}</span>
        </td>
        <td>${recommendationReason(row)}</td>
        <td>
          <div class="cell-actions">
            <button class="btn btn-primary btn-mini" data-song-id="${song.id}" data-action="play">Select</button>
            <button class="btn btn-primary btn-mini" data-song-id="${song.id}" data-action="like" ${likeDisabled}>Like</button>
            <button class="btn btn-secondary btn-mini" data-song-id="${song.id}" data-action="skip" ${skipDisabled}>Skip</button>
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
            <th>Actions</th>
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
      handleSongAction(profile, songId, action);
    });
  });

  updateSessionWidgets(profile);
}

function logEvent(message, isAlert) {
  const timestamp = new Date().toLocaleTimeString();
  state.logs.unshift({ message, isAlert, timestamp });
  state.logs = state.logs.slice(0, 10);

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

function applyProfileToControls(profile) {
  moodSelect.value = profile.mood;
  genreSelect.value = profile.genre;
  energyInput.value = profile.energy;
  tempoInput.value = profile.tempo_bpm;
  acousticInput.checked = Boolean(profile.likes_acoustic);
  energyValue.textContent = Number(profile.energy).toFixed(2);
  tempoValue.textContent = String(profile.tempo_bpm);
  customNameInput.value = profile.name || "";
  customGenresInput.value = (profile.favorite_genres || []).join(", ");
}

function setSaveButtonState(saved) {
  saveCustomButton.classList.toggle("btn-save-saved", saved);
  saveCustomButton.classList.toggle("btn-save-unsaved", !saved);
  saveCustomButton.textContent = saved ? "Profile Saved" : "Save My Profile";
}

function saveCustomProfile() {
  const name = String(customNameInput.value || "You").trim() || "You";
  const favorites = normalizeGenres(customGenresInput.value);
  const profile = {
    id: "custom_you",
    name,
    genre: genreSelect.value,
    favorite_genres: favorites.length > 0 ? favorites : [genreSelect.value],
    mood: moodSelect.value,
    energy: Number(energyInput.value),
    tempo_bpm: Number(tempoInput.value),
    likes_acoustic: acousticInput.checked,
    feedback_events: []
  };

  state.customProfile = profile;
  localStorage.setItem(STORAGE.customProfile, JSON.stringify(profile));
  setSaveButtonState(true);
  logEvent(`Saved personal profile for ${name}.`, false);
}

function loadOrCreateCustomProfile() {
  const saved = safeParseJSON(localStorage.getItem(STORAGE.customProfile), null);
  if (saved && saved.id) {
    state.customProfile = saved;
    return;
  }

  const base = state.profiles[0] || {
    genre: "pop",
    mood: "happy",
    energy: 0.6,
    tempo_bpm: 110,
    likes_acoustic: false,
    favorite_genres: ["pop"]
  };
  state.customProfile = {
    id: "custom_you",
    name: "You",
    genre: base.genre,
    favorite_genres: base.favorite_genres || [base.genre],
    mood: base.mood,
    energy: base.energy,
    tempo_bpm: base.tempo_bpm,
    likes_acoustic: base.likes_acoustic,
    feedback_events: []
  };
}

function setMode(mode) {
  state.activeMode = mode;
  localStorage.setItem(STORAGE.mode, mode);

  if (mode === "custom") {
    if (!state.customProfile) {
      loadOrCreateCustomProfile();
    }
    state.activeProfile = state.customProfile;
    state.learnedModel = null;
    applyProfileToControls(state.customProfile);
    demoProfileLabel.hidden = true;
    customNameLabel.hidden = false;
    customGenresLabel.hidden = false;
    profileSelect.disabled = true;
    saveCustomButton.hidden = false;
    setSaveButtonState(false);
    useCustomButton.textContent = "Use Demo Profiles";
    logEvent(`Switched to personal mode for ${state.customProfile.name}.`, false);
    renderResults(state.customProfile);
    return;
  }

  if (state.profiles.length > 0) {
    setDemoProfile(profileSelect.value || state.profiles[0].id);
  }
}

function setDemoProfile(profileId) {
  const profile = state.profiles.find((p) => String(p.id) === String(profileId));
  if (!profile) {
    return;
  }

  state.activeMode = "demo";
  state.activeProfile = profile;
  state.learnedModel = state.profileModels[profile.id] || null;
  profileSelect.value = profile.id;
  applyProfileToControls(profile);
  profileSelect.disabled = false;
  demoProfileLabel.hidden = false;
  customNameLabel.hidden = true;
  customGenresLabel.hidden = true;
  saveCustomButton.hidden = true;
  useCustomButton.textContent = "Use My Profile";
  logEvent(`Profile switched to demo user ${profile.name}.`, false);
  renderResults(profile);
}

function resetFeedbackForActiveProfile() {
  if (!state.activeProfile) {
    return;
  }

  localStorage.removeItem(feedbackStorageKey(state.activeProfile));
  localStorage.removeItem(activityStorageKey(state.activeProfile));
  logEvent(`Local activity reset for ${state.activeProfile.name || "active profile"}.`, true);
  renderResults(state.activeProfile);
}

function bindEvents() {
  profileSelect.addEventListener("change", () => setDemoProfile(profileSelect.value));
  useCustomButton.addEventListener("click", () => {
    if (state.activeMode === "custom") {
      setMode("demo");
      return;
    }
    saveCustomProfile();
    setMode("custom");
  });
  saveCustomButton.addEventListener("click", () => saveCustomProfile());

  resetButton.addEventListener("click", resetFeedbackForActiveProfile);

  energyInput.addEventListener("input", () => {
    energyValue.textContent = Number(energyInput.value).toFixed(2);
  });

  tempoInput.addEventListener("input", () => {
    tempoValue.textContent = String(tempoInput.value);
  });

  [moodSelect, genreSelect, acousticInput, energyInput, tempoInput].forEach((element) => {
    element.addEventListener("change", () => {
      if (!state.activeProfile) {
        return;
      }
      if (state.activeMode === "custom") {
        setSaveButtonState(false);
      }
      renderResults(state.activeProfile);
    });
  });
}

async function loadData() {
  try {
    const [songRes, profileRes] = await Promise.all([
      fetch("data/songs.json"),
      fetch("data/profiles.json")
    ]);

    if (!songRes.ok || !profileRes.ok) {
      throw new Error("Could not load JSON data files.");
    }

    state.songs = await songRes.json();
    state.profiles = await profileRes.json();
    state.songById = new Map(state.songs.map((song) => [song.id, song]));

    // Load one model per demo profile from docs/data/models/
    const modelFetches = state.profiles.map((profile) =>
      fetch(`data/models/${profile.id}_model.json`)
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => ({ id: profile.id, data }))
        .catch(() => ({ id: profile.id, data: null }))
    );
    const modelResults = await Promise.all(modelFetches);
    let loadedCount = 0;
    for (const { id, data } of modelResults) {
      if (data) {
        state.profileModels[id] = data;
        loadedCount++;
      }
    }
    if (loadedCount > 0) {
      logEvent(`Loaded ${loadedCount} per-profile model(s).`, false);
    } else {
      logEvent("No per-profile models found; using heuristic fallback.", true);
    }

    profileSelect.innerHTML = state.profiles
      .map((profile) => `<option value="${profile.id}">${profile.name}</option>`)
      .join("");

    fillMoodSelect();
    fillGenreSelect();
    loadOrCreateCustomProfile();
    bindEvents();

    const persistedMode = localStorage.getItem(STORAGE.mode);
    if (persistedMode === "demo") {
      setDemoProfile(state.profiles[0].id);
    } else {
      setMode("custom");
    }

    logEvent("App ready. Demo and personal profile modes are active.", false);
  } catch (error) {
    console.error(error);
    statusText.textContent = "Failed to load app data. Check file paths and refresh.";
    resultsContainer.innerHTML = "<p>Data loading error.</p>";
    logEvent("Fatal startup error: " + error.message, true);
  }
}

loadData();
