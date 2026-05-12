"""
Получение динамического состояния браузера: версия, запущен ли процесс,
заблокирован ли профиль, корректно ли завершилась прошлая сессия.

Используем стандартные средства Windows (tasklist, PowerShell), чтобы не
тянуть сторонние зависимости вроде psutil.
"""

import subprocess
from pathlib import Path


def get_file_version(exe_path):
    """Версия из VersionInfo .exe (через PowerShell Get-Item)."""
    if not exe_path:
        return None
    try:
        ps_cmd = (
            f"(Get-Item -LiteralPath '{exe_path}').VersionInfo.FileVersion"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=8,
        )
        version = (result.stdout or "").strip()
        return version or None
    except (OSError, subprocess.SubprocessError):
        return None


def is_process_running(process_name):
    """Простая проверка через tasklist — есть ли процесс с таким именем."""
    if not process_name:
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=8,
        )
        return process_name.lower() in (result.stdout or "").lower()
    except (OSError, subprocess.SubprocessError):
        return False


def is_profile_locked(profile_path):
    """
    Chromium создаёт SingletonLock/SingletonCookie/Singleton при запуске.
    Их наличие — признак того, что профиль сейчас используется (или
    браузер аварийно завершился и не убрал за собой).
    """
    if not profile_path:
        return False
    p = Path(profile_path)
    for marker in ("SingletonLock", "SingletonCookie", "Singleton"):
        m = p / marker
        try:
            if m.exists() or m.is_symlink():
                return True
        except OSError:
            continue
    return False


def get_last_exit_status(prefs):
    """
    Chromium пишет в Preferences состояние последнего выхода:
      profile.exit_type — "Normal" / "Crashed" / "SessionEnded"
      profile.exited_cleanly — true/false
    """
    if not isinstance(prefs, dict):
        return {"exit_type": None, "exited_cleanly": None}
    profile = prefs.get("profile", {}) or {}
    return {
        "exit_type": profile.get("exit_type"),
        "exited_cleanly": profile.get("exited_cleanly"),
    }
