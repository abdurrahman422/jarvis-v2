import random
from pathlib import Path


SUPPORTED_EXTENSIONS = (".mp3", ".wav", ".aac", ".flac", ".m4a")

_playlist: list[Path] = []
_current_index: int = -1


def _load_playlist_from_path(folder_path: str) -> None:
    global _playlist, _current_index
    root = Path(folder_path).expanduser()
    if not root.exists() or not root.is_dir():
        _playlist = []
        _current_index = -1
        return
    _playlist = sorted(
        [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    )
    _current_index = -1


def _start_track(index: int) -> str:
    global _current_index
    if not _playlist:
        return "No songs found. Set a valid music folder in Settings."
    _current_index = max(0, min(index, len(_playlist) - 1))
    track = _playlist[_current_index]
    try:
        # Windows-friendly default app playback.
        track_str = str(track)
        Path(track_str)
        import os

        os.startfile(track_str)
        return f"Playing: {track.name}"
    except OSError as exc:
        return f"Could not start music: {exc}"


def set_music_folder(path: str) -> str:
    _load_playlist_from_path(path)
    if not _playlist:
        return "Music folder saved but no supported audio files were found."
    return f"Music folder ready with {len(_playlist)} tracks."


def play_music(_: str) -> str:
    return _start_track(0)


def play_random_music(_: str) -> str:
    if not _playlist:
        return "No songs found. Set a valid music folder in Settings."
    return _start_track(random.randint(0, len(_playlist) - 1))


def next_track(_: str) -> str:
    if not _playlist:
        return "No songs found. Set a valid music folder in Settings."
    next_idx = _current_index + 1 if _current_index >= 0 else 0
    if next_idx >= len(_playlist):
        next_idx = 0
    return _start_track(next_idx)


def previous_track(_: str) -> str:
    if not _playlist:
        return "No songs found. Set a valid music folder in Settings."
    prev_idx = _current_index - 1 if _current_index > 0 else len(_playlist) - 1
    if prev_idx < 0:
        prev_idx = len(_playlist) - 1
    return _start_track(prev_idx)


def stop_music(_: str) -> str:
    try:
        import subprocess

        # Best-effort stop for common Windows media app.
        subprocess.run(["taskkill", "/IM", "wmplayer.exe", "/F"], capture_output=True, text=True)
        return "Stop command sent to media player."
    except Exception:
        return "Unable to stop media player automatically."
