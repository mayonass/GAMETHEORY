"""Hra člověka proti botovi, kolo po kole.

Server si nic nepamatuje: klient pošle celou dosavadní historii a dostane
zpátky tah bota pro další kolo. Bot je pořád ta samá čistá funkce z
app/game/ jako v duelu a turnaji - herní logika tedy zůstává na jednom
místě a nic se nepíše podruhé v JavaScriptu.
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from .. import schemas
from ..game import registry

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

    @model_validator(mode="after")
    def _stejna_delka(self) -> "MoveRequest":
        if len(self.bot_history) != len(self.opponent_history):
            raise ValueError("bot_history and opponent_history must have the same length.")
        if self.total_rounds is not None and len(self.bot_history) >= self.total_rounds:
            raise ValueError("The match is already over.")
        return self


class MoveResponse(BaseModel):
    move: Literal["C", "D"]


@router.post("/move", response_model=MoveResponse)
def next_move(payload: MoveRequest) -> MoveResponse:
    try:
        fn = registry.resolve_bot(payload.bot.type, payload.bot.config)
    except (registry.UnknownBotTypeError, registry.NevalidniKonfiguraceError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    info = {"kolo": len(payload.bot_history), "celkem_kol": payload.total_rounds}
    tah = fn(list(payload.bot_history), list(payload.opponent_history), info)
    return MoveResponse(move=tah)
