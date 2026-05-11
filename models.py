from dataclasses import dataclass


REQUIRED_HEADERS = [
    "ID",
    "Ability",
    "Description",
    "Champion",
    "Similar To",
    "Offensive",
    "Defensive",
    "Buff",
    "Debuff",
    "Updated On",
    "Notes",
]


@dataclass(frozen=True)
class AbilityRow:
    ability: str
    description: str
    champion: str
    similar_to: str
    offensive: str
    defensive: str
    buff: int
    debuff: int
    updated_on: str
    notes: str = ""

    @property
    def key(self) -> tuple[str, str, str, str]:
        return make_key(self.ability, self.champion, self.buff, self.debuff)

    def to_sheet_values(self, row_id: str = "", notes: str | None = None) -> list[str]:
        row_notes = self.notes if notes is None else notes
        return [
            row_id,
            self.ability,
            self.description,
            self.champion,
            self.similar_to,
            self.offensive,
            self.defensive,
            str(self.buff),
            str(self.debuff),
            self.updated_on,
            row_notes,
        ]


def make_key(ability: object, champion: object, buff: object, debuff: object) -> tuple[str, str, str, str]:
    return (
        normalize_key_part(ability),
        normalize_key_part(champion),
        normalize_bool_key(buff),
        normalize_bool_key(debuff),
    )


def normalize_key_part(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().casefold().split())


def normalize_bool_key(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().casefold()
    if text in {"1", "true", "yes", "y"}:
        return "1"
    if text in {"0", "false", "no", "n"}:
        return "0"
    return text
