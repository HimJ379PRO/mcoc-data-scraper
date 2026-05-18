import os
from dataclasses import dataclass

from dotenv import load_dotenv


DEFAULT_BUFFS_URL = "https://marvel-contestofchampions.fandom.com/wiki/Buff"
DEFAULT_DEBUFFS_URL = "https://marvel-contestofchampions.fandom.com/wiki/Debuff"
DEFAULT_MCOC_GG_BASE_URL = "https://mcoc.gg"
DEFAULT_WORKSHEET_NAME = "Abilities"
DEFAULT_MCOC_GG_CHAMPIONS_WORKSHEET_NAME = "Champions"


@dataclass(frozen=True)
class Settings:
    master_sheet_id: str
    worksheet_name: str
    service_account_file: str
    buffs_url: str
    debuffs_url: str
    mcoc_gg_sheet_id: str
    mcoc_gg_champions_worksheet_name: str
    mcoc_gg_base_url: str


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        master_sheet_id=os.getenv("MASTER_SHEET_ID", "").strip(),
        worksheet_name=os.getenv("GOOGLE_WORKSHEET_NAME", DEFAULT_WORKSHEET_NAME).strip(),
        service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials/service-account.json").strip(),
        buffs_url=os.getenv("BUFFS_URL", DEFAULT_BUFFS_URL).strip(),
        debuffs_url=os.getenv("DEBUFFS_URL", DEFAULT_DEBUFFS_URL).strip(),
        mcoc_gg_sheet_id=os.getenv("MCOC_GG_SHEET_ID", "").strip(),
        mcoc_gg_champions_worksheet_name=os.getenv(
            "MCOC_GG_CHAMPIONS_WORKSHEET_NAME",
            DEFAULT_MCOC_GG_CHAMPIONS_WORKSHEET_NAME,
        ).strip(),
        mcoc_gg_base_url=os.getenv("MCOC_GG_BASE_URL", DEFAULT_MCOC_GG_BASE_URL).strip(),
    )
