from dataclasses import dataclass


ABILITIES_HEADERS = [
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
    "Note",
]

MCOC_GG_CHAMPIONS_HEADERS = [
    "MCOC.gg ID",
    "Champion",
    "Class",
    "Relic",
    "Focus Attack",
    "Focus Defense",
    "Abilities",
    "Immunities & Resistances",
    "Counters Abilities",
    "Counters Champions",
    "Release Date",
    "Tags",
    "Updated On",
    "Note",
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
    note: str = ""

    @property
    def key(self) -> tuple[str, str, str, str]:
        return make_key(self.ability, self.champion, self.buff, self.debuff)

    def to_sheet_values(self, row_id: str = "", note: str | None = None) -> list[str]:
        row_note = self.note if note is None else note
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
            row_note,
        ]


@dataclass(frozen=True)
class McocGgChampionRow:
    mcoc_gg_id: str
    champion: str
    champion_class: str
    relic: str
    focus_attack: str
    focus_defense: str
    abilities: str
    immunities_resistances: str
    counters_abilities: str
    counters_champions: str
    release_date: str
    tags: str
    updated_on: str
    note: str = ""

    @property
    def id_key(self) -> str:
        return normalize_key_part(self.mcoc_gg_id)

    @property
    def name_key(self) -> str:
        return normalize_key_part(self.champion)

    def to_sheet_values(self, note: str | None = None) -> list[str]:
        row_note = self.note if note is None else note
        return [
            self.mcoc_gg_id,
            self.champion,
            self.champion_class,
            self.relic,
            self.focus_attack,
            self.focus_defense,
            self.abilities,
            self.immunities_resistances,
            self.counters_abilities,
            self.counters_champions,
            self.release_date,
            self.tags,
            self.updated_on,
            row_note,
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
