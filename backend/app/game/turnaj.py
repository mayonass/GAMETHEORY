"""Round-robin turnaj, volitelně opakovaný.

Vytažené z routeru simulate.py, aby se dal velký turnaj spustit v odděleném
procesu (app/vypocty.py). Počítá se jen se surovými součty; tvar odpovědi
API skládá router.

Vše se vede podle INDEXU bota v seznamu, ne podle jeho jména - dva vlastní
boti mohou mít stejné (nebo žádné) jméno a jejich skóre by se jinak omylem
sečetlo do jednoho řádku.
"""

from __future__ import annotations

from typing import Callable, Sequence

from .simulation import NastaveniZapasu, odehraj_simulovany_zapas


def odehraj_turnaj(funkce: Sequence[Callable], cfg: NastaveniZapasu, opakovani: int) -> dict:
    n = len(funkce)
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

        # Každý s každým právě jednou, stejně jako v originále.
        for i in range(n):
            for j in range(i + 1, n):
                s1, s2 = odehraj_simulovany_zapas(funkce[i], funkce[j], cfg)
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

    return {
        "body_celkem": body_celkem,
        "vyhry": vyhry,
        "remizy": remizy,
        "prohry": prohry,
        "prvni_mista": prvni_mista,
        "body_po_turnajich": body_po_turnajich,
        "zapasy": zapasy,
    }
