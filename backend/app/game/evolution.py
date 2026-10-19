"""
Evoluční dynamika populací botů.

Model je replikátorová dynamika (jako v desktopové hře): z výsledků zápasů
se spočítá fitness vážená velikostí populací a podle podílu na celkové
fitness se přerozdělí pevný počet 1000 jedinců. Populace pod 0.5 jedince
vymírá.

Dvě změny proti desktopu (audit 2026-10-19):

1. Zápasy se odehrají JEDNOU na začátku - každá dvojice (i každá strategie
   sama se sebou) ZAPASU_NA_DVOJICI-krát - a generace pak počítají jen
   s průměrnou výplatní maticí. Dřív se v každé generaci hrál jeden nový
   zápas na dvojici, takže náhoda z šumu, mlhy a náhodných strategií
   (ZD) cukala s celou populací a evoluce o 1000 generacích stála
   1000× víc zápasů.
2. Vymírání (< 0.5 jedince) přichází PŘED mutací a součet se pak dorovná
   na 1000. Dřív šla mutace první a malý mutační přírůstek (< 0.5) vymřelý
   druh hned znovu vynuloval, takže se nikdy nemohl vrátit.
"""

from __future__ import annotations

import random
from typing import Callable, List, Optional, Sequence

from .simulation import NastaveniZapasu, odehraj_simulovany_zapas

# Celkový počet jedinců v populaci je konstantní - mění se jen jejich rozdělení
# mezi strategie. Stejná hodnota jako v desktopové hře.
CELKOVA_POPULACE = 1000.0


def pocatecni_populace(
    pocet_druhu: int,
    rozlozeni: str = "equal",
    vahy: Optional[Sequence[float]] = None,
) -> List[float]:
    """Rozdělí `CELKOVA_POPULACE` mezi jednotlivé strategie.

    - "equal"  - všem stejně (výchozí)
    - "random" - náhodné váhy 1-100, stejně jako v originále
    - "manual" - poměr podle zadaných vah; při součtu nula spadne na "equal"
    """
    rovnomerne = [CELKOVA_POPULACE / pocet_druhu] * pocet_druhu

    if rozlozeni == "random":
        v = [float(random.randint(1, 100)) for _ in range(pocet_druhu)]
    elif rozlozeni == "manual" and vahy:
        v = [float(x) for x in vahy]
        if sum(v) == 0:
            return rovnomerne
    else:
        return rovnomerne

    soucet = sum(v)
    return [(x / soucet) * CELKOVA_POPULACE for x in v]


# Kolik zápasů na dvojici se zprůměruje do výplatní matice.
ZAPASU_NA_DVOJICI = 10


def vyplatni_matice(funkce: Sequence[Callable], cfg: NastaveniZapasu, zapasu: int = ZAPASU_NA_DVOJICI) -> List[List[float]]:
    """Průměrné skóre: matice[i][j] = kolik bodů získá strategie i za zápas proti j.

    Zápas strategie sama se sebou má dvě strany téhož druhu, proto se
    zprůměrují obě (dřív se omylem uložila jen druhá).
    """
    n = len(funkce)
    matice = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            s1 = s2 = 0
            for _ in range(zapasu):
                a, b = odehraj_simulovany_zapas(funkce[i], funkce[j], cfg)
                s1 += a
                s2 += b
            if i == j:
                matice[i][i] = (s1 + s2) / (2 * zapasu)
            else:
                matice[i][j] = s1 / zapasu
                matice[j][i] = s2 / zapasu
    return matice


def evolucni_krok(populace: List[float], vyplaty: List[List[float]], mutace_mira: float) -> List[float]:
    """Spočítá jednu generaci a vrátí novou velikost populací.

    `mutace_mira` je podíl (0-1), ne procenta. Pořadí: fitness ->
    přerozdělení -> vymírání -> dorovnání na 1000 -> mutace.
    """
    n = len(populace)

    # Fitness = kolik bodů strategie nasbírá proti celé populaci, vynásobeno
    # tím, kolik jí samotné je. Početnější strategie se tedy množí rychleji.
    fitness = []
    for i in range(n):
        agregat = sum(vyplaty[i][j] * populace[j] for j in range(n))
        fitness.append(agregat * populace[i])

    celkove_fitness = sum(fitness)
    if celkove_fitness > 0:
        nova = [(f / celkove_fitness) * CELKOVA_POPULACE for f in fitness]
    else:
        nova = list(populace)

    # Vymírání: zbytek menší než půl jedince už není populace. Uvolněná
    # místa se rozdělí poměrně mezi přeživší, aby součet zůstal 1000.
    nova = [x if x >= 0.5 else 0.0 for x in nova]
    soucet = sum(nova)
    if soucet > 0:
        nova = [x * CELKOVA_POPULACE / soucet for x in nova]

    # Mutace: každá strategie odevzdá daný podíl svých jedinců a rozdělí ho
    # rovným dílem mezi všechny ostatní - i mezi vymřelé, které se tak
    # můžou vrátit (test, jestli vítěz odolá invazi).
    if mutace_mira > 0 and n > 1:
        mutanti = [0.0] * n
        for i in range(n):
            pocet_mutantu = nova[i] * mutace_mira
            nova[i] -= pocet_mutantu
            pridel = pocet_mutantu / (n - 1)
            for k in range(n):
                if k != i:
                    mutanti[k] += pridel
        nova = [nova[i] + mutanti[i] for i in range(n)]

    return nova


def odehraj_evoluci(
    funkce: Sequence[Callable],
    cfg: NastaveniZapasu,
    generaci: int,
    rozlozeni: str = "equal",
    vahy: Optional[Sequence[float]] = None,
    mutace_procenta: float = 0.0,
):
    """Odehraje celou evoluci a vrátí `(historie, vymreli_v_generaci)`.

    `historie` má `generaci + 1` řádků - první je počáteční rozložení.
    `vymreli_v_generaci[i]` je číslo generace, ve které strategie i poprvé
    klesla na nulu, nebo None, pokud přežila. Se zapnutou mutací nevymře
    nikdo - mutanti každou generaci přibývají.
    """
    n = len(funkce)
    populace = pocatecni_populace(n, rozlozeni, vahy)
    historie = [list(populace)]
    vymreli: List[Optional[int]] = [None] * n
    mutace_mira = mutace_procenta / 100.0
    vyplaty = vyplatni_matice(funkce, cfg)

    for g in range(1, generaci + 1):
        populace = evolucni_krok(populace, vyplaty, mutace_mira)
        historie.append(list(populace))
        for i in range(n):
            if vymreli[i] is None and populace[i] == 0.0:
                vymreli[i] = g

    return historie, vymreli
