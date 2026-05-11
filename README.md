# MCOC Google Sheets Scraper

Scrapes Marvel Contest of Champions Wiki ability pages with Playwright and upserts rows into the `Abilities` tab of a Google Sheet.

## Sheet Columns

The `Abilities` worksheet must contain these headers in columns `A:K`:

```text
ID | Ability | Description | Champion | Similar To | Offensive | Defensive | Buff | Debuff | Updated On | Notes
```

## Setup

1. Create a Google Cloud service account and download its JSON key.
2. Put the key at `credentials/service-account.json`.
3. Share the Google Sheet with the service account email.
4. Create a `.env` file from `.env.example`.
5. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Dry Run

Dry run scrapes all supported ability pages and prints data without writing to Google Sheets:

```bash
python3 main.py --limit 10
```

Scrape a specific page only:

```bash
python3 main.py --type buffs --limit 5
python3 main.py --type debuffs --limit 5
```

## Check Google Sheet Access

After creating `.env` and sharing the Google Sheet with the service account email, verify that the script can open the sheet and find the required headers:

```bash
python3 main.py --check-sheet
```

## Write To Google Sheets

```bash
python3 main.py --write-sheet
```

Write a specific page only:

```bash
python3 main.py --type buffs --write-sheet
python3 main.py --type debuffs --write-sheet
```

## Mapping Rules

- Generic Buffs rows use `Champion = Generic`.
- Champion-specific Buffs rows use the table's `Unique to` champion value.
- Debuffs rows use `Champion = Generic`.
- Buffs rows use `Buff = 1` and `Debuff = 0`.
- Debuffs rows use `Buff = 0` and `Debuff = 1`.
- New Debuffs rows use `Notes = Damaging` or `Notes = Non-Damaging`.
- Blank existing Debuffs notes are backfilled from the scraper category.
- `Similar To`, `Offensive`, `Defensive`, and non-blank `Notes` are preserved for existing rows.
- Existing rows are matched by `Ability + Champion + Buff + Debuff`.
- Existing `ID` values are preserved.
- New rows receive the next numeric `ID`.
