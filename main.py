import argparse

from config import load_settings
from models import REQUIRED_HEADERS
from scrapers.buffs_scraper import scrape_buffs
from scrapers.debuffs_scraper import scrape_debuffs
from services.google_sheets import check_worksheet_access, upsert_ability_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape MCOC abilities into Google Sheets.")
    parser.add_argument(
        "--type",
        choices=["all", "buffs", "debuffs"],
        default="all",
        help="Which ability pages to scrape.",
    )
    parser.add_argument("--check-sheet", action="store_true", help="Verify Google Sheet access and headers.")
    parser.add_argument("--write-sheet", action="store_true", help="Write scraped rows to Google Sheets.")
    parser.add_argument("--headful", action="store_true", help="Run Playwright with a visible browser.")
    parser.add_argument("--limit", type=int, default=0, help="Limit printed dry-run rows.")
    args = parser.parse_args()

    settings = load_settings()

    if args.check_sheet:
        result = check_worksheet_access(
            sheet_id=settings.google_sheet_id,
            worksheet_name=settings.worksheet_name,
            service_account_file=settings.service_account_file,
        )
        print("Google Sheet access check passed:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        return 0

    rows = _scrape_selected_rows(args.type, settings, headless=not args.headful)

    print(f"Scraped {len(rows)} ability rows for type '{args.type}'")
    _print_validation_summary(rows)

    if not args.write_sheet:
        _print_rows(rows, limit=args.limit)
        print("\nDry run complete. Re-run with --write-sheet to update Google Sheets.")
        return 0

    result = upsert_ability_rows(
        sheet_id=settings.google_sheet_id,
        worksheet_name=settings.worksheet_name,
        service_account_file=settings.service_account_file,
        scraped_rows=rows,
    )
    print("Google Sheets update complete:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    return 0


def _scrape_selected_rows(scrape_type: str, settings, headless: bool):
    rows = []
    if scrape_type in {"all", "buffs"}:
        rows.extend(scrape_buffs(settings.buffs_url, headless=headless))
    if scrape_type in {"all", "debuffs"}:
        rows.extend(scrape_debuffs(settings.debuffs_url, headless=headless))
    return rows


def _print_validation_summary(rows) -> None:
    buffs_count = sum(1 for row in rows if row.buff == 1 and row.debuff == 0)
    debuffs_count = sum(1 for row in rows if row.buff == 0 and row.debuff == 1)
    generic_count = sum(1 for row in rows if row.champion == "Generic")
    champion_specific_count = len(rows) - generic_count
    invalid_type_rows = [row for row in rows if (row.buff, row.debuff) not in {(1, 0), (0, 1)}]
    new_owned_classification = [row for row in rows if row.offensive or row.defensive]

    print(f"  Buffs rows: {buffs_count}")
    print(f"  Debuffs rows: {debuffs_count}")
    print(f"  Generic rows: {generic_count}")
    print(f"  Champion-specific rows: {champion_specific_count}")
    print(f"  Type flag mismatches: {len(invalid_type_rows)}")
    print(f"  Offensive/Defensive populated by scraper: {len(new_owned_classification)}")


def _print_rows(rows, limit: int = 0) -> None:
    printable = rows[:limit] if limit else rows
    print("\n" + " | ".join(REQUIRED_HEADERS))
    for row in printable:
        print(" | ".join(row.to_sheet_values()))
    if limit and len(rows) > limit:
        print(f"... {len(rows) - limit} more rows not shown")


if __name__ == "__main__":
    raise SystemExit(main())
