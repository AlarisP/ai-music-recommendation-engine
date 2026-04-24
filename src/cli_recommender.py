"""Interactive CLI for testing recommendation logic without the web UI.

Run:
python -m src.cli_recommender
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Tuple

try:
    from .main import USER_PROFILES
    from .recommender import load_songs, recommend_songs
except ImportError:
    from main import USER_PROFILES
    from recommender import load_songs, recommend_songs


def _format_row(index: int, item: Tuple[Dict, float, str]) -> str:
    song, score, explanation = item
    short_explanation = explanation[:95] + "..." if len(explanation) > 98 else explanation
    return (
        f"{index:>2}. {song.get('title','Unknown')} | {song.get('artist','Unknown')} | "
        f"{song.get('genre','unknown')} | score={score:.3f}\n"
        f"    reason: {short_explanation}"
    )


def _copy_profile(profile_name: str) -> Dict:
    if profile_name not in USER_PROFILES:
        raise ValueError(f"Unknown profile: {profile_name}")
    profile = deepcopy(USER_PROFILES[profile_name])
    profile.setdefault("favorite_genres", [profile.get("genre", "")])
    profile.setdefault("recent_songs", [])
    return profile


@dataclass
class SessionState:
    profile_name: str
    profile: Dict
    mode: str
    feedback_by_song_id: Dict[int, str]


def _apply_feedback_to_profile(state: SessionState, songs_lookup: Dict[int, Dict]) -> None:
    events = []
    for song_id, action in state.feedback_by_song_id.items():
        events.append({"song_id": song_id, "action": action, "source": "cli"})

    state.profile["feedback_events"] = events

    # Mirror last few "played" artists via feedback preferences to trigger novelty logic.
    recent = []
    for song_id, action in list(state.feedback_by_song_id.items())[-5:]:
        if action == "like":
            song = songs_lookup.get(song_id)
            if song:
                recent.append({"artist": song.get("artist", "")})
    state.profile["recent_songs"] = recent


def _rerank(state: SessionState, songs: List[Dict], songs_lookup: Dict[int, Dict]) -> List[Tuple[Dict, float, str]]:
    _apply_feedback_to_profile(state, songs_lookup)
    return recommend_songs(state.profile, songs, k=5, mode=state.mode)


def _print_help() -> None:
    print("\nCommands:")
    print("  help                  Show this help")
    print("  show                  Reprint current top 5")
    print("  like <rank>           Like ranked song (1-5)")
    print("  skip <rank>           Skip ranked song (1-5)")
    print("  clear <rank>          Clear feedback for ranked song")
    print("  mode <simple|advanced>  Switch scoring mode")
    print("  profile <name>        Switch to seeded profile")
    print("  set mood <value>      Set target mood")
    print("  set genre <value>     Set target genre")
    print("  set energy <0-1>      Set target energy")
    print("  set tempo <bpm>       Set target tempo")
    print("  set acoustic <true|false>  Set acoustic preference")
    print("  quit                  Exit")


def _parse_rank(command: str) -> int:
    parts = command.split()
    if len(parts) != 2 or not parts[1].isdigit():
        raise ValueError("Expected rank command format: <action> <1-5>")
    rank = int(parts[1])
    if rank < 1 or rank > 5:
        raise ValueError("Rank must be between 1 and 5")
    return rank


def main() -> None:
    songs = load_songs("data/songs.csv")
    songs_lookup = {int(song["id"]): song for song in songs}

    print("\nAI Music Recommender CLI")
    print("Use this to test recommendation logic without the web UI.")
    print("Available seeded profiles:", ", ".join(sorted(USER_PROFILES.keys())))

    profile_name = input("\nStart with profile [alex]: ").strip().lower() or "alex"
    if profile_name not in USER_PROFILES:
        print(f"Unknown profile '{profile_name}'. Falling back to alex.")
        profile_name = "alex"

    mode = input("Scoring mode [advanced]: ").strip().lower() or "advanced"
    if mode not in {"simple", "advanced"}:
        print("Invalid mode. Falling back to advanced.")
        mode = "advanced"

    state = SessionState(
        profile_name=profile_name,
        profile=_copy_profile(profile_name),
        mode=mode,
        feedback_by_song_id={},
    )

    _print_help()

    current = _rerank(state, songs, songs_lookup)
    print("\nTop 5 recommendations:")
    for idx, item in enumerate(current, start=1):
        print(_format_row(idx, item))

    while True:
        command = input("\ncli> ").strip()
        if not command:
            continue

        cmd = command.lower()

        try:
            if cmd == "quit":
                print("Goodbye.")
                return

            if cmd == "help":
                _print_help()
                continue

            if cmd == "show":
                for idx, item in enumerate(current, start=1):
                    print(_format_row(idx, item))
                continue

            if cmd.startswith("like "):
                rank = _parse_rank(cmd)
                song_id = int(current[rank - 1][0]["id"])
                state.feedback_by_song_id[song_id] = "like"
                print(f"Recorded like for rank {rank}.")

            elif cmd.startswith("skip "):
                rank = _parse_rank(cmd)
                song_id = int(current[rank - 1][0]["id"])
                state.feedback_by_song_id[song_id] = "skip"
                print(f"Recorded skip for rank {rank}.")

            elif cmd.startswith("clear "):
                rank = _parse_rank(cmd)
                song_id = int(current[rank - 1][0]["id"])
                state.feedback_by_song_id.pop(song_id, None)
                print(f"Cleared feedback for rank {rank}.")

            elif cmd.startswith("mode "):
                next_mode = cmd.split(maxsplit=1)[1].strip()
                if next_mode not in {"simple", "advanced"}:
                    print("Mode must be simple or advanced.")
                    continue
                state.mode = next_mode
                print(f"Mode set to {next_mode}.")

            elif cmd.startswith("profile "):
                next_profile = cmd.split(maxsplit=1)[1].strip()
                if next_profile not in USER_PROFILES:
                    print("Unknown profile. Use one of:", ", ".join(sorted(USER_PROFILES.keys())))
                    continue
                state.profile_name = next_profile
                state.profile = _copy_profile(next_profile)
                state.feedback_by_song_id = {}
                print(f"Switched to profile {next_profile}.")

            elif cmd.startswith("set "):
                parts = command.split(maxsplit=2)
                if len(parts) < 3:
                    print("Use format: set <field> <value>")
                    continue
                field = parts[1].lower()
                raw_value = parts[2].strip()

                if field == "mood":
                    state.profile["mood"] = raw_value.lower()
                elif field == "genre":
                    state.profile["genre"] = raw_value.lower()
                    favs = state.profile.get("favorite_genres") or []
                    if state.profile["genre"] not in favs:
                        state.profile["favorite_genres"] = [state.profile["genre"], *favs][:5]
                elif field == "energy":
                    value = float(raw_value)
                    if not 0.0 <= value <= 1.0:
                        raise ValueError("Energy must be between 0 and 1")
                    state.profile["energy"] = value
                elif field == "tempo":
                    state.profile["tempo_bpm"] = float(raw_value)
                elif field == "acoustic":
                    state.profile["likes_acoustic"] = raw_value.lower() in {"1", "true", "yes", "y", "on"}
                else:
                    print("Unknown field. Allowed: mood, genre, energy, tempo, acoustic")
                    continue
                print(f"Updated {field}.")

            else:
                print("Unknown command. Type help.")
                continue

            current = _rerank(state, songs, songs_lookup)
            print("\nUpdated top 5:")
            for idx, item in enumerate(current, start=1):
                print(_format_row(idx, item))

        except Exception as exc:  # keep CLI interactive despite bad input
            print(f"Error: {exc}")


if __name__ == "__main__":
    main()
