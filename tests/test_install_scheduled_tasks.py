from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_install_scheduled_tasks_dry_run_uses_custom_radar_time() -> None:
    powershell = shutil.which("pwsh") or shutil.which("powershell.exe")
    if powershell is None:
        pytest.skip("PowerShell is not installed in this environment.")

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PROJECT_ROOT / "scripts" / "install_scheduled_tasks.ps1"),
            "-DryRun",
            "-IncludeRadar",
            "-RadarTime",
            "09:10",
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Hermes Intelligence OS Radar" in result.stdout
    assert "/ST 09:10" in result.stdout
