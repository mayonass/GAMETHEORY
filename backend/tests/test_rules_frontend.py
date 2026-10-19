"""Hlídá, že se frontend a backend shodnou.

1. Katalog metrik v editoru (METRIKY ve frontend/index.html) má stejné
   klíče, rozsahy a povolené hodnoty jako app/game/rules.py.
2. Převod starého (klasického) bota na pravidla v editoru hraje úplně
   stejně jako původní custom_player - na tisících náhodných průběhů.

Potřebuje Node.js (`node` v PATH); bez něj se testy přeskočí.
"""

from __future__ import annotations

import itertools
import json
import os
import random
import shutil
import subprocess
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest

from app.game import bots, registry, rules

INDEX = Path(__file__).resolve().parents[2] / "frontend" / "index.html"
ZACATEK = "6. ZÁLOŽKA MŮJ BOT"
KONEC = "/* ---------- editor ---------- */"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js")


def _spust_js(kod: str):
    html = INDEX.read_text(encoding="utf-8")
    a = html.index(ZACATEK)
    a = html.rindex("/*", 0, a)
    b = html.index(KONEC, a)
    program = html[a:b] + "\n" + kod
    vystup = subprocess.run(["node", "-"], input=program, capture_output=True, text=True, check=True, timeout=60)
    return json.loads(vystup.stdout)


def test_katalog_metrik_sedi_s_backendem():
    js = _spust_js("console.log(JSON.stringify(METRIKY))")
    assert set(js) == set(rules.METRIKY)
    for klic, m in js.items():
        py = rules.METRIKY[klic]
        if m["typ"] == "enum":
            assert py["typ"] == "enum", klic
            assert [v for v, _ in m["volby"]] == list(py["hodnoty"]), klic
        elif m["typ"] == "rate":
            assert (py["typ"], py["min"], py["max"], py["cele"]) == ("num", 0.0, 1.0, False), klic
        else:
            assert py["typ"] == "num", klic
            assert (m["min"], m["max"]) == (py["min"], py["max"]), klic
            assert py["cele"] == (m["typ"] == "count"), klic


# Deterministické klasické konfigurace (bez náhody), aby šlo porovnat tah po tahu.
KLASICKE = [
    {**dict(zip(("prvni_tah", "zakladni_strategie", "reakce_mlha", "posledni_tah", "nikdy_neodpoustet", "tolerance_d", "zrada_pri_pomeru"), k))}
    for k in itertools.product(
        ("C", "D"),
        ("tit_for_tat", "pavlov", "opak"),
        ("zradit", "spolupracovat", "opakovat_sebe"),
        ("normal", "vzdy_d", "vzdy_c"),
        (False, True),
        (1, 3, 6),
        (100, 60, 35, 0),
    )
]


def test_prevod_klasickeho_bota_hraje_stejne():
    prevedene = _spust_js(
        "const vstup = " + json.dumps(KLASICKE) + ";"
        "console.log(JSON.stringify(vstup.map((c) => konfiguraceV2(zKlasickehoBota(c, 'x')))))"
    )
    rng = random.Random(7)
    prubehy = []
    for _ in range(60):
        n = rng.randint(1, 25)
        opp = [rng.choice("CCD?") for _ in range(n)]
        prubehy.append((n, opp))

    for v1, v2 in zip(KLASICKE, prevedene):
        stary = registry.resolve_bot("custom", v1)
        novy = registry.resolve_bot("custom", v2)
        for n, opp in prubehy:
            celkem = n + 2 if rng.random() < 0.5 else None
            inst = novy.novy_zapas()
            moje_stary, moje_novy = [], []
            for k in range(n + 1):
                info = {"kolo": k, "celkem_kol": celkem}
                a = stary(moje_stary, opp[:k], info)
                b = inst(moje_novy, opp[:k], info)
                assert a == b, (v1, opp[:k], celkem, a, b)
                moje_stary.append(a)
                moje_novy.append(b)


def test_prevod_zachova_nahodu_a_chybovost():
    """Náhodné volby se nedají porovnat tah po tahu - porovnáme četnosti."""
    v1 = {"prvni_tah": "random", "zakladni_strategie": "pravdepodobnost", "pravdepodobnost_c": 30,
          "reakce_mlha": "random", "chyba_pct": 10}
    (v2,) = _spust_js("console.log(JSON.stringify([konfiguraceV2(zKlasickehoBota(" + json.dumps(v1) + ", 'x'))]))")
    assert v2["error_rate"] == 0.1
    random.seed(3)
    for historie, ocekavani in ((["C", "C"], 0.3 * 0.9 + 0.7 * 0.1), (["C", "?"], 0.5)):
        for fn in (registry.resolve_bot("custom", v1), registry.resolve_bot("custom", v2)):
            c = sum(fn(["C", "C"], historie, {"kolo": 2, "celkem_kol": None}) == "C" for _ in range(20000))
            assert abs(c / 20000 - ocekavani) < 0.015
