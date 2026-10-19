"""ZD strategie musí být opravdu Zero-Determinant (Press & Dyson 2012).

Pro dvojici memory-one strategií se spočítá stacionární rozdělení výsledků
kola (Markovův řetězec) a z něj dlouhodobé průměrné skóre. ZD strategie
vynutí lineární vztah mezi skóre - ať soupeř hraje jakkoli.
"""

from __future__ import annotations

import os
import random

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-tests-0123456789")

from app.game.bots import ZD_STEDRY, ZD_VYDERAC

STAVY = [("C", "C"), ("C", "D"), ("D", "C"), ("D", "D")]
BODY_X = {("C", "C"): 3, ("C", "D"): 0, ("D", "C"): 5, ("D", "D"): 1}
BODY_Y = {("C", "C"): 3, ("C", "D"): 5, ("D", "C"): 0, ("D", "D"): 1}


def dlouhodobe_skore(px: dict, qy: dict):
    """px: P(X spolupracuje | (tah X, tah Y)); qy: totéž pro Y z jeho pohledu."""
    rozdeleni = [0.25] * 4
    for _ in range(20000):
        nove = [0.0] * 4
        for k, (a, b) in enumerate(STAVY):
            x, y = px[(a, b)], qy[(b, a)]
            for m, (c, d) in enumerate(STAVY):
                nove[m] += rozdeleni[k] * (x if c == "C" else 1 - x) * (y if d == "C" else 1 - y)
        rozdeleni = nove
    sx = sum(rozdeleni[k] * BODY_X[s] for k, s in enumerate(STAVY))
    sy = sum(rozdeleni[k] * BODY_Y[s] for k, s in enumerate(STAVY))
    return sx, sy


def souperi():
    rng = random.Random(4)
    for _ in range(6):
        yield {s: rng.uniform(0.05, 0.95) for s in STAVY}


def test_vyderac_vynuti_pomer_3():
    for q in souperi():
        sx, sy = dlouhodobe_skore(ZD_VYDERAC, q)
        assert abs((sx - 1) - 3 * (sy - 1)) < 1e-6
        assert sx >= sy


def test_stedry_vynuti_pomer_2_a_nikdy_nevyhraje():
    for q in souperi():
        sx, sy = dlouhodobe_skore(ZD_STEDRY, q)
        assert abs((3 - sx) - 2 * (3 - sy)) < 1e-6
        assert sx <= sy + 1e-9
