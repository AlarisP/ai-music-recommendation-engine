"""Renders the music recommender data flow as a PNG using matplotlib."""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(18, 28))
ax.set_xlim(0, 18)
ax.set_ylim(0, 28)
ax.axis("off")
fig.patch.set_facecolor("#f8f9fa")

# ── colour palette ──────────────────────────────────────────────────────────
C_DATA   = "#4A90D9"   # blue  – data sources
C_ENTRY  = "#5BAD72"   # green – entry / output
C_FEAT   = "#E8A838"   # amber – individual feature scores
C_GROUP  = "#9B59B6"   # purple – group scores
C_LOGIC  = "#E74C3C"   # red   – decision / gate
C_RANK   = "#2E86AB"   # teal  – ranking steps
C_TEXT   = "white"

def box(ax, cx, cy, w, h, text, color, fontsize=8.5, radius=0.25, style="round,pad=0.1"):
    rect = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                          boxstyle=style, linewidth=1.2,
                          edgecolor="white", facecolor=color, zorder=3)
    ax.add_patch(rect)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize,
            color=C_TEXT, fontweight="bold", zorder=4,
            multialignment="center", wrap=True)

def diamond(ax, cx, cy, w, h, text, color, fontsize=8):
    xs = [cx, cx + w/2, cx, cx - w/2, cx]
    ys = [cy + h/2, cy, cy - h/2, cy, cy + h/2]
    ax.fill(xs, ys, color=color, zorder=3, linewidth=1.2, edgecolor="white")
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize,
            color=C_TEXT, fontweight="bold", zorder=4, multialignment="center")

def arrow(ax, x1, y1, x2, y2, label="", color="#555"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=1.4, mutation_scale=14), zorder=2)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx + 0.12, my, label, fontsize=7.5, color="#333",
                ha="left", va="center", style="italic")

# ── Title ────────────────────────────────────────────────────────────────────
ax.text(9, 27.4, "Music Recommender — Data Flow & Ranking Pipeline",
        ha="center", va="center", fontsize=14, fontweight="bold", color="#222")

# ── 1. Data Sources ──────────────────────────────────────────────────────────
box(ax, 5,   26.2, 3.0, 0.7, "songs.csv\n(19 songs)", C_DATA, fontsize=9)
box(ax, 13,  26.2, 3.0, 0.7, "users.json\n(alex / jordan / sam)", C_DATA, fontsize=9)

# ── 2. Loaders ───────────────────────────────────────────────────────────────
box(ax, 5,   24.8, 3.0, 0.7, "load_songs()\n→ List[Dict]", C_ENTRY, fontsize=8.5)
box(ax, 13,  24.8, 3.0, 0.7, "profiles[ACTIVE_USER]\n→ user_prefs Dict", C_ENTRY, fontsize=8.5)

arrow(ax, 5,  25.85, 5,  25.15)
arrow(ax, 13, 25.85, 13, 25.15)

# ── 3. recommend_songs() ─────────────────────────────────────────────────────
box(ax, 9, 23.5, 4.5, 0.7, "recommend_songs(user_prefs, songs, k=5)", C_ENTRY, fontsize=9)
arrow(ax, 5,  24.45, 7.8, 23.5)
arrow(ax, 13, 24.45, 10.2, 23.5)

# ── 4. Subgraph border ───────────────────────────────────────────────────────
sg = FancyBboxPatch((0.4, 13.0), 17.2, 9.8,
                    boxstyle="round,pad=0.1", linewidth=2,
                    edgecolor="#9B59B6", facecolor="#f0eaf6", zorder=1)
ax.add_patch(sg)
ax.text(9, 22.65, "_song_score_details()  —  runs once per song",
        ha="center", va="center", fontsize=10, color="#6a1f9e", fontweight="bold")

arrow(ax, 9, 23.15, 9, 22.4, label="for each of 19 songs")

# ── 5. Individual feature scores (two columns) ───────────────────────────────
LEFT, RIGHT = 4.5, 13.5
W, H = 3.6, 0.68

rows = [
    (LEFT,  21.9, "genre_score\nexact=1.0  ·  fallback 0.9/0.8  ·  miss=0.0"),
    (LEFT,  21.0, "mood_score\n2D euclidean distance / 2.83"),
    (LEFT,  20.1, "energy_score\n1 − |Δenergy| / 1.0"),
    (RIGHT, 21.9, "tempo_score\n1 − |Δtempo|  / 80"),
    (RIGHT, 21.0, "valence_score\n1 − |Δvalence| / 1.0"),
    (RIGHT, 20.1, "acoustic_score\n1 − |Δacoustic| / 1.0"),
    (9,     19.2, "dance_score   1 − |Δdance| / 1.0"),
]
for cx, cy, txt in rows:
    box(ax, cx, cy, W, H, txt, C_FEAT, fontsize=7.8)

