from __future__ import annotations

from pathlib import Path


class PathSafetyError(RuntimeError):
    """Raised when a path violates NPV Studio's write boundary."""


def _resolved(path: Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def is_within(path: Path, root: Path) -> bool:
    candidate = _resolved(path)
    boundary = _resolved(root)
    return candidate == boundary or boundary in candidate.parents


class PathGuard:
    """Restricts every application write to the configured workspace.

    The Cyberpunk installation is an explicit read-only source. This guard is
    intentionally independent of UI state so pipeline code cannot bypass it.
    """

    def __init__(self, game_root: Path, workspace_root: Path) -> None:
        self.game_root = _resolved(game_root)
        self.workspace_root = _resolved(workspace_root)
        if is_within(self.workspace_root, self.game_root) or is_within(
            self.game_root, self.workspace_root
        ):
            raise PathSafetyError("Game and workspace roots must not overlap")

    def assert_game_read_path(self, path: Path) -> Path:
        candidate = _resolved(path)
        if not is_within(candidate, self.game_root):
            raise PathSafetyError(f"Not inside configured game root: {candidate}")
        return candidate

    def assert_write_path(self, path: Path) -> Path:
        candidate = _resolved(path)
        if is_within(candidate, self.game_root):
            raise PathSafetyError(f"Writing to the game installation is forbidden: {candidate}")
        if not is_within(candidate, self.workspace_root):
            raise PathSafetyError(f"Write target is outside workspace: {candidate}")
        return candidate

    def ensure_directory(self, path: Path) -> Path:
        safe = self.assert_write_path(path)
        safe.mkdir(parents=True, exist_ok=True)
        return safe

    def assert_export_path(self, path: Path, export_root: Path) -> Path:
        """Allow a file only inside a directory explicitly selected by the user."""
        candidate = _resolved(path)
        boundary = _resolved(export_root)
        if (
            is_within(candidate, self.game_root)
            or is_within(boundary, self.game_root)
            or is_within(self.game_root, boundary)
        ):
            raise PathSafetyError(
                f"Export directories must not overlap the game installation: {boundary}"
            )
        if not is_within(candidate, boundary):
            raise PathSafetyError(f"Export target is outside selected directory: {candidate}")
        return candidate

    def ensure_export_directory(self, path: Path) -> Path:
        boundary = _resolved(path)
        safe = self.assert_export_path(boundary, boundary)
        safe.mkdir(parents=True, exist_ok=True)
        return safe

    def write_text(self, path: Path, content: str, encoding: str = "utf-8") -> Path:
        safe = self.assert_write_path(path)
        safe.parent.mkdir(parents=True, exist_ok=True)
        safe.write_text(content, encoding=encoding)
        return safe
