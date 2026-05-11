from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

from models import AbilityRow, REQUIRED_HEADERS, make_key


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def upsert_ability_rows(
    sheet_id: str,
    worksheet_name: str,
    service_account_file: str,
    scraped_rows: list[AbilityRow],
) -> dict[str, int]:
    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID is required when writing to Google Sheets.")
    if not Path(service_account_file).exists():
        raise FileNotFoundError(f"Service account file not found: {service_account_file}")

    worksheet = _open_worksheet(sheet_id, worksheet_name, service_account_file)
    values = worksheet.get_all_values()
    if not values:
        raise ValueError(f"Worksheet '{worksheet_name}' is empty. Add the required headers first.")

    header = values[0]
    _validate_headers(header, worksheet_name)

    existing_rows = [_pad_row(row, len(REQUIRED_HEADERS)) for row in values[1:]]
    next_id = _next_numeric_id(existing_rows)
    existing_by_key = {
        make_key(row[1], row[3], row[7], row[8]): index
        for index, row in enumerate(existing_rows)
        if row[1].strip()
    }

    inserted = 0
    updated = 0
    unchanged = 0

    for scraped in scraped_rows:
        key = scraped.key
        if key in existing_by_key:
            existing = existing_rows[existing_by_key[key]]
            original = list(existing)
            existing[1] = scraped.ability
            existing[2] = scraped.description
            existing[3] = scraped.champion
            existing[7] = str(scraped.buff)
            existing[8] = str(scraped.debuff)
            existing[9] = scraped.updated_on
            if not existing[10].strip() and scraped.notes:
                existing[10] = scraped.notes
            if existing == original:
                unchanged += 1
            else:
                updated += 1
            continue

        existing_rows.append(scraped.to_sheet_values(row_id=str(next_id)))
        existing_by_key[key] = len(existing_rows) - 1
        next_id += 1
        inserted += 1

    output = [REQUIRED_HEADERS] + existing_rows
    end_row = len(output)
    worksheet.update(f"A1:K{end_row}", output, value_input_option="USER_ENTERED")

    return {
        "scraped": len(scraped_rows),
        "updated": updated,
        "inserted": inserted,
        "unchanged": unchanged,
        "total_sheet_rows": len(existing_rows),
    }


def check_worksheet_access(
    sheet_id: str,
    worksheet_name: str,
    service_account_file: str,
) -> dict[str, int | str]:
    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID is required to check Google Sheets access.")
    if not Path(service_account_file).exists():
        raise FileNotFoundError(f"Service account file not found: {service_account_file}")

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


def _open_worksheet(sheet_id: str, worksheet_name: str, service_account_file: str) -> gspread.Worksheet:
    credentials = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.worksheet(worksheet_name)


def _validate_headers(header: list[str], worksheet_name: str) -> None:
    missing = [name for name in REQUIRED_HEADERS if name not in header]
    if missing:
        raise ValueError(
            f"Worksheet '{worksheet_name}' is missing required headers: {', '.join(missing)}"
        )
    if header[: len(REQUIRED_HEADERS)] != REQUIRED_HEADERS:
        raise ValueError(
            "The first columns must exactly match: " + " | ".join(REQUIRED_HEADERS)
        )


def _pad_row(row: list[str], length: int) -> list[str]:
    if len(row) >= length:
        return row[:length]
    return row + [""] * (length - len(row))


def _next_numeric_id(rows: list[list[str]]) -> int:
    numeric_ids = []
    for row in rows:
        try:
            numeric_ids.append(int(str(row[0]).strip()))
        except ValueError:
            continue
    return max(numeric_ids, default=0) + 1
