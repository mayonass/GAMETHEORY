"""Endpointy pro simulaci zápasů - nic se tu neukládá do databáze,
konfigurace botů přicházejí přímo v těle requestu."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from .. import schemas
from ..config import get_settings
from ..game import registry
from ..game.evolution import CELKOVA_POPULACE, odehraj_evoluci
from ..game.simulation import NastaveniZapasu, odehraj_simulovany_zapas, odehraj_zapas_s_poctem_kol

router = APIRouter(prefix="/simulate", tags=["simulate"])

# Při neznámém počtu kol se skutečná délka pohybuje do 1,3násobku zadané
# hodnoty (viz skutecny_pocet_kol), takže s tím rozpočet počítá.
_REZERVA_NEZNAMA_KOLA = 1.3


def _zkontroluj_rozpocet(dvojic: int, settings: schemas.MatchSettings, nasobek: int, co: str) -> None:
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

    Pozor na velikost úlohy: každá generace znamená n*(n+1)/2 zápasů, takže
    12 botů na 1000 generací je 78 000 zápasů. Proto jsou v `EvolutionRequest`
    stropy na počet botů i generací.
    """
    resolved = [_resolve(spec) for spec in payload.bots]
    n = len(resolved)
    # V evoluci hraje každý s každým VČETNĚ sebe sama, proto n*(n+1)/2.
    _zkontroluj_rozpocet(n * (n + 1) // 2, payload.settings, payload.generations,
                         "the number of generations, rounds or species")

    jmena = [name for name, _ in resolved]
    funkce = [fn for _, fn in resolved]
    cfg = _settings_to_cfg(payload.settings)

    historie, vymreli = odehraj_evoluci(
        funkce,
        cfg,
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
    _zkontroluj_rozpocet(n * (n - 1) // 2, payload.settings, payload.repeats,
                         "the number of repeats, rounds or bots")

    cfg = _settings_to_cfg(payload.settings)
    opakovani = payload.repeats

    # Vše se vede podle INDEXU bota v seznamu, ne podle jeho zobrazovaného
    # jména - dva vlastní boti mohou mít stejné (nebo žádné) jméno a jejich
    # skóre by se jinak omylem sečetlo do jednoho řádku.
    body_celkem = [0.0] * n
    vyhry = [0.0] * n
    remizy = [0.0] * n
    prohry = [0.0] * n
    prvni_mista = [0.0] * n
    body_po_turnajich: list[list[int]] = [[] for _ in range(n)]
    # (i, j) -> [součet skóre bota i, součet skóre bota j]
    zapasy: dict[tuple[int, int], list[float]] = {}

    for _ in range(opakovani):
        body_turnaje = [0] * n

        # Round-robin - každý s každým právě jednou, stejně jako v originále.
        for i in range(n):
            for j in range(i + 1, n):
                s1, s2 = odehraj_simulovany_zapas(resolved[i][1], resolved[j][1], cfg)
                body_turnaje[i] += s1
                body_turnaje[j] += s2

                if s1 > s2:
                    vyhry[i] += 1
                    prohry[j] += 1
                elif s2 > s1:
                    vyhry[j] += 1
                    prohry[i] += 1
                else:
                    remizy[i] += 1
                    remizy[j] += 1

                soucet = zapasy.setdefault((i, j), [0.0, 0.0])
                soucet[0] += s1
                soucet[1] += s2

        for i in range(n):
            body_celkem[i] += body_turnaje[i]
            body_po_turnajich[i].append(body_turnaje[i])

        # Podíl prvních míst. Při dělené první příčce se kredit rozdělí, aby
        # součet přes všechny boty dal přesně 100 %.
        nejvic = max(body_turnaje)
        prvni = [i for i in range(n) if body_turnaje[i] == nejvic]
        for i in prvni:
            prvni_mista[i] += 1.0 / len(prvni)

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
