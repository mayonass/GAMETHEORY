"""
Čistá herní logika (žádná závislost na Tkinteru).

Přeneseno beze změny z desktopové aplikace "The Game Theory"
(mlha_valky_gui2.py, sekce "ČISTÁ HERNÍ LOGIKA"). Tyto funkce se dají testovat
samostatně bez GUI a používá je jak interaktivní zápas, tak turnaj a evoluce -
pravidla hry jsou tedy definovaná přesně na jednom místě.

Jediné, co k původní logice přibylo, je ZÁZNAM průběhu zápasu: `_odehraj_kola`
si vedle skóre odkládá i to, co se v každém kole stalo. Záznam se jen zapisuje,
nikde se podle něj nerozhoduje a nevolá se kvůli němu `random`, takže výsledky
zápasů jsou identické jako předtím.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, List, Tuple

from .bots import PAYOFFS

BotFn = Callable[[List[str], List[str], dict], str]


@dataclass
class NastaveniZapasu:
    """Sdílené nastavení jednoho zápasu / jednoho střetnutí v simulaci."""
    kola: int
    neznama_kola: bool
    mlha: float
    delay: int
    zkresleni: float


def skutecny_pocet_kol(cfg: NastaveniZapasu) -> int:
    """Reálný počet kol zápasu. Při neznámém počtu kol je náhodný, ale vždy >= 1."""
    if not cfg.neznama_kola:
        return max(1, cfg.kola)
    rozptyl = max(1, int(cfg.kola * 0.3))
    return max(1, random.randint(cfg.kola - rozptyl, cfg.kola + rozptyl))


def spocitej_viditelnou_historii(vnimana_historie, fog, aktualni_kolo, delay):
    """Z historie (může už být zkreslená šumem) odstraní tahy skryté mlhou."""
    vysledek = []
    for i, tah in enumerate(vnimana_historie):
        if fog[i] and (aktualni_kolo - i) <= delay:
            vysledek.append('?')
        else:
            vysledek.append(tah)
    return vysledek


def vyhodnot_kolo(tah1, tah2, zkresleni, mlha):
    """Spočítá výsledek jednoho kola: co soupeři VNÍMAJÍ (šum), body a novou mlhu."""
    p1 = ('D' if tah1 == 'C' else 'C') if (random.random() < zkresleni) else tah1
    p2 = ('D' if tah2 == 'C' else 'C') if (random.random() < zkresleni) else tah2
    b1, b2 = PAYOFFS[(tah1, tah2)]
    nova_mlha1 = random.random() < mlha
    nova_mlha2 = random.random() < mlha
    return p1, p2, b1, b2, nova_mlha1, nova_mlha2


def _odehraj_kola(f1: BotFn, f2: BotFn, cfg: NastaveniZapasu, kola: int):
    """Interní pomocná funkce: odehraje přesně `kola` kol.

    Vrací `(skore1, skore2, zaznam)`, kde `zaznam` je seznam slovníků - jeden
    na kolo. Klíče odpovídají modelu `RoundRecord` v app/schemas.py:

        round     pořadí kola (od 1)
        move1/2   co bot SKUTEČNĚ zahrál
        arrived1/2 co z toho dorazilo soupeři (může být převrácené šumem)
        fog1/2    zda ten tah zůstal soupeři skrytý mlhou
        points1/2 body za kolo

    Sdílená implementace pro `odehraj_simulovany_zapas` (turnaj, kde záznam
    nikoho nezajímá) i pro `odehraj_zapas_s_poctem_kol` (duel, kde se záznam
    posílá do frontendu jako průběh zápasu).
    """
    info = {"celkem_kol": None if cfg.neznama_kola else kola}
    true1, true2, perc1, perc2, fog1, fog2 = [], [], [], [], [], []
    s1, s2 = 0, 0
    zaznam = []

    for kolo in range(kola):
        info["kolo"] = kolo
        v1 = spocitej_viditelnou_historii(perc1, fog1, kolo, cfg.delay)
        v2 = spocitej_viditelnou_historii(perc2, fog2, kolo, cfg.delay)

        tah1 = f1(true1, v2, info)
        tah2 = f2(true2, v1, info)

        p1, p2, b1, b2, f1_bool, f2_bool = vyhodnot_kolo(tah1, tah2, cfg.zkresleni, cfg.mlha)
        s1 += b1
        s2 += b2

        zaznam.append({
            "round": kolo + 1,
            "move1": tah1,
            "move2": tah2,
            "arrived1": p1,
            "arrived2": p2,
            "fog1": f1_bool,
            "fog2": f2_bool,
            "points1": b1,
            "points2": b2,
        })

        true1.append(tah1)
        true2.append(tah2)
        perc1.append(p1)
        perc2.append(p2)
        fog1.append(f1_bool)
        fog2.append(f2_bool)

    return s1, s2, zaznam


def odehraj_simulovany_zapas(f1: BotFn, f2: BotFn, cfg: NastaveniZapasu) -> Tuple[int, int]:
    """Odehraje jeden neinteraktivní zápas mezi dvěma boty a vrátí (skóre1, skóre2).

    Identické chování jako originální funkce z desktopové aplikace.
    """
    kola = skutecny_pocet_kol(cfg)
    s1, s2, _ = _odehraj_kola(f1, f2, cfg, kola)
    return s1, s2


def odehraj_zapas_s_poctem_kol(f1: BotFn, f2: BotFn, cfg: NastaveniZapasu):
    """Stejné jako `odehraj_simulovany_zapas`, ale navíc vrátí skutečný počet
    odehraných kol a záznam průběhu - obojí pro API odpověď u duelu.

    Vrací `(skore1, skore2, kola, zaznam)`.
    """
    kola = skutecny_pocet_kol(cfg)
    s1, s2, zaznam = _odehraj_kola(f1, f2, cfg, kola)
    return s1, s2, kola, zaznam
