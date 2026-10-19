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


def posledni_videne_kolo(my_hist, opp_hist):
    """(můj tah, soupeřův tah) z posledního kola, kde byl soupeřův tah vidět.

    Pavlov a ZD strategie se rozhodují podle výsledku minulého kola. V mlze
    ale poslední tah soupeře často vidět není - dřív to znamenalo, že ZD
    strategie rovnou spolupracovaly (při 100% mlze z nich byl Always
    Cooperate) a Pavlov jen opakoval svůj tah. Teď se, stejně jako
    Tit-for-Tat, řídí posledním kolem, o kterém něco vědí. None = zatím
    neviděly nic.
    """
    for i in range(len(opp_hist) - 1, -1, -1):
        if opp_hist[i] != '?':
            return my_hist[i], opp_hist[i]
    return None


def pavlov(my_hist, opp_hist, info):
    if not my_hist:
        return 'C'
    kolo = posledni_videne_kolo(my_hist, opp_hist)
    if kolo is None:
        return my_hist[-1]
    muj, jeho = kolo
    # Win-stay, lose-shift: soupeř spolupracoval -> nech svůj tah, jinak ho otoč.
    if jeho == 'C':
        return muj
    return 'C' if muj == 'D' else 'D'


# Zero-Determinant strategie (Press & Dyson 2012). Pravděpodobnost spolupráce
# podle výsledku minulého kola (můj tah, soupeřův tah): CC, CD, DC, DD.
# Pro výplaty R=3, S=0, T=5, P=1 je ZD strategie tvaru
#   p - (1, 1, 0, 0) = phi * [(S_X - base) - chi * (S_Y - base)]
# (ověřuje backend/tests/test_zd.py).

# Vyděrač: chi = 3, phi = 1/26, základ P = 1. Dlouhodobě vynutí
# (moje skóre - 1) = 3 * (soupeřovo skóre - 1), takže nikdy neskončí pod
# soupeřem. Přesně vektor z článku Press & Dyson; dřív zaokrouhlený na
# (0.85, 0.50, 0.27, 0), čímž poměr vycházel 2,96 místo 3.
ZD_VYDERAC = {("C", "C"): 11 / 13, ("C", "D"): 1 / 2, ("D", "C"): 7 / 26, ("D", "D"): 0.0}

# Štědrý: ZDGTFT-2 (Stewart & Plotkin 2012), chi = 2, phi = 1/8, základ R = 3.
# Vynutí (3 - moje skóre) = 2 * (3 - soupeřovo skóre), takže nikdy neskončí
# NAD soupeřem. Původní vektor (1, 0.18, 0.54, 0.13) ZD strategií nebyl
# a proti některým soupeřům Štědrý vyhrával.
ZD_STEDRY = {("C", "C"): 1.0, ("C", "D"): 1 / 8, ("D", "C"): 1.0, ("D", "D"): 1 / 4}


def zd_extortioner(my_hist, opp_hist, info):
    kolo = posledni_videne_kolo(my_hist, opp_hist)
    if kolo is None:
        return 'C'
    return 'C' if random.random() < ZD_VYDERAC[kolo] else 'D'


def zd_generous(my_hist, opp_hist, info):
    kolo = posledni_videne_kolo(my_hist, opp_hist)
    if kolo is None:
        return 'C'
    return 'C' if random.random() < ZD_STEDRY[kolo] else 'D'


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

    # 'D' v historii = 'D' ve viditelné historii ('?' se jen vynechává).
    if n["nikdy_neodpoustet"] and 'D' in opp_hist:
        return aplikuj_chybu('D')

    if not opp_hist:
        prvni = n["prvni_tah"]
        if prvni == "random":
            return aplikuj_chybu('C' if random.random() < 0.5 else 'D')
        return aplikuj_chybu(prvni)

    # Viditelná historie = opp_hist bez '?'. Dřív se v každém kole skládala
    # znovu (zápas o K kolech pak stál K^2 kroků); počty se ale dají vzít
    # rovnou z opp_hist a sérii stačí dojít od konce. Rozhoduje to stejně.
    pocet_viditelnych = len(opp_hist) - opp_hist.count('?')

    if pocet_viditelnych >= 5:
        opp_d_count = opp_hist.count('D')
        d_ratio = (opp_d_count / pocet_viditelnych) * 100
        if d_ratio >= n["zrada_pri_pomeru"]:
            return aplikuj_chybu('D')

    # Tolerance k po sobě jdoucím zradám: tolerance_d = kolik zrad v řadě
    # bot odpustí, než začne oplácet (retaliace nastává až při tolerance_d + 1).
    # Počítá se přes viditelné tahy, mlha se přeskakuje.
    limit = n["tolerance_d"] + 1
    serie = 0
    for x in reversed(opp_hist):
        if x == '?':
            continue
        if x != 'D':
            break
        serie += 1
        if serie >= limit:
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
