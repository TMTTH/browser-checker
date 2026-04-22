import json
from datetime import datetime
from playwright.sync_api import sync_playwright


def load_policies(path="policies.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Ошибка загрузки политик:", e)
        exit()


def find_browsers():
    return ["chromium"]


def get_real_js_setting(prefs):
    profile = prefs.get("profile", {})

    # глобальная настройка
    js = profile.get("default_content_setting_values", {}).get("javascript")
    if js == 1:
        return True
    if js == 2:
        return False

    # управляемые политики
    js = profile.get("managed_default_content_settings", {}).get("javascript")
    if js == 1:
        return True
    if js == 2:
        return False

    # правила (exceptions)
    exceptions = profile.get("content_settings", {}).get("exceptions", {}).get("javascript", {})

    for rule in exceptions.values():
        setting = rule.get("setting")
        if setting == 2:
            return False
        if setting == 1:
            return True

    # по умолчанию включен
    return True


def collect_config(browser):
    prefs_path = r"C:\Users\Matvey\AppData\Local\Google\Chrome\User Data\Default\Preferences"

    try:
        with open(prefs_path, "r", encoding="utf-8") as f:
            prefs = json.load(f)

        js_enabled = get_real_js_setting(prefs)

    except Exception as e:
        print("Ошибка чтения Preferences:", e)
        js_enabled = True

    # проверка cookies через браузер
    with sync_playwright() as p:
        browser_instance = p.chromium.launch(headless=True)
        context = browser_instance.new_context()

        try:
            context.add_cookies([{
                "name": "test",
                "value": "1",
                "domain": "example.com",
                "path": "/"
            }])
            cookies_count = len(context.cookies())
        except:
            cookies_count = 0

        browser_instance.close()

    return {
        "javascript_enabled": js_enabled,
        "cookies_count": cookies_count
    }


def compare(actual, expected):
    results = []

    for key in expected:
        actual_value = actual.get(key)
        expected_value = expected[key]

        status = "OK" if actual_value == expected_value else "FAIL"

        results.append({
            "param": key,
            "actual": actual_value,
            "expected": expected_value,
            "status": status
        })

    return results


def make_report(results):
    filename = "report.txt"
    total_fail = 0

    with open(filename, "w", encoding="utf-8") as f:
        f.write("ОТЧЕТ ПРОВЕРКИ\n")
        f.write(f"Дата: {datetime.now()}\n\n")

        for browser in results:
            f.write(f"Браузер: {browser['name']}\n")

            for r in browser["results"]:
                if r["status"] == "FAIL":
                    total_fail += 1

                f.write(
                    f"{r['param']} → {r['status']} "
                    f"(fact={r['actual']}, expected={r['expected']})\n"
                )

            f.write("\n")

        f.write(f"ИТОГО несоответствий: {total_fail}\n")

    print("Проверка завершена")
    print(f"Найдено несоответствий: {total_fail}")
    print(f"Отчет сохранен в {filename}")


def main():
    print("Проверка конфигурации браузера")

    policies = load_policies()
    browsers = find_browsers()

    if not browsers:
        print("Браузеры не найдены")
        return

    all_results = []

    for browser in browsers:
        print(f"Проверка {browser}...")

        actual = collect_config(browser)
        expected = policies.get(browser, {})

        result = compare(actual, expected)

        all_results.append({
            "name": browser,
            "results": result
        })

    make_report(all_results)


if __name__ == "__main__":
    main()
