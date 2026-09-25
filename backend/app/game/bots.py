"""
Čisté strategie botů pro iterované vězňovo dilema.

Přeneseno beze změny rozhodovací logiky z desktopové aplikace "The Game Theory"
(mlha_valky_gui2.py). Každá strategie má stejný podpis:

    funkce(my_hist, opp_hist, info) -> 'C' nebo 'D'

- my_hist / opp_hist: seznamy dosavadních SKUTEČNÝCH tahů ('C'/'D'), volitelně
  s '?' na místech, kde je tah kvůli mlze skrytý.
- info: dict s klíči "kolo" (index aktuálního kola od 0) a "celkem_kol"
  (celkový počet kol, nebo None, pokud je počet kol v zápase neznámý).

Jediná záměrná odchylka od originálu je u `custom_player`: místo čtení
nastavení z globální proměnné (což by na serveru s více uživateli najednou
vedlo k tomu, že by si boti přepisovali nastavení navzájem) dostává
konfiguraci jako parametr `config`. Rozhodovací logika uvnitř je identická.
"""

from __future__ import annotations

import random
from typing import Literal, TypedDict

Move = Literal["C", "D"]


class CustomBotConfig(TypedDict, total=False):
    """Tvar JSON konfigurace vlastního bota (odpovídá VLASTNI_NASTAVENI v originále)."""

    prvni_tah: str            # "C" | "D" | "random"
    zakladni_strategie: str   # "tit_for_tat" | "pavlov" | "pravdepodobnost" | "opak"
    pravdepodobnost_c: float  # 0-100
    tolerance_d: int          # >= 1
    zrada_pri_pomeru: float   # 0-100
    reakce_mlha: str          # "zradit" | "spolupracovat" | "random" | "opakovat_sebe"
    posledni_tah: str         # "normal" | "vzdy_d" | "vzdy_c"
    nikdy_neodpoustet: bool
    chyba_pct: float          # 0-100


DEFAULT_CUSTOM_CONFIG: CustomBotConfig = {
    "prvni_tah": "C",
    "zakladni_strategie": "tit_for_tat",
    "pravdepodobnost_c": 100,
    "tolerance_d": 1,
    "zrada_pri_pomeru": 100,
    "reakce_mlha": "zradit",
    "posledni_tah": "normal",
    "nikdy_neodpoustet": False,
    "chyba_pct": 0,
}


def always_cooperate(my_hist, opp_hist, info):
    return 'C'


def always_defect(my_hist, opp_hist, info):
    return 'D'


def tit_for_tat(my_hist, opp_hist, info):
    for tah in reversed(opp_hist):
        if tah != '?':
            return tah
    return 'C'


def grudger(my_hist, opp_hist, info):
    if 'D' in opp_hist:
        return 'D'
    return 'C'


def pavlov(my_hist, opp_hist, info):
    if not my_hist:
        return 'C'
    if opp_hist[-1] == '?':
        return my_hist[-1]
    my_last, opp_last = my_hist[-1], opp_hist[-1]
    if (my_last == 'C' and opp_last == 'C') or (my_last == 'D' and opp_last == 'C'):
        return my_last
    return 'C' if my_last == 'D' else 'D'


def zd_extortioner(my_hist, opp_hist, info):
    if not my_hist or opp_hist[-1] == '?':
        return 'C'
    my_last, opp_last = my_hist[-1], opp_hist[-1]
    if my_last == 'C' and opp_last == 'C':
        p = 0.85
    elif my_last == 'C' and opp_last == 'D':
        p = 0.50
    elif my_last == 'D' and opp_last == 'C':
        p = 0.27
    else:
        p = 0.0
    return 'C' if random.random() < p else 'D'


