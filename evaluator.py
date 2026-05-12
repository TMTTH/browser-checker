"""
Проверки эталонных параметров безопасности из таблицы 4.1.1.

Каждая функция-проверка принимает (prefs, local_state) и возвращает кортеж:
    (actual, ok, note)
где
    actual — реальное значение параметра в браузере,
    ok     — True/False/None (None — не удалось определить, считается N/A),
    note   — короткий пояснительный текст для отчёта.

prefs       — словарь из Preferences (уже смерженный с Secure Preferences),
local_state — словарь из Local State (общие настройки User Data, могут быть None).
"""

from config_reader import effective_value


def check_safe_browsing_enhanced(prefs, local_state):
    enhanced, src1 = effective_value(prefs, "safebrowsing.enhanced")
    if enhanced is True:
        return True, True, f"enhanced=true ({src1})"
    enabled, src2 = effective_value(prefs, "safebrowsing.enabled")
    if enhanced is False and enabled is False:
        return False, False, "Safe Browsing полностью выключен"
    if enabled is True:
        return "standard", False, f"стандартная защита, расширенная не включена ({src2})"
    return None, None, "значение не задано (по умолчанию = standard)"


def check_https_only(prefs, local_state):
    # В современном Chromium ключ называется https_only_mode_enabled.
    val, src = effective_value(prefs, "https_only_mode_enabled")
    if val is None:
        val, src = effective_value(prefs, "https_only_mode.enabled")
    if val is True:
        return True, True, f"включён ({src})"
    if val is False:
        return False, False, f"выключен ({src})"
    return None, None, "значение не задано"


def check_doh_secure(prefs, local_state):
    # DNS-over-HTTPS: mode = "off" | "automatic" | "secure".
    # Может быть в Local State (общая настройка) или в Preferences.
    for label, source in (("preferences", prefs), ("local_state", local_state)):
        if not isinstance(source, dict):
            continue
        # managed policy
        managed_mode = (source.get("policy") or {}).get("DnsOverHttpsMode")
        if managed_mode:
            return managed_mode, managed_mode == "secure", f"{managed_mode} (managed/{label})"
        # пользовательская настройка
        mode = (source.get("dns_over_https") or {}).get("mode")
        if mode:
            return mode, mode == "secure", f"{mode} ({label})"
    return None, None, "значение не задано (используется системный DNS)"


def check_site_per_process(prefs, local_state):
    val, src = effective_value(prefs, "policy.SitePerProcess")
    if val is True:
        return True, True, f"включено политикой ({src})"
    if val is False:
        return False, False, f"явно выключено политикой ({src})"
    # На десктопном Chromium Site Isolation включена по умолчанию,
    # но определить её фактическое состояние из Preferences невозможно.
    return "default", None, "по умолчанию включена в Chromium (не верифицируется)"


def check_extension_blocklist(prefs, local_state):
    # Корпоративная политика ExtensionInstallBlocklist лежит здесь:
    blocklist, src = effective_value(prefs, "extension_install_blocklist")
    if blocklist is None:
        blocklist, src = effective_value(prefs, "extensions.install.blacklist")
    if blocklist == "*" or (isinstance(blocklist, list) and "*" in blocklist):
        return "all_blocked", True, f"запрет на все, кроме allowlist ({src})"

    # Альтернатива: пользователь сам поставил расширения — посчитаем сколько активно.
    extensions = (prefs.get("extensions") or {}).get("settings") or {}
    active = [
        ext_id for ext_id, ext in extensions.items()
        if isinstance(ext, dict) and ext.get("state") == 1
    ]
    if not active:
        return "none_installed", None, "расширений нет, но политика не задана"
    return f"installed={len(active)}", False, (
        f"установлено активных расширений: {len(active)}, политика не задана"
    )


def check_javascript_enabled(prefs, local_state):
    # 1 = разрешить, 2 = блокировать.
    val, src = effective_value(prefs, "profile.default_content_setting_values.javascript")
    if val == 2:
        return False, False, f"JS заблокирован глобально ({src})"
    if val == 1:
        return True, True, f"JS разрешён ({src})"
    # managed
    val_m, src_m = effective_value(prefs, "profile.managed_default_content_settings.javascript")
    if val_m == 2:
        return False, False, f"JS заблокирован политикой ({src_m})"
    if val_m == 1:
        return True, True, f"JS разрешён политикой ({src_m})"
    return True, True, "по умолчанию разрешён"


CHECKS = {
    "safe_browsing_enhanced": check_safe_browsing_enhanced,
    "https_only_mode":        check_https_only,
    "doh_mode_secure":        check_doh_secure,
    "site_per_process":       check_site_per_process,
    "extension_blocklist":    check_extension_blocklist,
    "javascript_enabled":     check_javascript_enabled,
}
