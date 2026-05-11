import os
from dataclasses import dataclass

from dotenv import load_dotenv


DEFAULT_BUFFS_URL = "https://marvel-contestofchampions.fandom.com/wiki/Buff"
DEFAULT_DEBUFFS_URL = "https://marvel-contestofchampions.fandom.com/wiki/Debuff"
DEFAULT_WORKSHEET_NAME = "Abilities"


@dataclass(frozen=True)
class Settings:
    google_sheet_id: str
    worksheet_name: str
    service_account_file: str
    buffs_url: str
    debuffs_url: str


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        google_sheet_id=os.getenv("GOOGLE_SHEET_ID", "").strip(),
        worksheet_name=os.getenv("GOOGLE_WORKSHEET_NAME", DEFAULT_WORKSHEET_NAME).strip(),
        service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service-account.json").strip(),
        buffs_url=os.getenv("BUFFS_URL", DEFAULT_BUFFS_URL).strip(),
        debuffs_url=os.getenv("DEBUFFS_URL", DEFAULT_DEBUFFS_URL).strip(),
    )
