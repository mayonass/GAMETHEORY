"""Endpointy pro simulaci zápasů - nic se tu neukládá do databáze,
konfigurace botů přicházejí přímo v těle requestu."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from .. import schemas
from ..config import get_settings
from ..game import registry
from ..game.evolution import CELKOVA_POPULACE, ZAPASU_NA_DVOJICI, odehraj_evoluci
from ..game.simulation import NastaveniZapasu, odehraj_zapas_s_poctem_kol
from ..game.turnaj import odehraj_turnaj
from ..vypocty import PrilisDlouho, Zaneprazdneno, spust_oddelene

router = APIRouter(prefix="/simulate", tags=["simulate"])

# Při neznámém počtu kol se skutečná délka pohybuje do 1,3násobku zadané
# hodnoty (viz skutecny_pocet_kol), takže s tím rozpočet počítá.
_REZERVA_NEZNAMA_KOLA = 1.3

# Od kolika odhadovaných kol se simulace pouští v odděleném procesu
# (app/vypocty.py). Menší se spočítají dřív, než by se proces stihl spustit.
_ODDELENE_OD_KOL = 20_000


def _zkontroluj_rozpocet(dvojic: int, settings: schemas.MatchSettings, nasobek: int, co: str) -> int:
    """Odmítne simulaci, která by procesor zaměstnala na dlouhé minuty.

    Stránku servíruje ta samá (a malá) instance, takže jeden nenasytný
    požadavek by zpomalil nebo shodil hru všem ostatním. Radši rovnou řekneme,
    co snížit, než abychom to nechali běžet.
    """
    strop = get_settings().max_simulation_rounds
    kola = settings.kola * (_REZERVA_NEZNAMA_KOLA if settings.neznama_kola else 1)
    celkem = int(dvojic * kola * nasobek)
    if celkem > strop:
        def slovy(n: int) -> str:
            """Počet kol anglicky: 1 million / 1.1 million / 850 thousand."""
            if n < 1_000_000:
                return f"{n // 1000} thousand"
            milionu = n / 1_000_000
            if abs(milionu - round(milionu)) < 0.05:
                return f"{round(milionu)} million"
            return f"{milionu:.1f} million"

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"This simulation is too large: it would play about {slovy(celkem)} rounds, "
                f"and the limit is {slovy(strop)}. Lower {co}."
            ),
        )
    return celkem


def _spocitej(fn, *args, kol: int, co: str, **kwargs):
    """Malou simulaci spočítá rovnou, velkou v odděleném procesu s limitem."""
    if kol < _ODDELENE_OD_KOL:
        return fn(*args, **kwargs)
    limit = get_settings().simulation_timeout_seconds
    try:
        return spust_oddelene(fn, *args, casovy_limit=limit, **kwargs)
    except Zaneprazdneno:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The server is busy with another big simulation. Try again in a moment.",
            headers={"Retry-After": "10"},
        ) from None
    except PrilisDlouho:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"The simulation took longer than {limit} seconds and was stopped. Lower {co}.",
        ) from None


def _settings_to_cfg(settings: schemas.MatchSettings) -> NastaveniZapasu:
    return NastaveniZapasu(
        kola=settings.kola,
        neznama_kola=settings.neznama_kola,
        mlha=settings.mlha,
        delay=settings.delay,
        zkresleni=settings.zkresleni,
    )


def _resolve(spec: schemas.BotSpec):
    """Bezpečně převede BotSpec na (zobrazovaný_název, čistá_funkce).

    `registry.resolve_bot` povoluje jen pevně danou množinu typů - u
    `type="custom"` se konfigurace jen dosadí jako parametry do
    `custom_player`, nikdy se nespouští žádný kód dodaný uživatelem.
    """
    try:
        fn = registry.resolve_bot(spec.type, spec.config)
    except (registry.UnknownBotTypeError, registry.NevalidniKonfiguraceError) as exc:
        # Schéma BotSpec tohle chytá už dřív a vrací 422; tenhle catch je
        # pojistka pro případ, že by se sem bot dostal jinou cestou
        # (třeba starý záznam v databázi uložený před zavedením kontroly).
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    name = registry.bot_display_name(spec.type, spec.config, spec.name)
    return name, fn


@router.post("/duel", response_model=schemas.DuelResponse)
def simulate_duel(payload: schemas.DuelRequest) -> schemas.DuelResponse:
    name1, f1 = _resolve(payload.bot1)
    name2, f2 = _resolve(payload.bot2)
    cfg = _settings_to_cfg(payload.settings)

    s1, s2, kola, zaznam = odehraj_zapas_s_poctem_kol(f1, f2, cfg)

    if s1 > s2:
        result = "bot1"
    elif s2 > s1:
        result = "bot2"
    else:
        result = "tie"

    return schemas.DuelResponse(
        bot1_name=name1,
        bot2_name=name2,
        score1=s1,
        score2=s2,
        rounds_played=kola,
        result=result,
        # Průběh se posílá jen na vyžádání - při stovce zápasů v dávce by to
        # byly desetitisíce zbytečných řádků JSONu.
        history=[schemas.RoundRecord(**z) for z in zaznam] if payload.history else [],
    )


@router.post("/evolution", response_model=schemas.EvolutionResponse)
def simulate_evolution(payload: schemas.EvolutionRequest) -> schemas.EvolutionResponse:
    """Odehraje evoluční simulaci - replikátorová dynamika z desktopové hry.

    Zápasy se odehrají jen jednou na začátku (n*(n+1)/2 dvojic, každá
    ZAPASU_NA_DVOJICI-krát); generace jsou pak čistá matematika, takže
    jejich počet na náročnost skoro nemá vliv.
    """
    resolved = [_resolve(spec) for spec in payload.bots]
    n = len(resolved)
    # V evoluci hraje každý s každým VČETNĚ sebe sama, proto n*(n+1)/2.
    co = "the number of rounds or species"
    kol = _zkontroluj_rozpocet(n * (n + 1) // 2, payload.settings, ZAPASU_NA_DVOJICI, co)

    jmena = [name for name, _ in resolved]
    funkce = [fn for _, fn in resolved]
    cfg = _settings_to_cfg(payload.settings)

    historie, vymreli = _spocitej(
        odehraj_evoluci,
        funkce,
        cfg,
        kol=kol,
        co=co,
        generaci=payload.generations,
        rozlozeni=payload.distribution,
        vahy=payload.weights,
        mutace_procenta=payload.mutation,
    )

    posledni = historie[-1]
    druhy = [
        schemas.EvolutionSpecies(
            name=jmena[i],
            start=round(historie[0][i], 2),
            final=round(posledni[i], 2),
            share=round(posledni[i] / CELKOVA_POPULACE * 100, 2),
            extinct_at=vymreli[i],
        )
        for i in range(len(jmena))
    ]
    druhy.sort(key=lambda d: d.final, reverse=True)

    return schemas.EvolutionResponse(
        names=jmena,
        generations=payload.generations,
        total_population=CELKOVA_POPULACE,
        # Zaokrouhlení na dvě desetinná místa - u tisíce generací by plná
        # přesnost floatů zbytečně nafoukla odpověď.
        history=[[round(x, 2) for x in radek] for radek in historie],
        species=druhy,
    )


@router.post("/tournament", response_model=schemas.TournamentResponse)
def simulate_tournament(payload: schemas.TournamentRequest) -> schemas.TournamentResponse:
    """Round-robin turnaj, volitelně opakovaný.

    Jeden turnaj o výsledku moc nevypovídá: ZD strategie se rozhodují náhodně
    a se zapnutým šumem nebo mlhou je náhodný i zbytek. Proto se dá turnaj
    odehrát vícekrát a vrací se průměr na turnaj, rozpětí a podíl prvních
    míst - z toho je teprve poznat, co je skutečný rozdíl a co jen šum.
    """
    resolved = [_resolve(spec) for spec in payload.bots]
    n = len(resolved)
    co = "the number of repeats, rounds or bots"
    kol = _zkontroluj_rozpocet(n * (n - 1) // 2, payload.settings, payload.repeats, co)

    cfg = _settings_to_cfg(payload.settings)
    opakovani = payload.repeats
    t = _spocitej(odehraj_turnaj, [fn for _, fn in resolved], cfg, opakovani, kol=kol, co=co)
    body_celkem, vyhry, remizy, prohry = t["body_celkem"], t["vyhry"], t["remizy"], t["prohry"]
    prvni_mista, body_po_turnajich, zapasy = t["prvni_mista"], t["body_po_turnajich"], t["zapasy"]

    standings = [
        schemas.TournamentStanding(
            name=resolved[i][0],
            score=round(body_celkem[i] / opakovani, 1),
            wins=round(vyhry[i] / opakovani, 2),
            ties=round(remizy[i] / opakovani, 2),
            losses=round(prohry[i] / opakovani, 2),
            score_min=min(body_po_turnajich[i]),
            score_max=max(body_po_turnajich[i]),
            first_place_share=round(prvni_mista[i] / opakovani * 100, 1),
        )
        for i in range(n)
    ]
    standings.sort(key=lambda s: s.score, reverse=True)

    matches = [
        schemas.TournamentMatchResult(
            bot1=resolved[i][0],
            bot2=resolved[j][0],
            score1=round(soucty[0] / opakovani, 1),
            score2=round(soucty[1] / opakovani, 1),
        )
        for (i, j), soucty in zapasy.items()
    ]

    return schemas.TournamentResponse(repeats=opakovani, standings=standings, matches=matches)
