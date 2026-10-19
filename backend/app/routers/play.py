"""Hra, kde hraje člověk - kolo po kole.

- POST /play/move  - jen tah bota (používá ho krok 1 příběhu).
- POST /play/round - celé kolo režimu "Play yourself": člověk proti botovi,
  nebo dva lidé u jednoho zařízení; server spočítá šum, mlhu a body.

Server si nic nepamatuje: klient pošle celou dosavadní historii a dostane
zpátky tah bota pro další kolo. Bot je pořád ta samá čistá funkce z
app/game/ jako v duelu a turnaji - herní logika tedy zůstává na jednom
místě a nic se nepíše podruhé v JavaScriptu.

Pravidlový bot (schema_version 2) má paměť (bot_mode, trust_score, timer).
Protože server nic nedrží, posílá klient paměť z minulé odpovědi zpátky
v `bot_state`. V prvním kole ji vynechá a bot začne ze svého initial_state.
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from .. import schemas
from ..game import registry, rules
from ..game.bots import PAYOFFS
from ..game.simulation import (
    NastaveniZapasu,
    skutecny_pocet_kol,
    spocitej_viditelnou_historii,
    vyhodnot_kolo,
)

router = APIRouter(prefix="/play", tags=["play"])

# Strop délky hry proti člověku. Nikdo nebude klikat tisíckrát, a server
# nemusí přijímat libovolně dlouhé seznamy.
_MAX_KOL = 500


class MoveRequest(BaseModel):
    bot: schemas.BotSpec
    bot_history: list[Literal["C", "D"]] = Field(
        default_factory=list, max_length=_MAX_KOL,
        description="Co bot v dosavadních kolech skutečně zahrál.",
    )
    opponent_history: list[Literal["C", "D", "?"]] = Field(
        default_factory=list, max_length=_MAX_KOL,
        description="Co bot viděl z tahů hráče; '?' = tah skrytý mlhou.",
    )
    total_rounds: Optional[int] = Field(
        default=None, ge=1, le=_MAX_KOL,
        description="Celkový počet kol, pokud ho bot smí znát. None = neznámý.",
    )
    noise: float = Field(default=0.0, ge=0.0, le=1.0, description="Šum v zápase (pro env_noise).")
    fog: float = Field(default=0.0, ge=0.0, le=1.0, description="Mlha v zápase (pro env_fog).")
    bot_state: Optional[dict] = Field(
        default=None,
        description="Paměť pravidlového bota z minulé odpovědi. None = začni z initial_state.",
    )

    @model_validator(mode="after")
    def _stejna_delka(self) -> "MoveRequest":
        if len(self.bot_history) != len(self.opponent_history):
            raise ValueError("bot_history and opponent_history must have the same length.")
        if self.total_rounds is not None and len(self.bot_history) >= self.total_rounds:
            raise ValueError("The match is already over.")
        return self


class MoveResponse(BaseModel):
    move: Literal["C", "D"]
    bot_state: Optional[dict] = Field(
        default=None, description="Nová paměť pravidlového bota - pošli ji v dalším tahu. None u ostatních botů."
    )


@router.post("/move", response_model=MoveResponse)
def next_move(payload: MoveRequest) -> MoveResponse:
    try:
        fn = registry.resolve_bot(payload.bot.type, payload.bot.config)
        stav = rules.zkontroluj_stav(payload.bot_state) if payload.bot_state is not None else None
    except (registry.UnknownBotTypeError, registry.NevalidniKonfiguraceError, rules.ChybaPravidel) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    info = {
        "kolo": len(payload.bot_history),
        "celkem_kol": payload.total_rounds,
        "sum": payload.noise,
        "mlha": payload.fog,
    }

    if isinstance(fn, rules.RuleBot):
        instance = fn.novy_zapas(stav)
        tah = instance(list(payload.bot_history), list(payload.opponent_history), info)
        return MoveResponse(move=tah, bot_state=dict(instance.stav))

    tah = fn(list(payload.bot_history), list(payload.opponent_history), info)
    return MoveResponse(move=tah)


# ---------------------------------------------------------------------------
# Režim "Play yourself": člověk proti botovi nebo dva lidé u jednoho zařízení
# ---------------------------------------------------------------------------
#
# Server zase nic nedrží. Klient pošle dosavadní průběh (přesně ty záznamy,
# které mu server v minulých kolech vrátil) a tahy pro tohle kolo. Šum, mlhu,
# body i to, co kdo z tahů soupeře vidí, počítá server stejnými funkcemi jako
# duel - pravidla hry se tak nepíšou podruhé v JavaScriptu.

# Delší zápas nikdo neodklikává; při neznámém počtu kol může skutečná délka
# vyjít až o 30 % víc než zadaná.
_MAX_KOL_HRA = 200
_MAX_SKUTECNYCH_KOL = int(_MAX_KOL_HRA * 1.3) + 1


class RoundRequest(BaseModel):
    settings: schemas.MatchSettings = Field(default_factory=schemas.MatchSettings)
    rounds_total: Optional[int] = Field(
        default=None, ge=1, le=_MAX_SKUTECNYCH_KOL,
        description="Skutečná délka zápasu z odpovědi na první kolo. V prvním kole vynech - server ji určí.",
    )
    history: list[schemas.RoundRecord] = Field(default_factory=list, max_length=_MAX_SKUTECNYCH_KOL)
    move1: Literal["C", "D"] = Field(..., description="Tah hráče 1 (vždy člověk).")
    move2: Optional[Literal["C", "D"]] = Field(default=None, description="Tah hráče 2, když je to člověk.")
    bot: Optional[schemas.BotSpec] = Field(default=None, description="Soupeř-bot (místo move2).")
    bot_state: Optional[dict] = None

    @model_validator(mode="after")
    def _kontrola(self) -> "RoundRequest":
        if (self.move2 is None) == (self.bot is None):
            raise ValueError("Send either move2 (a second player) or bot (a bot opponent), not both.")
        if self.settings.kola > _MAX_KOL_HRA:
            raise ValueError(f"A match you play yourself can have at most {_MAX_KOL_HRA} rounds.")
        if self.history and self.rounds_total is None:
            raise ValueError("rounds_total is required after the first round.")
        if self.rounds_total is not None and len(self.history) >= self.rounds_total:
            raise ValueError("The match is already over.")
        for i, r in enumerate(self.history):
            if r.round != i + 1 or (r.points1, r.points2) != PAYOFFS[(r.move1, r.move2)]:
                raise ValueError(f"history[{i}] is not a valid round record.")
        return self


class RoundResponse(BaseModel):
    round: schemas.RoundRecord = Field(..., description="Co se v tomhle kole skutečně stalo.")
    rounds_total: int = Field(..., description="Skutečná délka zápasu - posílej ji v dalších kolech.")
    over: bool
    score1: int
    score2: int
    seen_by_1: list[Literal["C", "D", "?"]] = Field(
        ..., description="Tahy hráče 2 tak, jak je teď vidí hráč 1 (šum už v nich je, '?' = mlha)."
    )
    seen_by_2: list[Literal["C", "D", "?"]] = Field(..., description="Tahy hráče 1 tak, jak je teď vidí hráč 2.")
    bot_state: Optional[dict] = None


@router.post("/round", response_model=RoundResponse)
def play_round(payload: RoundRequest) -> RoundResponse:
    s = payload.settings
    cfg = NastaveniZapasu(kola=s.kola, neznama_kola=s.neznama_kola, mlha=s.mlha, delay=s.delay, zkresleni=s.zkresleni)
    celkem = payload.rounds_total or skutecny_pocet_kol(cfg)
    h = payload.history
    kolo = len(h)

    tah2 = payload.move2
    novy_stav = None
    if payload.bot is not None:
        try:
            fn = registry.resolve_bot(payload.bot.type, payload.bot.config)
            stav = rules.zkontroluj_stav(payload.bot_state) if payload.bot_state is not None else None
        except (registry.UnknownBotTypeError, registry.NevalidniKonfiguraceError, rules.ChybaPravidel) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        # Bot (hráč 2) se rozhoduje jen z minulých kol - tah člověka v tomhle kole nevidí.
        videl = spocitej_viditelnou_historii([r.arrived1 for r in h], [r.fog1 for r in h], kolo, s.delay)
        info = {"kolo": kolo, "celkem_kol": None if s.neznama_kola else celkem, "sum": s.zkresleni, "mlha": s.mlha}
        if isinstance(fn, rules.RuleBot):
            instance = fn.novy_zapas(stav)
            tah2 = instance([r.move2 for r in h], videl, info)
            novy_stav = dict(instance.stav)
        else:
            tah2 = fn([r.move2 for r in h], videl, info)

    p1, p2, b1, b2, mlha1, mlha2 = vyhodnot_kolo(payload.move1, tah2, s.zkresleni, s.mlha)
    zaznam = schemas.RoundRecord(
        round=kolo + 1, move1=payload.move1, move2=tah2, arrived1=p1, arrived2=p2,
        fog1=mlha1, fog2=mlha2, points1=b1, points2=b2,
    )
    vse = [*h, zaznam]
    konec = len(vse) >= celkem
    # Na konci už se nic neskrývá; jinak to, co bude kdo vidět v dalším kole.
    pristi = len(vse) + (s.delay + 1 if konec else 0)
    return RoundResponse(
        round=zaznam,
        rounds_total=celkem,
        over=konec,
        score1=sum(r.points1 for r in vse),
        score2=sum(r.points2 for r in vse),
        seen_by_1=spocitej_viditelnou_historii([r.arrived2 for r in vse], [r.fog2 for r in vse], pristi, s.delay),
        seen_by_2=spocitej_viditelnou_historii([r.arrived1 for r in vse], [r.fog1 for r in vse], pristi, s.delay),
        bot_state=novy_stav,
    )
