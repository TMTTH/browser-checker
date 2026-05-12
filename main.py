"""
Точка входа автоматизированного средства проверки конфигурации браузеров.

Алгоритм:
    1. Загружаем эталонные политики (policies.json).
    2. Просим detector.py найти установленные браузеры и их профили.
    3. Для каждого браузера читаем Local State.
    4. Для каждого профиля:
          - читаем Preferences + Secure Preferences и мерджим,
          - снимаем состояние (lock, exit_type, exited_cleanly),
          - прогоняем все проверки из evaluator.py,
          - сверяем результат с эталоном из policies.json.
    5. Параллельно фиксируем "статичные" свойства браузера: версию .exe,
       признак "процесс запущен".
    6. Передаём собранный результат в reporter.py — пишем report.txt
       и печатаем его в stdout.
"""

import json
import sys

import config_reader
import detector
import evaluator
import reporter
import state


POLICIES_FILE = "policies.json"
REPORT_FILE = "report.txt"


def load_policies(path=POLICIES_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Ошибка загрузки политик ({path}): {exc}", file=sys.stderr)
        sys.exit(1)


def evaluate_profile(profile, browser_policy, local_state):
    prefs = config_reader.load_json(profile["preferences_path"])
    secure = config_reader.load_json(profile.get("secure_preferences_path"))
    merged = config_reader.merge_prefs(prefs, secure)

    checks = []
    for check_id, check_def in browser_policy.get("checks", {}).items():
        check_fn = evaluator.CHECKS.get(check_id)
        if check_fn is None:
            continue
        actual, ok, note = check_fn(merged, local_state)
        expected = check_def.get("expected")
        # Если эталон задан жёстко и не совпадает с фактом — это FAIL,
        # независимо от того, что вернула проверка (даёт строгий режим
        # для случаев "OK по умолчанию" vs "явно сконфигурировано").
        if expected is not None and ok is True and actual != expected:
            ok = False
            note = f"{note}; фактическое значение != эталона"
        checks.append({
            "id": check_id,
            "label": check_def.get("label", check_id),
            "actual": actual,
            "expected": expected,
            "ok": ok,
            "note": note,
        })

    return {
        "name": profile["name"],
        "display_name": profile["display_name"],
        "path": profile["path"],
        "locked": state.is_profile_locked(profile["path"]),
        "exit_status": state.get_last_exit_status(prefs or {}),
        "checks": checks,
    }


def evaluate_browser(browser, browser_policy):
    local_state = config_reader.load_json(browser.get("local_state_path"))
    profile_reports = [
        evaluate_profile(profile, browser_policy, local_state)
        for profile in browser.get("profiles", [])
    ]
    return {
        "id": browser["id"],
        "display_name": browser["display_name"],
        "exe_path": browser.get("exe_path"),
        "user_data_dir": browser.get("user_data_dir"),
        "local_state_path": browser.get("local_state_path"),
        "version": state.get_file_version(browser.get("exe_path")),
        "running": state.is_process_running(browser["process_name"]),
        "profiles": profile_reports,
    }


def main():
    print("Проверка конфигурации браузеров…")
    policies = load_policies()

    browsers = detector.detect_installed(policies)
    if not browsers:
        print("Поддерживаемые браузеры не обнаружены.")
        reporter.write_report([], REPORT_FILE)
        return

    print(f"Обнаружено браузеров: {len(browsers)}")
    for b in browsers:
        print(f"  - {b['display_name']:<20} профилей: {len(b['profiles'])}")

    results = [
        evaluate_browser(browser, policies.get(browser["id"], {}))
        for browser in browsers
    ]

    text = reporter.write_report(results, REPORT_FILE)
    print()
    print(text)
    print()
    print(f"Отчёт сохранён в {REPORT_FILE}")


if __name__ == "__main__":
    main()
