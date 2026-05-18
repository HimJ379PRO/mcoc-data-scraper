from pathlib import Path

import gspread
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials

from models import MCOC_GG_CHAMPIONS_HEADERS, McocGgChampionRow, normalize_key_part


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def check_mcoc_gg_champions_worksheet_access(
    sheet_id: str,
    worksheet_name: str,
    service_account_file: str,
) -> dict[str, int | str]:
    worksheet = _open_worksheet(sheet_id, worksheet_name, service_account_file)
    values = worksheet.get_all_values()
    if not values:
        raise ValueError(f"Worksheet '{worksheet_name}' is empty. Add the required headers first.")

    _validate_headers(values[0], worksheet_name)
    return {
        "worksheet": worksheet.title,
        "rows": len(values),
        "columns": len(values[0]),
    }


def upsert_mcoc_gg_champion_rows(
    sheet_id: str,
    worksheet_name: str,
    service_account_file: str,
    scraped_rows: list[McocGgChampionRow],
    update_existing: bool = False,
) -> dict[str, object]:
    worksheet = _open_worksheet(sheet_id, worksheet_name, service_account_file)
    values = worksheet.get_all_values()
    if not values:
        raise ValueError(f"Worksheet '{worksheet_name}' is empty. Add the required headers first.")

    _validate_headers(values[0], worksheet_name)
    existing_rows = [_pad_row(row, len(MCOC_GG_CHAMPIONS_HEADERS)) for row in values[1:]]

    existing_by_id: dict[str, int] = {}
    existing_by_name: dict[str, int] = {}
    duplicate_rows = 0

    for index, row in enumerate(existing_rows):
        id_key = normalize_key_part(row[0])
        name_key = normalize_key_part(row[1])
        if id_key:
            if id_key in existing_by_id:
                duplicate_rows += 1
            else:
                existing_by_id[id_key] = index
        elif name_key:
            if name_key in existing_by_name:
                duplicate_rows += 1
            else:
                existing_by_name[name_key] = index

    inserted = 0
    updated = 0
    skipped = 0
    inserted_champions: list[str] = []
    changed_champions: list[dict[str, object]] = []

    for scraped in scraped_rows:
        match_index = _find_existing_index(scraped, existing_by_id, existing_by_name)
        if match_index is None:
            existing_rows.append(scraped.to_sheet_values())
            existing_by_id[scraped.id_key] = len(existing_rows) - 1
            inserted += 1
            inserted_champions.append(scraped.champion)
            continue

        if not update_existing:
            skipped += 1
            continue

        existing = existing_rows[match_index]
        note = existing[13]
        refreshed = scraped.to_sheet_values(note=note)
        if refreshed == existing:
            skipped += 1
        else:
            diff = _diff_champion_row(existing, refreshed)
            if diff:
                changed_champions.append({
                    "champion": scraped.champion,
                    "changes": diff,
                })
            existing_rows[match_index] = refreshed
            updated += 1

    output = [MCOC_GG_CHAMPIONS_HEADERS] + existing_rows
    worksheet.update(f"A1:N{len(output)}", output, value_input_option="USER_ENTERED")

    return {
        "scraped": len(scraped_rows),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "duplicates": duplicate_rows,
        "total_sheet_rows": len(existing_rows),
        "inserted_champions": inserted_champions,
        "changed_champions": changed_champions,
    }


def _find_existing_index(
    scraped: McocGgChampionRow,
    existing_by_id: dict[str, int],
    existing_by_name: dict[str, int],
) -> int | None:
    if scraped.id_key and scraped.id_key in existing_by_id:
        return existing_by_id[scraped.id_key]
    if scraped.name_key and scraped.name_key in existing_by_name:
        return existing_by_name[scraped.name_key]
    return None


def _diff_champion_row(existing: list[str], refreshed: list[str]) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    for index in range(1, len(MCOC_GG_CHAMPIONS_HEADERS)):
        old_value = existing[index]
        new_value = refreshed[index]
        if old_value != new_value:
            changes.append({
                "field": MCOC_GG_CHAMPIONS_HEADERS[index],
                "old": old_value,
                "new": new_value,
            })
    return changes


def _open_worksheet(sheet_id: str, worksheet_name: str, service_account_file: str) -> gspread.Worksheet:
    if not sheet_id:
        raise ValueError("MCOC_GG_SHEET_ID is required for staging Champions sheet operations.")
    if not Path(service_account_file).exists():
        raise FileNotFoundError(f"Service account file not found: {service_account_file}")

    credentials = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)
    try:
        return spreadsheet.worksheet(worksheet_name)
    except WorksheetNotFound as exc:
        raise ValueError(
            f"Worksheet '{worksheet_name}' was not found in the staging spreadsheet. "
            "Create the tab and add the required Champions headers first."
        ) from exc


def _validate_headers(header: list[str], worksheet_name: str) -> None:
    missing = [name for name in MCOC_GG_CHAMPIONS_HEADERS if name not in header]
    if missing:
        raise ValueError(
            f"Worksheet '{worksheet_name}' is missing required headers: {', '.join(missing)}"
        )
    if header[: len(MCOC_GG_CHAMPIONS_HEADERS)] != MCOC_GG_CHAMPIONS_HEADERS:
        raise ValueError(
            "The first columns must exactly match: " + " | ".join(MCOC_GG_CHAMPIONS_HEADERS)
        )


def _pad_row(row: list[str], length: int) -> list[str]:
    if len(row) >= length:
        return row[:length]
    return row + [""] * (length - len(row))
