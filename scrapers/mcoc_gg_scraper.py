from datetime import date
import json
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from models import McocGgChampionRow


DEFAULT_MCOC_GG_VERSION = "5.38"
JOINER = " | "


def scrape_mcoc_gg_champions(
    base_url: str,
    updated_on: str | None = None,
    champion_name: str | None = None,
) -> list[McocGgChampionRow]:
    scrape_date = updated_on or date.today().isoformat()
    version = _detect_json_version(base_url)

    champions = _load_data(base_url, "champions", version)
    classes = _index_by_id(_load_data(base_url, "class", version))
    abilities = _index_by_id(_load_data(base_url, "abilities", version))
    immunities = _index_by_id(_load_data(base_url, "immunities", version))
    tags = _index_by_id(_load_data(base_url, "tags", version))
    relics = _index_by_id(_load_data(base_url, "relics", version))
    focus = _index_by_id(_load_data(base_url, "focus", version))
    champions_by_id = _index_by_id(champions)

    if champion_name:
        target_name = _normalize_name(champion_name)
        champions = [
            champion
            for champion in champions
            if _normalize_name(champion.get("name")) == target_name
        ]

    rows = [
        _build_champion_row(
            champion,
            classes=classes,
            abilities=abilities,
            immunities=immunities,
            tags=tags,
            relics=relics,
            focus=focus,
            champions_by_id=champions_by_id,
            updated_on=scrape_date,
        )
        for champion in champions
    ]
    return sorted(rows, key=lambda row: row.champion.casefold())


def _build_champion_row(
    champion: dict,
    classes: dict[str, dict],
    abilities: dict[str, dict],
    immunities: dict[str, dict],
    tags: dict[str, dict],
    relics: dict[str, dict],
    focus: dict[str, dict],
    champions_by_id: dict[str, dict],
    updated_on: str,
) -> McocGgChampionRow:
    return McocGgChampionRow(
        mcoc_gg_id=str(champion.get("id", "")),
        champion=_clean(champion.get("name")),
        champion_class=_lookup_name(classes, champion.get("class")),
        relic=_lookup_name(relics, champion.get("relic")),
        focus_attack=_lookup_name(focus, champion.get("focus_attack")),
        focus_defense=_lookup_name(focus, champion.get("focus_defense")),
        abilities=_join_names(abilities, champion.get("ability", [])),
        immunities_resistances=_join_names(immunities, champion.get("immune", [])),
        counters_abilities=_join_names(abilities, champion.get("xability", [])),
        counters_champions=_join_names(champions_by_id, champion.get("xchampion", [])),
        release_date=_clean(champion.get("date")),
        tags=_join_tags(tags, champion.get("tags", [])),
        updated_on=updated_on,
    )


def _detect_json_version(base_url: str) -> str:
    try:
        html = _fetch_text(base_url)
    except Exception:
        return DEFAULT_MCOC_GG_VERSION

    versions = re.findall(r"[?&]v=([0-9.]+)", html)
    if not versions:
        return DEFAULT_MCOC_GG_VERSION
    return versions[-1]


def _load_data(base_url: str, name: str, version: str) -> list[dict]:
    url = urljoin(_base_url(base_url), f"json/{name}.json?v={version}")
    payload = json.loads(_fetch_text(url))
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload
    raise ValueError(f"Unexpected mcoc.gg JSON shape for {name}: {type(payload).__name__}")


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def _base_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/"


def _index_by_id(items: list[dict]) -> dict[str, dict]:
    return {
        str(item["id"]): item
        for item in items
        if "id" in item
    }


def _lookup_name(index: dict[str, dict], value: object) -> str:
    if value is None:
        return ""
    return _clean(index.get(str(value), {}).get("name"))


def _join_names(index: dict[str, dict], values: list) -> str:
    names = [_lookup_name(index, value) for value in values or []]
    return JOINER.join(name for name in names if name)


def _join_tags(index: dict[str, dict], values: list) -> str:
    tag_values = [
        _clean(index.get(str(value), {}).get("tag"))
        for value in values or []
    ]
    return JOINER.join(tag for tag in tag_values if tag)


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _normalize_name(value: object) -> str:
    return _clean(value).casefold()