def zd_generous(my_hist, opp_hist, info):
    if not my_hist or opp_hist[-1] == '?':
        return 'C'
    my_last, opp_last = my_hist[-1], opp_hist[-1]
    if my_last == 'C' and opp_last == 'C':
        p = 1.00
    elif my_last == 'C' and opp_last == 'D':
        p = 0.18
    elif my_last == 'D' and opp_last == 'C':
        p = 0.54
    else:
        p = 0.13
    return 'C' if random.random() < p else 'D'


def custom_player(my_hist, opp_hist, info, config: CustomBotConfig = None):
    """Vlastní bot definovaný JSON konfigurací (viz CustomBotConfig).

    Rozhodovací logika je 1:1 přenesená z originálního `custom_player`
    (ten čerpal ze sdílené globální proměnné `VLASTNI_NASTAVENI`) - jediná
    změna je, že konfigurace přichází jako parametr `config`, protože na
    serveru běží současně boti mnoha různých uživatelů.
    """
    n: CustomBotConfig = {**DEFAULT_CUSTOM_CONFIG, **(config or {})}

    def aplikuj_chybu(tah):
        if n["chyba_pct"] > 0 and random.random() * 100 < n["chyba_pct"]:
            return 'D' if tah == 'C' else 'C'
        return tah

    if info["celkem_kol"] is not None and info["kolo"] == info["celkem_kol"] - 1:
        if n["posledni_tah"] == "vzdy_c":
            return aplikuj_chybu('C')
        elif n["posledni_tah"] == "vzdy_d":
            return aplikuj_chybu('D')

    if n["nikdy_neodpoustet"] and 'D' in [x for x in opp_hist if x != '?']:
        return aplikuj_chybu('D')

    if not opp_hist:
        prvni = n["prvni_tah"]
        if prvni == "random":
            return aplikuj_chybu('C' if random.random() < 0.5 else 'D')
        return aplikuj_chybu(prvni)

    viditelna_historie = [x for x in opp_hist if x != '?']

    if len(viditelna_historie) >= 5:
        opp_d_count = sum(1 for x in viditelna_historie if x == 'D')
        d_ratio = (opp_d_count / len(viditelna_historie)) * 100
        if d_ratio >= n["zrada_pri_pomeru"]:
            return aplikuj_chybu('D')

    # Tolerance k po sobě jdoucím zradám: tolerance_d = kolik zrad v řadě
    # bot odpustí, než začne oplácet (retaliace nastává až při tolerance_d + 1).
    limit = n["tolerance_d"] + 1
    if len(viditelna_historie) >= limit:
        if all(x == 'D' for x in viditelna_historie[-limit:]):
            return aplikuj_chybu('D')

    if opp_hist[-1] == '?':
        reakce = n["reakce_mlha"]
        if reakce == "zradit":
            return aplikuj_chybu('D')
        elif reakce == "spolupracovat":
            return aplikuj_chybu('C')
        elif reakce == "random":
            return aplikuj_chybu('C' if random.random() < 0.5 else 'D')
        else:
            return aplikuj_chybu(my_hist[-1] if my_hist else 'C')

    posledni = opp_hist[-1]
    strategie = n["zakladni_strategie"]
    if strategie == "tit_for_tat":
        tah = posledni
    elif strategie == "pavlov":
        ml = my_hist[-1]
        if (ml == 'C' and posledni == 'C') or (ml == 'D' and posledni == 'C'):
            tah = ml
        else:
            tah = 'C' if ml == 'D' else 'D'
    elif strategie == "opak":
        tah = 'D' if posledni == 'C' else 'C'
    elif strategie == "pravdepodobnost":
        tah = 'C' if random.random() * 100 < n["pravdepodobnost_c"] else 'D'
    else:
        tah = 'C'

    return aplikuj_chybu(tah)


# Výplatní matice (řádek = můj tah, sloupec = tah soupeře) - beze změny z originálu.
PAYOFFS = {('C', 'C'): (3, 3), ('D', 'D'): (1, 1), ('D', 'C'): (5, 0), ('C', 'D'): (0, 5)}
