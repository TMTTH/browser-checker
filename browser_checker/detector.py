"""
Автоматическое обнаружение установленных браузеров и их профилей.

Источники сведений (используются по очереди, пока не получим путь):
  1. Реестр Windows — ветка App Paths (HKLM и HKCU).
  2. Известные шаблоны установки (Program Files, LocalAppData, AppData).
  3. Существование каталога User Data — если он есть, считаем браузер
     "был установлен ранее" даже при отсутствующем .exe (мог быть удалён,
     но профиль ещё лежит).
"""

import json
import os
import winreg
from pathlib import Path


def _expand(path):
    if not path:
        return None
    return os.path.expandvars(path)


def _exists(p):
    return p is not None and Path(p).exists()


def _find_exe_in_registry(subkeys):
    """Ищем (Default) значение в HKLM/HKCU\\...\\App Paths\\<exe>."""
    hives = (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER)
    for hive in hives:
        for subkey in subkeys:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    value, _ = winreg.QueryValueEx(key, None)
                    if _exists(value):
                        return value
            except OSError:
                continue
    return None


def _find_exe(browser_def):
    exe = _find_exe_in_registry(browser_def.get("registry_app_paths", []))
    if exe:
        return exe
    for candidate in browser_def.get("exe_candidates", []):
        path = _expand(candidate)
        if _exists(path):
            return path
    return None


def _read_local_state(user_data_dir):
    """Local State лежит в корне User Data, содержит profile.info_cache —
    карту "имя каталога профиля -> метаданные (включая отображаемое имя)."""
    ls_path = Path(user_data_dir) / "Local State"
    if not ls_path.exists():
        return None, None
    try:
        with open(ls_path, "r", encoding="utf-8") as f:
            return json.load(f), str(ls_path)
    except (OSError, json.JSONDecodeError):
        return None, str(ls_path)


def _profile_entry(profile_dir, display_name):
    prefs = profile_dir / "Preferences"
    if not prefs.exists():
        return None
    secure = profile_dir / "Secure Preferences"
    return {
        "name": profile_dir.name,
        "display_name": display_name or profile_dir.name,
        "path": str(profile_dir),
        "preferences_path": str(prefs),
        "secure_preferences_path": str(secure) if secure.exists() else None,
    }


def _find_profiles(user_data_dir, single_profile=False):
    """
    Для Chrome/Yandex: ищем подкаталоги Default и Profile N.
    Для Opera (single_profile=True): сам каталог User Data — это и есть профиль.
    """
    root = Path(user_data_dir)
    if not root.exists():
        return []

    if single_profile:
        entry = _profile_entry(root, "Default")
        return [entry] if entry else []

    local_state, _ = _read_local_state(user_data_dir)
    info_cache = {}
    if local_state:
        info_cache = local_state.get("profile", {}).get("info_cache", {}) or {}

    profiles = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        # Стандартные имена каталогов профилей в Chromium-семействе.
        if child.name != "Default" and not child.name.startswith("Profile "):
            continue
        meta_name = (info_cache.get(child.name) or {}).get("name")
        entry = _profile_entry(child, meta_name)
        if entry:
            profiles.append(entry)
    return profiles


def detect_installed(policies):
    """
    На вход — словарь policies (содержимое policies.json).
    На выходе — список найденных браузеров с их exe, путями и профилями.
    """
    found = []
    for browser_id, defn in policies.items():
        user_data_dir = _expand(defn.get("user_data_dir"))
        exe_path = _find_exe(defn)

        # Считаем браузер "найденным", если есть либо .exe, либо каталог профиля.
        if not _exists(user_data_dir) and not exe_path:
            continue

        local_state_path = None
        if _exists(user_data_dir):
            _, local_state_path = _read_local_state(user_data_dir)

        profiles = _find_profiles(
            user_data_dir,
            single_profile=defn.get("single_profile", False),
        ) if _exists(user_data_dir) else []

        found.append({
            "id": browser_id,
            "display_name": defn.get("display_name", browser_id),
            "process_name": defn.get("process_name", ""),
            "exe_path": exe_path,
            "user_data_dir": user_data_dir if _exists(user_data_dir) else None,
            "local_state_path": local_state_path,
            "profiles": profiles,
        })
    return found
