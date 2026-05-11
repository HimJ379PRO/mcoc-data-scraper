from datetime import date
from typing import Any

from models import AbilityRow
from scrapers.fandom import clean_text, dedupe_rows, extract_fandom_tables, is_header_row


def scrape_buffs(url: str, updated_on: str | None = None, headless: bool = True) -> list[AbilityRow]:
    scrape_date = updated_on or date.today().isoformat()
    tables = extract_fandom_tables(url, ["Generic", "Champion-Specific"], headless=headless)

    generic = _parse_generic_rows(tables["Generic"], scrape_date)
    generic_names = {row.ability for row in generic}
    champion_specific = _parse_champion_specific_rows(
        tables["Champion-Specific"],
        generic_names,
        scrape_date,
    )
    return dedupe_rows(generic + champion_specific)


def _parse_generic_rows(rows: list[list[dict[str, Any]]], updated_on: str) -> list[AbilityRow]:
    parsed: list[AbilityRow] = []
    for row in rows:
        if len(row) < 3 or is_header_row(row):
            continue

        ability = clean_text(row[1]["text"])
        description = clean_text(row[2]["text"])
        if not ability or not description:
            continue

        parsed.append(
            AbilityRow(
                ability=ability,
                description=description,
                champion="Generic",
                similar_to="",
                offensive="",
                defensive="",
                buff=1,
                debuff=0,
                updated_on=updated_on,
            )
        )
    return parsed


def _parse_champion_specific_rows(
    rows: list[list[dict[str, Any]]],
    generic_names: set[str],
    updated_on: str,
) -> list[AbilityRow]:
    parsed: list[AbilityRow] = []
    for row in rows:
        if len(row) < 4 or is_header_row(row):
            continue

        ability = clean_text(row[1]["text"])
        champion = clean_text(row[2]["text"])
        description = clean_text(row[3]["text"])
        if not ability or not champion or not description:
            continue

        parsed.append(
            AbilityRow(
                ability=ability,
                description=description,
                champion=champion,
                similar_to=_find_similar_to(row[1], generic_names),
                offensive="",
                defensive="",
                buff=1,
                debuff=0,
                updated_on=updated_on,
            )
        )
    return parsed


def _find_similar_to(buff_cell: dict[str, Any], generic_names: set[str]) -> str:
    generic_lookup = {name.casefold(): name for name in generic_names}
    for link in buff_cell.get("links", []):
        normalized = clean_text(link).casefold()
        if normalized in generic_lookup:
            return generic_lookup[normalized]
    return ""
