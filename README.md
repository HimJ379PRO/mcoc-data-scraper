# MCOC Data Scraper & Sync Tool

## TL;DR

This tool automatically collects Marvel Contest of Champions game data from multiple sources and keeps your Google Sheets synchronized. It:
- Scrapes ability data (buffs/debuffs) from community wikis
- Fetches champion information from mcoc.gg database
- Syncs updates from a staging table to your master database
- Maintains data consistency with smart matching and deduplication

Perfect for game analysts, content creators, and community managers who need up-to-date MCOC data.

## Tech Stack

- **Language**: Python 3
- **Web Scraping**: Playwright (for dynamic content)
- **Google Sheets API**: gspread
- **Authentication**: Google Service Account (OAuth2)
- **Data Sources**: 
  - Fandom wiki (abilities)
  - mcoc.gg (champions)

## Setup Instructions

### Prerequisites
- Python 3.8+
- Google Cloud project with Sheets API enabled
- A Google Sheet for storing data

### Step 1: Google Cloud Setup
1. Create a Google Cloud service account
2. Download the service account JSON key
3. Place the key at: `credentials/service-account.json`
4. Share your Google Sheet with the service account email address

### Step 2: Project Setup
1. Clone or download this project
2. Create a `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```
3. Edit `.env` and fill in:
   - `MASTER_SHEET_ID`: Your master sheet's ID
   - `MCOC_GG_SHEET_ID`: Your staging sheet's ID
   - `GOOGLE_SERVICE_ACCOUNT_FILE`: Path to your credentials

### Step 3: Install Dependencies
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### Step 4: Verify Setup
```bash
# Test master sheet access
python3 main.py --check-sheet

# Test staging sheet access
python3 main.py --target staging --check-sheet --type champions
```

## Commands Reference

### 1. Dry Run (Preview Data)
Preview what would be scraped without writing to Google Sheets.

**Scrape all abilities:**
```bash
python3 main.py --limit 10
```

**Scrape specific ability types:**
```bash
python3 main.py --type buffs --limit 5
python3 main.py --type debuffs --limit 5
```

**Preview staging champions:**
```bash
python3 main.py --target staging --type champions --limit 5

# Search for specific champion
python3 main.py --target staging --type champions --champion "Iron Man"
```

### 2. Check Sheet Access
Verify the script can access your Google Sheets and find required headers.

**Check master sheet:**
```bash
python3 main.py --check-sheet
```

**Check staging sheet:**
```bash
python3 main.py --target staging --check-sheet --type champions
```

### 3. Write Data to Google Sheets
Scrape data and update your Google Sheets.

**Update all abilities:**
```bash
python3 main.py --write-sheet
```

**Update specific ability types:**
```bash
python3 main.py --type buffs --write-sheet
python3 main.py --type debuffs --write-sheet
```

**Update staging champions:**
```bash
python3 main.py --target staging --type champions --write-sheet
```

Features:
- Inserts new champions automatically
- Updates existing champions when data changes
- Preserves manual notes and custom fields

### 4. Sync Champions from Staging to Master

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

#### Example Behavior

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

## Common Workflows

### Workflow 1: Initial Data Collection
```bash
# 1. Preview what will be scraped
python3 main.py --type buffs --limit 10

# 2. If it looks good, write to sheets
python3 main.py --type buffs --write-sheet

# 3. Repeat for debuffs
python3 main.py --type debuffs --write-sheet
```

### Workflow 2: Update Champion Data
```bash
# 1. Scrape latest champion data to staging
python3 main.py --target staging --type champions --write-sheet

# 2. Review changes in staging sheet

# 3. Flag champions that need syncing (set Update=1 in master)

# 4. Sync to master
python3 main.py --sync-champs
```

### Workflow 3: Refresh Specific Champion
```bash
# Preview changes for one champion
python3 main.py --target staging --type champions --champion "Iron Man" --limit 1

# If good, update it
python3 main.py --target staging --type champions --champion "Iron Man" --write-sheet
```

## Data Mapping Rules

### Abilities Mapping
- Generic Buffs use `Champion = Generic`
- Champion-specific Buffs use the champion's unique name
- Debuffs always use `Champion = Generic`
- Buffs are marked: `Buff = 1`, `Debuff = 0`
- Debuffs are marked: `Buff = 0`, `Debuff = 1`
- New Debuffs are categorized as `Damaging` or `Non-Damaging`
- Blank Debuff notes are auto-filled from scraper category
- Custom fields (`Similar To`, `Offensive`, `Defensive`, `Note`) are preserved
- Rows are matched by: `Ability + Champion + Buff + Debuff`
- Existing IDs are preserved, new rows get auto-incremented IDs

### Champions Mapping
- Staging data goes to `MCOC.gg Data > Champions` worksheet
- New champions are inserted automatically
- Existing champions are matched by `MCOC.gg ID` or champion name
- Custom notes are preserved
- Master sheet is only updated via the sync command

## Sheet Requirements

### Master Sheet - Abilities Worksheet
Required headers (in any order):
```
ID | Ability | Description | Champion | Similar To | Offensive | Defensive | Buff | Debuff | Updated On | Note
```

### Master Sheet - Champs Worksheet
Required headers (in any order):
```
ID | Champion | Abilities | Immunities & Resistances | Counters Abilities | Counters Champions | Release Date | Tags | Update | Updated On
```

Optional headers: Class, Relic, Focus Attack, Focus Defense, Note

### Staging Sheet - Champions Worksheet
Required headers:
```
MCOC.gg ID | Champion | Class | Relic | Focus Attack | Focus Defense | Abilities | Immunities & Resistances | Counters Abilities | Counters Champions | Release Date | Tags | Updated On | Note
```

## Troubleshooting

**"Sheet not found" error:**
- Verify sheet IDs in `.env` are correct
- Ensure sheet is shared with service account email

**"Missing headers" error:**
- Create the worksheet tab if it doesn't exist
- Add all required headers to the first row

**Script hangs during scraping:**
- This is normal for first run - it's downloading browser engine
- Subsequent runs will be faster
- Use `--limit` to test with fewer rows

**No champions synced:**
- Check that master sheet has champions with `Update = 1`
- Verify champion names match between master and staging exactly
- Run with `--check-sheet` to confirm headers
