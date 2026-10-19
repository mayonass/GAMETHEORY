"""Čtení a ukládání botů.

- `GET /bots` funguje bez přihlášení (čtení, případně filtr na veřejné boty).
- `POST /bots`, `GET /bots/mine` a `PATCH /bots/{bot_id}` vyžadují přihlášení
  (JWT token) - bot se vždy ukládá pod účet přihlášeného uživatele a upravit
  ho může jen jeho vlastník.
- `config` uloženého bota musí obsahovat klíč "type" z pevně dané množiny
  povolených typů (viz `app.game.registry`) - stejná bezpečnostní zásada
  jako u simulace: žádný kód dodaný uživatelem se nikde nespouští.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..db import get_db
from ..game import registry
from ..models import Bot, User
from ..security import get_current_user

router = APIRouter(prefix="/bots", tags=["bots"])


def _validate_config(config: dict) -> None:
    """Poslední kontrola před zápisem do databáze.

    Schémata BotCreate/BotUpdate tohle ověřují už při parsování requestu
    (a vracejí 422). Tenhle catch je pojistka pro případ, že by se sem
    konfigurace dostala jinudy - do galerie se nesmí dostat bot, se kterým
    pak nejde odehrát zápas.
    """
    try:
        registry.zkontroluj_konfiguraci_bota(config)
    except (registry.UnknownBotTypeError, registry.NevalidniKonfiguraceError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _bot_to_out(bot: Bot, owner_username: str) -> schemas.BotOut:
    return schemas.BotOut(
        id=bot.id,
        name=bot.name,
        description=bot.description,
        config=bot.config,
        config_version=bot.config_version,
        is_public=bot.is_public,
        owner_username=owner_username,
        created_at=bot.created_at,
        updated_at=bot.updated_at,
    )


@router.get("", response_model=list[schemas.BotOut])
def list_bots(
    public: bool | None = Query(default=None, description="Pokud True, vrátí jen veřejné boty."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Bot, User.username).join(User, Bot.owner_id == User.id)
    if public is not None:
        stmt = stmt.where(Bot.is_public == public)
    stmt = stmt.order_by(Bot.created_at.desc()).limit(limit).offset(offset)

    rows = db.execute(stmt).all()
    return [_bot_to_out(bot, owner_username) for bot, owner_username in rows]


@router.get("/mine", response_model=list[schemas.BotOut])
def list_my_bots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Bot).where(Bot.owner_id == current_user.id).order_by(Bot.created_at.desc())
    my_bots = db.execute(stmt).scalars().all()
    return [_bot_to_out(bot, current_user.username) for bot in my_bots]


@router.post("", response_model=schemas.BotOut, status_code=status.HTTP_201_CREATED)
def create_bot(
    payload: schemas.BotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _validate_config(payload.config)

    bot = Bot(
        owner_id=current_user.id,
        name=payload.name,
        description=payload.description,
        config=payload.config,
        is_public=payload.is_public,
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return _bot_to_out(bot, current_user.username)


@router.patch("/{bot_id}", response_model=schemas.BotOut)
def update_bot(
    bot_id: uuid.UUID,
    payload: schemas.BotUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bot = db.get(Bot, bot_id)
    if bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found.")
    if bot.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This bot does not belong to you.")

    changes = payload.model_dump(exclude_unset=True)

    if "config" in changes and changes["config"] is not None:
        _validate_config(changes["config"])
        bot.config = changes["config"]
        bot.config_version += 1
    if "name" in changes and changes["name"] is not None:
        bot.name = changes["name"]
    if "description" in changes:
        bot.description = changes["description"]
    if "is_public" in changes and changes["is_public"] is not None:
        bot.is_public = changes["is_public"]

    bot.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(bot)
    return _bot_to_out(bot, current_user.username)


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bot(
    bot_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Smaže bota. Smazat lze jen vlastního.

    Příspěvky ve fóru, které se na bota odkazovaly, zůstávají - `forum_posts`
    má na `bot_id` nastavené ON DELETE SET NULL, takže se jen odpojí.
    """
    bot = db.get(Bot, bot_id)
    if bot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found.")
    if bot.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This bot does not belong to you.")

    db.delete(bot)
    db.commit()
    return None
