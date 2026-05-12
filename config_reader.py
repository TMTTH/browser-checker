"""
Чтение и нормализация файлов конфигурации Chromium-браузера.

Главный нюанс — у одного параметра одновременно может быть несколько
значений в разных частях Preferences:
  - выставленное пользователем (раздел верхнего уровня),
  - наложенное корпоративной политикой (раздел "policy"),
  - значение из exceptions (для content settings),
  - значение по умолчанию.
Эта логика "что в итоге действует" реализована в effective_value().
"""

import json
from copy import deepcopy


def load_json(path):
    """Терпимое чтение JSON: если файла нет или он битый, возвращаем None."""
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def merge_prefs(prefs, secure_prefs):
    """
    Secure Preferences — отдельный файл, в котором Chromium хранит часть
    настроек с подписью HMAC (расширения, протоколы и т.п.). Для целей
    проверки достаточно мерджа верхнего уровня: значения из Preferences
    приоритетнее, остальное добираем из Secure Preferences.
    """
    if not prefs and not secure_prefs:
        return {}
    if not secure_prefs:
        return deepcopy(prefs)
    if not prefs:
        return deepcopy(secure_prefs)
    merged = deepcopy(secure_prefs)
    _deep_update(merged, prefs)
    return merged


def _deep_update(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v


def _walk(obj, parts):
    cur = obj
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def effective_value(prefs, dotted_key):
    """
    Возвращает (value, source), где source — "managed" / "user" / "default".
    Приоритет: managed (корпоративная политика) → user (выбор пользователя)
    → default (не задано).
    """
    if not isinstance(prefs, dict):
        return None, "default"

    parts = dotted_key.split(".")

    managed = prefs.get("policy")
    if isinstance(managed, dict):
        val = _walk(managed, parts)
        if val is not None:
            return val, "managed"

    val = _walk(prefs, parts)
    if val is not None:
        return val, "user"

    return None, "default"
