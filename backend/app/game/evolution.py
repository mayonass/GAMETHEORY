"""
Evoluční dynamika populací botů.

Přeneseno beze změny výpočtu z desktopové aplikace "The Game Theory"
(metody `spustit_evoluci` a `evoluci_krok`). Z původního kódu je vytažená
jen matematika - všechno kreslení, časovače a stav okna zůstalo v GUI.

Model je replikátorová dynamika: v každé generaci se odehrají zápasy každý
s každým (a každý i sám se sebou), z výsledků se spočítá fitness vážená
velikostí populací a podle podílu na celkové fitness se přerozdělí pevný
počet jedinců. Populace pod 0.5 jedince vymírá.
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


def evolucni_krok(
    populace: List[float],
    funkce: Sequence[Callable],
    cfg: NastaveniZapasu,
    mutace_mira: float,
) -> List[float]:
    """Spočítá jednu generaci a vrátí novou velikost populací.

    `mutace_mira` je podíl (0-1), ne procenta. Pořadí kroků je přesně jako
    v originálním `evoluci_krok`: výplaty -> fitness -> přerozdělení ->
    mutace -> vymírání.
    """
    n = len(funkce)

    # Výplatní matice. Zápasy se hrají znovu každou generaci, takže se do
    # evoluce propisuje i náhoda z mlhy a šumu. Rozsah `range(i, n)` je
    # z originálu - zahrnuje i zápas strategie samé se sebou.
    vyplaty = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            s1, s2 = odehraj_simulovany_zapas(funkce[i], funkce[j], cfg)
            vyplaty[i][j] = s1
            vyplaty[j][i] = s2

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

    # Mutace: každá strategie odevzdá daný podíl svých jedinců a rozdělí ho
    # rovným dílem mezi všechny ostatní.
    if mutace_mira > 0:
        mutanti = [0.0] * n
        for i in range(n):
            pocet_mutantu = nova[i] * mutace_mira
            nova[i] -= pocet_mutantu
            pridel = pocet_mutantu / (n - 1) if n > 1 else 0.0
            for k in range(n):
                if k != i:
                    mutanti[k] += pridel
        for i in range(n):
            nova[i] += mutanti[i]

    # Vymírání: zbytek menší než půl jedince už není populace.
    for i in range(n):
        if nova[i] < 0.5:
            nova[i] = 0.0

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
    klesla na nulu, nebo None, pokud přežila.
    """
    n = len(funkce)
    populace = pocatecni_populace(n, rozlozeni, vahy)
    historie = [list(populace)]
    vymreli: List[Optional[int]] = [None] * n
    mutace_mira = mutace_procenta / 100.0

    for g in range(1, generaci + 1):
        populace = evolucni_krok(populace, funkce, cfg, mutace_mira)
        historie.append(list(populace))
        for i in range(n):
            if vymreli[i] is None and populace[i] == 0.0:
                vymreli[i] = g

    return historie, vymreli
