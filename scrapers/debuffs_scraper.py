from datetime import date
from typing import Any

from models import AbilityRow
from scrapers.fandom import clean_text, dedupe_rows, extract_fandom_tables, is_header_row


DEBUFF_SECTIONS = ["Damaging", "Non-Damaging"]


def scrape_debuffs(url: str, updated_on: str | None = None, headless: bool = True) -> list[AbilityRow]:
    scrape_date = updated_on or date.today().isoformat()
    tables = extract_fandom_tables(url, DEBUFF_SECTIONS, headless=headless)
    rows: list[AbilityRow] = []

    for section in DEBUFF_SECTIONS:
        rows.extend(_parse_debuff_rows(tables[section], section, scrape_date))

    return dedupe_rows(rows)


def _parse_debuff_rows(
    rows: list[list[dict[str, Any]]],
    category: str,
    updated_on: str,
) -> list[AbilityRow]:
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
                buff=0,
                debuff=1,
                updated_on=updated_on,
                notes=category,
            )
        )
    return parsed
