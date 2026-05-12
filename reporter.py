"""
Формирование текстового отчёта.

Структура:
    ┌─ заголовок (дата, общее число найденных браузеров)
    ├─ для каждого браузера:
    │     метаданные (exe, версия, запущен, User Data, число профилей)
    │     для каждого профиля:
    │         метаданные профиля (путь, lock, exit_type)
    │         список проверок: OK / FAIL / N/A
    └─ итоговая сводка
"""

from datetime import datetime


STATUS = {True: "OK  ", False: "FAIL", None: "N/A "}


def _fmt(value, width=14):
    text = "—" if value is None else str(value)
    if len(text) > width:
        text = text[: width - 1] + "…"
    return f"{text:<{width}}"


def build_report(results):
    lines = []
    lines.append("=" * 78)
    lines.append("ОТЧЁТ О ПРОВЕРКЕ КОНФИГУРАЦИИ БРАУЗЕРОВ")
    lines.append(f"Дата: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Обнаружено браузеров: {len(results)}")
    lines.append("=" * 78)

    totals = {"ok": 0, "fail": 0, "na": 0}

    if not results:
        lines.append("")
        lines.append("Ни один из поддерживаемых браузеров не найден.")
        lines.append("Поддерживаемые: Google Chrome, Yandex Browser, Opera.")
    else:
        for browser in results:
            _render_browser(browser, lines, totals)

    lines.append("")
    lines.append("-" * 78)
    lines.append(
        f"ИТОГО проверок: OK={totals['ok']}, FAIL={totals['fail']}, "
        f"N/A={totals['na']}"
    )
    lines.append("-" * 78)
    return "\n".join(lines)


def _render_browser(browser, lines, totals):
    lines.append("")
    lines.append(f"[ {browser['display_name']} ]")
    lines.append(f"  Исполняемый файл : {browser.get('exe_path') or '—'}")
    lines.append(f"  Версия           : {browser.get('version') or '—'}")
    lines.append(f"  Процесс запущен  : {'да' if browser.get('running') else 'нет'}")
    lines.append(f"  User Data        : {browser.get('user_data_dir') or '—'}")
    lines.append(f"  Local State      : {browser.get('local_state_path') or '—'}")
    lines.append(f"  Профилей найдено : {len(browser.get('profiles', []))}")

    for profile in browser.get("profiles", []):
        _render_profile(profile, lines, totals)


def _render_profile(profile, lines, totals):
    lines.append("")
    lines.append(f"  --- Профиль: {profile['display_name']} ({profile['name']}) ---")
    lines.append(f"    Путь          : {profile['path']}")
    lines.append(f"    Заблокирован  : {'да' if profile.get('locked') else 'нет'}")
    exit_status = profile.get("exit_status") or {}
    lines.append(
        f"    Прошлый выход : exited_cleanly={exit_status.get('exited_cleanly')}, "
        f"exit_type={exit_status.get('exit_type')}"
    )
    lines.append(f"    Проверки:")
    for check in profile.get("checks", []):
        glyph = STATUS.get(check["ok"], "?   ")
        if check["ok"] is True:
            totals["ok"] += 1
        elif check["ok"] is False:
            totals["fail"] += 1
        else:
            totals["na"] += 1
        lines.append(
            f"      [{glyph}] {check['label']:<34}"
            f" факт={_fmt(check['actual'])}"
            f" эталон={_fmt(check['expected'])}"
            f" — {check['note']}"
        )


def write_report(results, path="report.txt"):
    text = build_report(results)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return text
