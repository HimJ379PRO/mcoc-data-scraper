from datetime import date
from pathlib import Path

import gspread
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials

from models import CHAMPS_HEADERS, CHAMPS_SYNC_FIELDS, CHAMPS_REQUIRED_HEADERS, ChampsMasterRow, McocGgChampionRow, normalize_key_part


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def check_champs_worksheet_access(
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


def sync_flagged_champs(
    master_sheet_id: str,
    champs_worksheet_name: str,
    mcoc_gg_sheet_id: str,
    mcoc_gg_worksheet_name: str,
    service_account_file: str,
) -> dict[str, object]:
    champs_worksheet = _open_worksheet(master_sheet_id, champs_worksheet_name, service_account_file)
    champs_values = champs_worksheet.get_all_values()
    if not champs_values:
        raise ValueError(f"Worksheet '{champs_worksheet_name}' is empty. Add the required headers first.")

    _validate_headers(champs_values[0], champs_worksheet_name)
    champs_header_indices = _build_header_indices(champs_values[0])

    staging_worksheet = _open_worksheet(mcoc_gg_sheet_id, mcoc_gg_worksheet_name, service_account_file)
    staging_values = staging_worksheet.get_all_values()
    if not staging_values:
        raise ValueError(f"Staging worksheet '{mcoc_gg_worksheet_name}' is empty.")

    champs_rows = [_pad_row(row, len(champs_values[0])) for row in champs_values[1:]]
    staging_rows = [_pad_row(row, 14) for row in staging_values[1:]]

    staging_by_name: dict[str, list[str]] = {}
    for row in staging_rows:
        if row and len(row) > 1:
            name_key = normalize_key_part(row[1])
            if name_key:
                staging_by_name[name_key] = row

    synced_champions: list[str] = []
    failed_to_match: list[str] = []
    current_date = date.today().isoformat()
    updated_rows = []

    for index, row in enumerate(champs_rows):
        if not row:
            updated_rows.append(row)
            continue

        update_idx = champs_header_indices.get("Update")
        if update_idx is None or len(row) <= update_idx:
            updated_rows.append(row)
            continue

        update_flag = row[update_idx]
        try:
            update_value = int(update_flag) if update_flag else 0
        except (ValueError, TypeError):
            update_value = 0

        if update_value != 1:
            updated_rows.append(row)
            continue

        champion_idx = champs_header_indices.get("Champion")
        if champion_idx is None or len(row) <= champion_idx:
            updated_rows.append(row)
            continue

        champion_name = row[champion_idx]
        name_key = normalize_key_part(champion_name)

        if name_key not in staging_by_name:
            failed_to_match.append(champion_name)
            updated_rows.append(row)
            continue

        staging_row = staging_by_name[name_key]

        for field_name in CHAMPS_SYNC_FIELDS:
            master_idx = champs_header_indices.get(field_name)
            staging_idx = 6 + list(CHAMPS_SYNC_FIELDS).index(field_name)
            if master_idx is not None and staging_idx < len(staging_row):
                row[master_idx] = staging_row[staging_idx]

        update_idx = champs_header_indices["Update"]
        updated_on_idx = champs_header_indices["Updated On"]
        row[update_idx] = "0"
        row[updated_on_idx] = current_date

        synced_champions.append(champion_name)
        updated_rows.append(row)

    output = [champs_values[0]] + updated_rows
    champs_worksheet.update(f"A1:{chr(64 + len(champs_values[0]))}{len(output)}", output, value_input_option="USER_ENTERED")

    return {
        "synced_champions": synced_champions,
        "failed_to_match": failed_to_match,
        "total_synced": len(synced_champions),
        "total_failed": len(failed_to_match),
    }


def _build_header_indices(header: list[str]) -> dict[str, int]:
    return {name: header.index(name) for name in CHAMPS_REQUIRED_HEADERS if name in header}


def _open_worksheet(sheet_id: str, worksheet_name: str, service_account_file: str) -> gspread.Worksheet:
    if not sheet_id:
        raise ValueError("Sheet ID is required for Champs sheet operations.")
    if not Path(service_account_file).exists():
        raise FileNotFoundError(f"Service account file not found: {service_account_file}")

    credentials = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)
    try:
        return spreadsheet.worksheet(worksheet_name)
    except WorksheetNotFound as exc:
        raise ValueError(
            f"Worksheet '{worksheet_name}' was not found in the spreadsheet. "
            "Create the tab and add the required headers first."
        ) from exc


def _validate_headers(header: list[str], worksheet_name: str) -> None:
    missing = [name for name in CHAMPS_REQUIRED_HEADERS if name not in header]
    if missing:
        raise ValueError(
            f"Worksheet '{worksheet_name}' is missing required headers: {', '.join(missing)}"
        )


def _pad_row(row: list[str], length: int) -> list[str]:
    if len(row) >= length:
        return row[:length]
    return row + [""] * (length - len(row))
