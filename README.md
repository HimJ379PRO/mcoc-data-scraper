# MCOC Google Sheets Scraper

Scrapes Marvel Contest of Champions data into Google Sheets.

## Sheet Columns

The `Abilities` worksheet must contain these headers in columns `A:K`:

```text
ID | Ability | Description | Champion | Similar To | Offensive | Defensive | Buff | Debuff | Updated On | Note
```

The staging `MCOC.gg Data > Champions` worksheet must contain these headers in columns `A:N`:

```text
MCOC.gg ID | Champion | Class | Relic | Focus Attack | Focus Defense | Abilities | Immunities & Resistances | Counters Abilities | Counters Champions | Release Date | Tags | Updated On | Note
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

Preview staging Champions data from `mcoc.gg`:

```bash
python3 main.py --target staging --type champions --limit 5
python3 main.py --target staging --type champions --champion "Absorbing Man"
```

## Check Google Sheet Access

After creating `.env` and sharing the Google Sheet with the service account email, verify that the script can open the sheet and find the required headers:

```bash
python3 main.py --check-sheet
```

Check the staging Champions worksheet:

```bash
python3 main.py --target staging --check-sheet --type champions
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

Write staging Champions data:

```bash
python3 main.py --target staging --type champions --write-sheet
python3 main.py --target staging --type champions --update --write-sheet
```

## Mapping Rules

- Generic Buffs rows use `Champion = Generic`.
- Champion-specific Buffs rows use the table's `Unique to` champion value.
- Debuffs rows use `Champion = Generic`.
- Buffs rows use `Buff = 1` and `Debuff = 0`.
- Debuffs rows use `Buff = 0` and `Debuff = 1`.
- New Debuffs rows use `Note = Damaging` or `Note = Non-Damaging`.
- Blank existing Debuffs `Note` values are backfilled from the scraper category.
- `Similar To`, `Offensive`, `Defensive`, and non-blank `Note` values are preserved for existing rows.
- Existing rows are matched by `Ability + Champion + Buff + Debuff`.
- Existing `ID` values are preserved.
- New rows receive the next numeric `ID`.

## Staging Champions Mapping

- Staging Champions data is written only to `MCOC.gg Data > Champions`.
- Normal staging writes insert missing Champions rows only.
- Staging update mode refreshes existing Champions rows and inserts missing rows.
- Existing staging Champions rows are matched by `MCOC.gg ID`.
- If `MCOC.gg ID` is missing, exact `Champion` name matching is used.
- Non-blank `Note` values are preserved.
- Master data is not touched by staging commands.
