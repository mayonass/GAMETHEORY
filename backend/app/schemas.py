"""Pydantic schémata pro request/response těla API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

# Jediné místo, kde je popsané, co smí být v konfiguraci vlastního bota, je
# app/game/registry.py. Schémata sem tu kontrolu jen zavolají, aby se povolené
# hodnoty nepsaly na dvou místech a nemohly se rozejít.
from .game.registry import (
    NevalidniKonfiguraceError,
    UnknownBotTypeError,
    zkontroluj_custom_config,
    zkontroluj_konfiguraci_bota,
)


class BotSpec(BaseModel):
    """Konfigurace jednoho bota pro duel/turnaj.

    `type` musí být jeden z povolených typů (viz GET /bots/types) - pro
    vestavěné strategie stačí jen `type`, pro `type="custom"` je potřeba
    ještě `config` s parametry vlastního bota.
    """

    type: str = Field(..., examples=["tit_for_tat"])
    name: Optional[str] = Field(default=None, description="Volitelný zobrazovaný název.")
    config: Optional[dict] = Field(
        default=None,
        description=(
            "Povinné jen pro type='custom'. Povolené položky: prvni_tah "
            "(C|D|random), zakladni_strategie (tit_for_tat|pavlov|"
            "pravdepodobnost|opak), pravdepodobnost_c (0-100), tolerance_d "
            "(1-1000), zrada_pri_pomeru (0-100), reakce_mlha (zradit|"
            "spolupracovat|random|opakovat_sebe), posledni_tah (normal|vzdy_d|"
            "vzdy_c), nikdy_neodpoustet (bool), chyba_pct (0-100)."
        ),
    )

    @model_validator(mode="after")
    def _zkontroluj_config(self) -> "BotSpec":
        """Vlastní bot se ověří dřív, než se z konfigurace stane funkce.

        Bez toho by se špatná hodnota projevila až uprostřed zápasu -
        `prvni_tah: "Q"` by spadlo na výplatní matici, `tolerance_d` jako text
        na sčítání s číslem, a klient by dostal HTTP 500 místo vysvětlení.
        """
        if self.type == "custom":
            try:
                zkontroluj_custom_config(self.config)
            except NevalidniKonfiguraceError as exc:
                raise ValueError(str(exc)) from exc
        return self


class MatchSettings(BaseModel):
    """Nastavení jednoho zápasu / jednoho střetnutí v turnaji (odpovídá NastaveniZapasu)."""

    kola: int = Field(default=10, ge=1, le=1000, description="Základní počet kol.")
    neznama_kola: bool = Field(
        default=False, description="Pokud True, skutečný počet kol je náhodný (viz skutecny_pocet_kol)."
    )
    mlha: float = Field(default=0.0, ge=0.0, le=1.0, description="Šance, že tah zůstane dočasně skrytý mlhou.")
    delay: int = Field(
        default=1, ge=0, le=200,
        description="Kolik kol zůstane zamlžený tah skrytý. POZOR: při delay=0 nemá mlha "
                    "žádný účinek — bot se soupeřova tahu ptá nejdřív v následujícím kole, "
                    "kdy je rozdíl kol už 1, takže podmínka skrytí nikdy neplatí. "
                    "Nula je tedy 'mlha vypnutá'; smysluplné hodnoty začínají u 1.",
    )
    zkresleni: float = Field(default=0.0, ge=0.0, le=1.0, description="Šance na chybu vnímání (šum).")


class RoundRecord(BaseModel):
    """Co se stalo v jednom kole zápasu.

    Rozlišuje tři různé věci, které se v mlze války rozcházejí:
    co bot ZAHRÁL (`move`), co z toho DORAZILO soupeři (`arrived` - šum to
    mohl převrátit) a jestli to soupeř vůbec VIDĚL (`fog`). Body se počítají
    vždy podle skutečně zahraných tahů, ne podle toho, co kdo vnímal.
    """

    round: int = Field(..., description="Pořadí kola, počítáno od 1.")
    move1: Literal["C", "D"] = Field(..., description="Co bot 1 skutečně zahrál.")
    move2: Literal["C", "D"] = Field(..., description="Co bot 2 skutečně zahrál.")
    arrived1: Literal["C", "D"] = Field(..., description="Jak tah bota 1 dorazil k botovi 2.")
    arrived2: Literal["C", "D"] = Field(..., description="Jak tah bota 2 dorazil k botovi 1.")
    fog1: bool = Field(..., description="True = tah bota 1 zůstal botovi 2 skrytý mlhou.")
    fog2: bool = Field(..., description="True = tah bota 2 zůstal botovi 1 skrytý mlhou.")
    points1: int = Field(..., description="Body bota 1 za tohle kolo.")
    points2: int = Field(..., description="Body bota 2 za tohle kolo.")


class DuelRequest(BaseModel):
    bot1: BotSpec
    bot2: BotSpec
    settings: MatchSettings = Field(default_factory=MatchSettings)
    history: bool = Field(
        default=True,
        description="Vrátit i průběh zápasu kolo po kole. Vypni při dávkovém "
                    "spouštění mnoha zápasů, kde tě zajímá jen výsledné skóre.",
    )


class DuelResponse(BaseModel):
    bot1_name: str
    bot2_name: str
    score1: int
    score2: int
    rounds_played: int
    result: Literal["bot1", "bot2", "tie"]
    history: list[RoundRecord] = Field(
        default_factory=list,
        description="Průběh kolo po kole. Prázdné, pokud si o něj request neřekl.",
    )


class EvolutionRequest(BaseModel):
    """Nastavení evoluční simulace.

    Populace má vždy dohromady 1000 jedinců; mění se jen jejich rozdělení
    mezi jednotlivé strategie.
    """

    bots: list[BotSpec] = Field(..., min_length=2, max_length=12)
    settings: MatchSettings = Field(default_factory=MatchSettings)
    generations: int = Field(default=100, ge=1, le=1000, description="Kolik generací se má odehrát.")
    distribution: Literal["equal", "random", "manual"] = Field(
        default="equal", description="Počáteční rozložení populace."
    )
    weights: Optional[list[float]] = Field(
        default=None,
        description="Váhy pro distribution='manual' - jedno číslo na bota, ve stejném pořadí.",
    )
    mutation: float = Field(
        default=0.0, ge=0.0, le=10.0,
        description="Procento jedinců, kteří každou generaci přeběhnou k jiným strategiím.",
    )

    @model_validator(mode="after")
    def _zkontroluj_vahy(self) -> "EvolutionRequest":
        if self.distribution == "manual":
            if not self.weights or len(self.weights) != len(self.bots):
                raise ValueError("With distribution='manual', weights must have the same length as bots.")
            if any(w < 0 for w in self.weights):
                raise ValueError("Weights must not be negative.")
        return self


class EvolutionSpecies(BaseModel):
    name: str
    start: float = Field(..., description="Počáteční velikost populace.")
    final: float = Field(..., description="Velikost populace po poslední generaci.")
    share: float = Field(..., description="Podíl na celkové populaci na konci, v procentech.")
    extinct_at: Optional[int] = Field(
        default=None, description="Generace, ve které strategie vymřela. None = přežila."
    )


class EvolutionResponse(BaseModel):
    names: list[str]
    generations: int
    total_population: float
    history: list[list[float]] = Field(
        ...,
        description="Jeden řádek na generaci (první je počáteční stav), v něm velikost "
                    "populace každé strategie ve stejném pořadí jako `names`.",
    )
    species: list[EvolutionSpecies] = Field(..., description="Seřazeno podle konečné velikosti populace.")


class TournamentRequest(BaseModel):
    bots: list[BotSpec] = Field(..., min_length=2, max_length=16)
    settings: MatchSettings = Field(default_factory=MatchSettings)
    repeats: int = Field(
        default=1, ge=1, le=50,
        description="Kolikrát celý turnaj odehrát. Se stochastickými strategiemi "
                    "(ZD, vlastní bot s chybovostí) nebo se zapnutým šumem je jeden "
                    "turnaj málo — pořadí pak z velké části určuje náhoda.",
    )


class TournamentMatchResult(BaseModel):
    bot1: str
    bot2: str
    score1: float = Field(..., description="Průměrné skóre bota 1 přes všechna opakování.")
    score2: float = Field(..., description="Průměrné skóre bota 2 přes všechna opakování.")


class TournamentStanding(BaseModel):
    name: str
    score: float = Field(..., description="Průměrný počet bodů na jeden turnaj.")
    wins: float = Field(..., description="Průměrný počet výher na jeden turnaj.")
    ties: float
    losses: float
    score_min: float = Field(..., description="Nejhorší výsledek napříč opakováními.")
    score_max: float = Field(..., description="Nejlepší výsledek napříč opakováními.")
    first_place_share: float = Field(
        ...,
        description="V kolika procentech opakování skončil první. Při dělené první "
                    "příčce se podíl rozdělí, takže součet přes všechny boty je 100.",
    )


class TournamentResponse(BaseModel):
    repeats: int
    standings: list[TournamentStanding]
    matches: list[TournamentMatchResult]


class BotOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    config: dict
    config_version: int
    is_public: bool
    owner_username: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ==========================================
# Auth / uživatelé
# ==========================================

_EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=_EMAIL_RE, max_length=255)
    password: str = Field(..., min_length=8, max_length=72, description="Max. 72 znaků (limit bcryptu).")


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ==========================================
# Vytváření / úprava vlastních botů (vyžaduje přihlášení)
# ==========================================


def _zkontroluj_ulozenou_konfiguraci(config: Optional[dict]) -> Optional[dict]:
    """Sdílená kontrola pro ukládání i úpravu bota.

    Nevalidní bot se do databáze nesmí dostat vůbec - jinak by se dal zveřejnit
    v galerii a shodil by zápas každému, kdo by si ho zkusil.
    """
    if config is None:
        return None
    try:
        return zkontroluj_konfiguraci_bota(config)
    except (NevalidniKonfiguraceError, UnknownBotTypeError) as exc:
        raise ValueError(str(exc)) from exc


class BotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    config: dict = Field(
        ..., description="Musí obsahovat klíč 'type' z povolené množiny a u vlastního bota jeho parametry."
    )
    is_public: bool = False

    @model_validator(mode="after")
    def _zkontroluj_config(self) -> "BotCreate":
        _zkontroluj_ulozenou_konfiguraci(self.config)
        return self


class BotUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=2000)
    config: Optional[dict] = None
    is_public: Optional[bool] = None

    @model_validator(mode="after")
    def _zkontroluj_config(self) -> "BotUpdate":
        _zkontroluj_ulozenou_konfiguraci(self.config)
        return self
