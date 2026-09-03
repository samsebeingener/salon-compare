"""Карточка Checko: ООО по ОГРН, ИП по ИНН (person) или ОГРНИП."""

from __future__ import annotations

import re
from html import unescape

_MONTHS = {
    "января": "01",
    "февраля": "02",
    "марта": "03",
    "апреля": "04",
    "мая": "05",
    "июня": "06",
    "июля": "07",
    "августа": "08",
    "сентября": "09",
    "октября": "10",
    "ноября": "11",
    "декабря": "12",
}

_DATE_RU = re.compile(
    r"Дата регистрации\s+(\d{1,2})\s+"
    r"(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|"
    r"октября|ноября|декабря)\s+(\d{4})",
    re.IGNORECASE,
)
_DATE_DOT = re.compile(
    r"Дата регистрации\s+(\d{2}\.\d{2}\.\d{4})",
    re.IGNORECASE,
)
_KAD_COUNT = re.compile(r"Арбитражные дела\s+(\d+)", re.IGNORECASE)
_ACTIVITY = re.compile(
    r"Вид деятельности\s+(.+?)\s+(\d{2}\.\d{2})",
    re.IGNORECASE | re.DOTALL,
)


def checko_card_url(ogrn: str, inn: str | None = None) -> str:
    ogrn_digits = re.sub(r"\D", "", ogrn)
    inn_digits = re.sub(r"\D", "", inn or "")
    if len(ogrn_digits) == 13:
        return f"https://checko.ru/company/{ogrn_digits}"
    if len(inn_digits) == 12:
        return f"https://checko.ru/person/{inn_digits}"
    if len(ogrn_digits) == 15:
        return f"https://checko.ru/entrepreneur/{ogrn_digits}"
    return f"https://checko.ru/company/{ogrn_digits}"


def _plain(html: str) -> str:
    text = unescape(re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S))
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def checko_page_matches(html: str, ogrn: str) -> bool:
    return ogrn in html


def checko_registered_at(html: str) -> str | None:
    text = _plain(html)
    match = _DATE_RU.search(text)
    if match is not None:
        day = int(match.group(1))
        month = _MONTHS[match.group(2).lower()]
        return f"{day:02d}.{month}.{match.group(3)}"
    dotted = _DATE_DOT.search(text)
    if dotted is not None:
        return dotted.group(1)
    return None


def checko_status(html: str) -> str | None:
    lowered = _plain(html).lower()
    if "ликвидирован" in lowered or "недействующ" in lowered:
        return "не действует"
    if "действующ" in lowered:
        return "действует"
    return None


def checko_activity(html: str) -> str | None:
    match = _ACTIVITY.search(_plain(html))
    if match is None:
        return None
    name = re.sub(r"\s+", " ", match.group(1)).strip()
    if not name:
        return None
    return f"{name} {match.group(2)}"[:120]


def checko_legal_address(html: str) -> str | None:
    text = _plain(html)
    idx = text.lower().find("юридический адрес")
    if idx < 0:
        return None
    chunk = text[idx : idx + 900]
    hits = list(re.finditer(r"\d{6},\s*г\.\s*", chunk))
    if not hits:
        return None
    start = hits[-1].start()
    tail = chunk[start : start + 140]
    line = re.split(r"Нажмите", tail, maxsplit=1)[0]
    line = re.sub(r"\s+", " ", line).strip(" .>")
    if len(line) < 16:
        return None
    return line[:180]


def checko_kad(html: str) -> str | None:
    match = _KAD_COUNT.search(_plain(html))
    if match is None:
        return None
    count = int(match.group(1))
    if count == 0:
        return "не обнаружено"
    return f"есть дела ({count})"


def checko_fedresurs(html: str) -> str | None:
    text = _plain(html)
    if re.search(r"не опубликов\w+\s+ни одного сообщения", text, re.IGNORECASE):
        return "не обнаружено"
    return None


def checko_efrsb(html: str) -> str | None:
    text = _plain(html)
    if "нет сообщений о банкротстве" in text.lower():
        return "не обнаружено"
    if "не входит в реестр банкротств" in text.lower():
        return "не обнаружено"
    return None
