from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_LANGUAGES = ("en", "ro", "ru")

LANGUAGE_LABELS = {
    "en": "English",
    "ro": "Română",
    "ru": "Русский",
}


@dataclass(frozen=True)
class Texts:
    choose_language: str
    language_saved: str
    main_menu: str
    unauthorized: str
    help: str
    status_button: str
    check_button: str
    wax_button: str
    language_button: str
    help_button: str
    current_mileage: str
    last_wax: str
    distance_since_wax: str
    interval: str
    overrun: str
    next_wax: str
    remaining: str
    not_set: str
    current_not_set: str
    wax_hint: str
    wax_saved: str
    wax_mileage_saved: str
    mileage: str
    strava_unavailable_wax: str
    strava_unavailable_check: str
    current_mileage_missing: str
    wax_number_hint: str
    interval_hint: str
    interval_number_error: str
    interval_range_error: str
    interval_saved: str
    alert_title: str
    km: str


TEXTS = {
    "en": Texts(
        choose_language="Choose language:",
        language_saved="✅ Language saved: English",
        main_menu="Main menu",
        unauthorized="Unauthorized",
        help=(
            "Available commands:\n"
            "/status - current chain status\n"
            "/wax - save current Strava mileage as wax mileage\n"
            "/wax <mileage> - save wax mileage manually\n"
            "/interval <km> - change service interval\n"
            "/check - check Strava now\n"
            "/language - change language\n"
            "/help - show commands"
        ),
        status_button="📊 Status",
        check_button="🔄 Check now",
        wax_button="🫕 Wax now",
        language_button="🌐 Language",
        help_button="❓ Help",
        current_mileage="🚴 Current mileage",
        last_wax="🫕 Last wax",
        distance_since_wax="📏 Since wax",
        interval="🎯 Interval",
        overrun="⚠️ Overrun",
        next_wax="➡️ Next wax",
        remaining="⏳ Remaining",
        not_set="not set",
        current_not_set="🚴 Current mileage: not set",
        wax_hint="Use /wax or /wax <mileage>",
        wax_saved="✅ Chain wax saved.",
        wax_mileage_saved="✅ Wax mileage saved",
        mileage="Mileage",
        strava_unavailable_wax="Strava is temporarily unavailable. Wax mileage was not saved.",
        strava_unavailable_check="Strava is temporarily unavailable. Try again later.",
        current_mileage_missing="Current mileage has not been fetched yet.",
        wax_number_hint="Send mileage as a number: /wax 12910",
        interval_hint="Send interval: /interval 450",
        interval_number_error="Interval must be a number.",
        interval_range_error="Interval must be between 50 and 5000 km.",
        interval_saved="✅ Service interval",
        alert_title="⚠️ Time to wax the chain",
        km="km",
    ),
    "ro": Texts(
        choose_language="Alege limba:",
        language_saved="✅ Limba a fost salvată: Română",
        main_menu="Meniu principal",
        unauthorized="Neautorizat",
        help=(
            "Comenzi disponibile:\n"
            "/status - starea curentă a lanțului\n"
            "/wax - salvează kilometrajul Strava curent ca ceruire\n"
            "/wax <kilometraj> - salvează manual kilometrajul ceruirii\n"
            "/interval <km> - schimbă intervalul de service\n"
            "/check - verifică Strava acum\n"
            "/language - schimbă limba\n"
            "/help - afișează comenzile"
        ),
        status_button="📊 Status",
        check_button="🔄 Verifică acum",
        wax_button="🫕 Ceruire acum",
        language_button="🌐 Limbă",
        help_button="❓ Ajutor",
        current_mileage="🚴 Kilometraj curent",
        last_wax="🫕 Ultima ceruire",
        distance_since_wax="📏 După ceruire",
        interval="🎯 Interval",
        overrun="⚠️ Depășire",
        next_wax="➡️ Următoarea ceruire",
        remaining="⏳ Rămas",
        not_set="nesetat",
        current_not_set="🚴 Kilometraj curent: nesetat",
        wax_hint="Folosește /wax sau /wax <kilometraj>",
        wax_saved="✅ Ceruirea lanțului a fost salvată.",
        wax_mileage_saved="✅ Kilometrajul ceruirii a fost salvat",
        mileage="Kilometraj",
        strava_unavailable_wax="Strava este temporar indisponibilă. Ceruirea nu a fost salvată.",
        strava_unavailable_check="Strava este temporar indisponibilă. Încearcă mai târziu.",
        current_mileage_missing="Kilometrajul curent încă nu a fost obținut.",
        wax_number_hint="Trimite kilometrajul ca număr: /wax 12910",
        interval_hint="Trimite intervalul: /interval 450",
        interval_number_error="Intervalul trebuie să fie un număr.",
        interval_range_error="Intervalul trebuie să fie între 50 și 5000 km.",
        interval_saved="✅ Interval de service",
        alert_title="⚠️ Este timpul să ceruiești lanțul",
        km="km",
    ),
    "ru": Texts(
        choose_language="Выбери язык:",
        language_saved="✅ Язык сохранён: Русский",
        main_menu="Главное меню",
        unauthorized="Unauthorized",
        help=(
            "Доступные команды:\n"
            "/status - текущий статус цепи\n"
            "/wax - записать текущий пробег Strava как проварку\n"
            "/wax <пробег> - записать пробег проварки вручную\n"
            "/interval <км> - изменить интервал обслуживания\n"
            "/check - проверить Strava сейчас\n"
            "/language - изменить язык\n"
            "/help - показать команды"
        ),
        status_button="📊 Статус",
        check_button="🔄 Проверить",
        wax_button="🫕 Проварил",
        language_button="🌐 Язык",
        help_button="❓ Помощь",
        current_mileage="🚴 Текущий пробег",
        last_wax="🫕 Последняя проварка",
        distance_since_wax="📏 После проварки",
        interval="🎯 Интервал",
        overrun="⚠️ Перепробег",
        next_wax="➡️ Следующая проварка",
        remaining="⏳ Осталось",
        not_set="не задана",
        current_not_set="🚴 Текущий пробег: не задан",
        wax_hint="Используй /wax или /wax <пробег>",
        wax_saved="✅ Проварка цепи сохранена.",
        wax_mileage_saved="✅ Пробег проварки сохранён",
        mileage="Пробег",
        strava_unavailable_wax="Strava временно недоступна. Проварку не сохранил.",
        strava_unavailable_check="Strava временно недоступна. Попробуй позже.",
        current_mileage_missing="Текущий пробег ещё не получен.",
        wax_number_hint="Укажи пробег числом: /wax 12910",
        interval_hint="Укажи интервал: /interval 450",
        interval_number_error="Интервал должен быть числом.",
        interval_range_error="Интервал должен быть в диапазоне 50-5000 км.",
        interval_saved="✅ Интервал обслуживания",
        alert_title="⚠️ Пора проварить цепь",
        km="км",
    ),
}


def normalize_language(language: str | None) -> str:
    if language in SUPPORTED_LANGUAGES:
        return language
    return "en"


def get_texts(language: str | None) -> Texts:
    return TEXTS[normalize_language(language)]


def language_from_label(label: str) -> str | None:
    normalized = label.strip().lower()
    for code, language_label in LANGUAGE_LABELS.items():
        if normalized == language_label.lower():
            return code
    return None

