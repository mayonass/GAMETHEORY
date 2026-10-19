"""Hra člověka proti botovi, kolo po kole.

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