# ── 6. Group scores ───────────────────────────────────────────────────────────
GW, GH = 3.8, 0.72
groups = [
    (3.2,  17.9, "FEEL\n0.65 × mood + 0.35 × valence"),
    (7.0,  17.9, "INTENSITY\n0.70 × energy + 0.30 × tempo"),
    (11.0, 17.9, "STYLE\n0.55 × acoustic + 0.45 × genre"),
    (14.8, 17.9, "GROOVE\n= dance_score"),
]
for cx, cy, txt in groups:
    box(ax, cx, cy, GW, GH, txt, C_GROUP, fontsize=8)

# Arrows: features → groups
# FEEL ← mood (LEFT,21.0) and valence (RIGHT,21.0)
arrow(ax, LEFT,  20.65, 3.2,  18.26)
arrow(ax, RIGHT, 20.65, 3.2,  18.26)
# INTENSITY ← energy (LEFT,20.1) and tempo (RIGHT,21.9)
arrow(ax, LEFT,  19.74, 7.0,  18.26)
arrow(ax, RIGHT, 21.56, 7.0,  18.26)
# STYLE ← acoustic (RIGHT,20.1) and genre (LEFT,21.9)
arrow(ax, RIGHT, 19.74, 11.0, 18.26)
arrow(ax, LEFT,  21.56, 11.0, 18.26)
# GROOVE ← dance (9, 19.2)
arrow(ax, 9,     18.86, 14.8, 18.26)

# ── 7. Weighted sum ───────────────────────────────────────────────────────────
box(ax, 9, 16.8, 11.0, 0.72,
    "Weighted Sum:  0.38×FEEL  +  0.30×INTENSITY  +  0.22×STYLE  +  0.10×GROOVE",
    "#34495E", fontsize=8.5)
for cx, _, _ in groups:
    arrow(ax, cx, 17.54, 9, 17.16)

# ── 8. Mood gate ──────────────────────────────────────────────────────────────
diamond(ax, 9, 15.8, 5.0, 0.8, "mood_distance > 1.8 ?", C_LOGIC, fontsize=8.5)
arrow(ax, 9, 16.44, 9, 16.2)

box(ax, 5.5, 14.9, 3.8, 0.68,
    "Yes — near-opposite vibe\nfinal ×= max(0.5, gate multiplier)", C_LOGIC, fontsize=7.8)
box(ax, 12.5, 14.9, 3.2, 0.68,
    "No\nscore passes through", "#27AE60", fontsize=8)

arrow(ax, 6.5,  15.8, 6.5,  15.24,  label="Yes")
arrow(ax, 11.5, 15.8, 11.5, 15.24, label="No")

box(ax, 9, 14.0, 3.8, 0.68, "final_score   0.0 – 1.0", "#2C3E50", fontsize=9)
arrow(ax, 5.5,  14.56, 7.6,  14.0)
arrow(ax, 12.5, 14.56, 10.4, 14.0)

# ── end subgraph ─────────────────────────────────────────────────────────────

# ── 9. Post-scoring pipeline ─────────────────────────────────────────────────
steps = [
    (9, 12.8, "Novelty boost:  +0.02 if artist NOT in recent_songs\nthen cap at 1.0", C_RANK),
    (9, 11.7, "All 19 songs collected  →  sort descending", C_RANK),
    (9, 10.6, "Artist diversity pass\n−0.05 per repeated artist already seen in list", C_RANK),
    (9,  9.5, "Re-sort descending on adjusted scores", C_RANK),
    (9,  8.4, "Slice top k", C_RANK),
    (9,  7.3, "_build_explanation()\nflag each component score > 0.8 threshold", C_RANK),
    (9,  6.1, "OUTPUT:  title  ·  score  ·  plain-language reason", C_ENTRY),
]
prev_y = 13.66
arrow(ax, 9, 13.66, 9, 13.14)
for cx, cy, txt, col in steps:
    box(ax, cx, cy, 10.0, 0.72, txt, col, fontsize=8.5)
    if cy < 12.8:
        arrow(ax, cx, prev_y - 0.36, cx, cy + 0.36)
    prev_y = cy

# ── legend ───────────────────────────────────────────────────────────────────
legend_items = [
    (C_DATA,  "Data source"),
    (C_ENTRY, "Entry point / output"),
    (C_FEAT,  "Individual feature score"),
    (C_GROUP, "Group score"),
    (C_LOGIC, "Decision / mood gate"),
    (C_RANK,  "Ranking step"),
]
lx, ly = 0.6, 5.2
ax.text(lx, ly + 0.5, "Legend", fontsize=9, fontweight="bold", color="#333")
for i, (col, label) in enumerate(legend_items):
    bx = lx + (i % 3) * 3.2
    by = ly - (i // 3) * 0.6
    rect = FancyBboxPatch((bx, by - 0.18), 0.38, 0.36,
                          boxstyle="round,pad=0.05", facecolor=col,
                          edgecolor="white", linewidth=0.8, zorder=3)
    ax.add_patch(rect)
    ax.text(bx + 0.52, by, label, fontsize=8, va="center", color="#333")

plt.tight_layout(pad=0.2)
plt.savefig("diagram.png", dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
print("Saved diagram.png")
