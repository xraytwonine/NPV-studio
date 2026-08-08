from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from npv_studio.core.paths import PathGuard


@dataclass(frozen=True)
class ProcessResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


class ExternalToolRunner:
    """Guarded subprocess runner reserved for the next integration milestone."""

    def __init__(self, guard: PathGuard, enabled: bool = False) -> None:
        self.guard = guard
        self.enabled = enabled

    def run(self, executable: Path, arguments: list[str], working_directory: Path) -> ProcessResult:
        if not self.enabled:
            raise RuntimeError("External tool execution is disabled in alpha settings")
        safe_workdir = self.guard.assert_write_path(working_directory)
        process_options: dict[str, object] = {}
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            process_options.update(
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        completed = subprocess.run(
            [str(executable), *arguments],
            cwd=safe_workdir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            **process_options,
        )
        return ProcessResult(
            command=(str(executable), *arguments),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
