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
```

`--write-sheet` now inserts new champions and refreshes existing champion rows with updated data.

Optional legacy form:

```bash
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
- `--write-sheet` now inserts missing Champions rows and refreshes existing rows when source data has changed.
- `--update --write-sheet` is optional legacy syntax for the same behavior.
- Existing staging Champions rows are matched by `MCOC.gg ID`.
- If `MCOC.gg ID` is missing, exact `Champion` name matching is used.
- Non-blank `Note` values are preserved.
- Master data is not touched by staging commands.

## Sync Champions from Staging to Master

Sync flagged champion rows from the staging `Champions` table to the master `Champs` table:

```bash
python3 main.py --sync-champs
```

This command performs a one-way sync for champions flagged for update in the master sheet:

1. Reads the master `Champs` worksheet and identifies rows with `Update = 1` flag.
2. Matches each flagged row with staging data by champion name.
3. Copies updated field values from staging to master:
   - Abilities
   - Immunities & Resistances
   - Counters Abilities
   - Counters Champions
   - Release Date
   - Tags
4. Resets the `Update` flag to `0` and updates the `Updated On` timestamp.
5. Skips champions that cannot be matched in staging.

### Example Behavior

Master sheet before sync:
```
ID | Champion      | ... | Abilities | Update | Updated On
1  | Iron Man      | ... | Repulsor  | 1      | 2026-05-10
2  | Captain America| ... | Shield    | 0      | 2026-05-15
```

Staging sheet:
```
MCOC.gg ID | Champion      | ... | Abilities              | Updated On
123        | Iron Man      | ... | Repulsor | Arc Reactor | 2026-05-19
456        | Captain America| ... | Shield | Leadership    | 2026-05-19
```

After sync:
```
ID | Champion      | ... | Abilities              | Update | Updated On
1  | Iron Man      | ... | Repulsor | Arc Reactor | 0      | 2026-05-19
2  | Captain America| ... | Shield    | 0           | 2026-05-15
```

Only Iron Man was synced (Update=1), Captain America was skipped (Update=0). Iron Man's `Abilities` field was updated and the flag was reset. If a champion exists in master but not in staging, it remains unchanged and the `Update` flag stays as-is.
