import argparse

from config import load_settings
from models import ABILITIES_HEADERS, MCOC_GG_CHAMPIONS_HEADERS
from scrapers.buffs_scraper import scrape_buffs
from scrapers.debuffs_scraper import scrape_debuffs
from scrapers.mcoc_gg_scraper import scrape_mcoc_gg_champions
from services.master_spreadsheet import check_worksheet_access, upsert_ability_rows
from services.mcoc_gg_staging_spreadsheet import (
    check_mcoc_gg_champions_worksheet_access,
    upsert_mcoc_gg_champion_rows,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape MCOC data into Google Sheets.")
    parser.add_argument(
        "--target",
        choices=["abilities", "staging"],
        default="abilities",
        help="Which spreadsheet target to use.",
    )
    parser.add_argument(
        "--type",
        choices=["all", "buffs", "debuffs", "champions"],
        default="all",
        help="Which ability pages to scrape.",
    )
    parser.add_argument("--check-sheet", action="store_true", help="Verify Google Sheet access and headers.")
    parser.add_argument("--write-sheet", action="store_true", help="Write scraped rows to Google Sheets.")
    parser.add_argument("--update", action="store_true", help="Refresh existing staging rows where supported.")
    parser.add_argument("--champion", help="Limit Champions dry-run/write source data to an exact champion name.")
    parser.add_argument("--headful", action="store_true", help="Run Playwright with a visible browser.")
    parser.add_argument("--limit", type=int, default=0, help="Limit printed dry-run rows.")
    args = parser.parse_args()

    settings = load_settings()

    if args.target == "staging":
        return _run_staging(args, settings)

    if args.type == "champions":
        raise ValueError("Use --target staging when scraping --type champions.")
    if args.update:
        raise ValueError("--update is only supported with --target staging --type champions.")
    if args.champion:
        raise ValueError("--champion is only supported with --target staging --type champions.")

    if args.check_sheet:
        result = check_worksheet_access(
            sheet_id=settings.master_sheet_id,
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
        sheet_id=settings.master_sheet_id,
        worksheet_name=settings.worksheet_name,
        service_account_file=settings.service_account_file,
        scraped_rows=rows,
    )
    print("Google Sheets update complete:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    return 0


def _run_staging(args, settings) -> int:
    if args.type != "champions":
        raise ValueError("--target staging currently supports only --type champions.")

    if args.check_sheet:
        result = check_mcoc_gg_champions_worksheet_access(
            sheet_id=settings.mcoc_gg_sheet_id,
            worksheet_name=settings.mcoc_gg_champions_worksheet_name,
            service_account_file=settings.service_account_file,
        )
        print("Staging Champions sheet access check passed:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        return 0

    rows = scrape_mcoc_gg_champions(
        settings.mcoc_gg_base_url,
        champion_name=args.champion,
    )
    print(f"Scraped {len(rows)} staging Champions rows from {settings.mcoc_gg_base_url}")
    _print_mcoc_gg_champions_summary(rows)

    if not args.write_sheet:
        _print_mcoc_gg_champion_rows(rows, limit=args.limit)
        print("\nStaging dry run complete. Re-run with --write-sheet to update staging Google Sheets.")
        return 0

    result = upsert_mcoc_gg_champion_rows(
        sheet_id=settings.mcoc_gg_sheet_id,
        worksheet_name=settings.mcoc_gg_champions_worksheet_name,
        service_account_file=settings.service_account_file,
        scraped_rows=rows,
        update_existing=True,
    )
    print("Staging Champions update complete:")
    for key, value in result.items():
        if key in {"inserted_champions", "changed_champions"}:
            continue
        print(f"  {key}: {value}")
    _print_staging_update_summary(result)
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
    print("\n" + " | ".join(ABILITIES_HEADERS))
    for row in printable:
        print(" | ".join(row.to_sheet_values()))
    if limit and len(rows) > limit:
        print(f"... {len(rows) - limit} more rows not shown")


def _print_mcoc_gg_champions_summary(rows) -> None:
    with_ids = sum(1 for row in rows if row.mcoc_gg_id)
    print(f"  Rows with unique MCOC.gg ID: {with_ids}")


def _print_mcoc_gg_champion_rows(rows, limit: int = 0) -> None:
    printable = rows[:limit] if limit else rows
    print("\n" + " | ".join(MCOC_GG_CHAMPIONS_HEADERS))
    for row in printable:
        print(" | ".join(row.to_sheet_values()))
    if limit and len(rows) > limit:
        print(f"... {len(rows) - limit} more rows not shown")


def _print_staging_update_summary(result) -> None:
    inserted = result.get("inserted_champions", []) or []
    changed = result.get("changed_champions", []) or []

    if inserted:
        print("New champions inserted:")
        for champion in inserted:
            print(f"  {champion}")

    if changed:
        print("Updated champions:")
        for item in changed:
            champion = item.get("champion", "")
            changes = item.get("changes", [])
            change_text = "; ".join(
                f"{change['field']}: {change['old']} -> {change['new']}"
                for change in changes
            )
            print(f"  {champion}: {change_text}")


if __name__ == "__main__":
    raise SystemExit(main())
