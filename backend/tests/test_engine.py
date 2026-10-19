"""Zrychlené herní jádro musí hrát přesně stejně jako původní.

`_puvodni_zapas` je doslovná kopie smyčky před zrychlením (viditelná
historie se v každém kole počítala znovu přes spocitej_viditelnou_historii).
Se stejným seedem musí nová i stará verze dát identický průběh.
"""

from __future__ import annotations

import os
import random
import time

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-tests-0123456789")

import pytest

from app.game import registry
from app.game.simulation import (
    NastaveniZapasu,
    _odehraj_kola,
    odehraj_simulovany_zapas,
    spocitej_viditelnou_historii,
    vyhodnot_kolo,
)


def _puvodni_zapas(f1, f2, cfg, kola):
    if hasattr(f1, "novy_zapas"):
        f1 = f1.novy_zapas()
    if hasattr(f2, "novy_zapas"):
        f2 = f2.novy_zapas()
    info = {"celkem_kol": None if cfg.neznama_kola else kola, "sum": cfg.zkresleni, "mlha": cfg.mlha}
    true1, true2, perc1, perc2, fog1, fog2 = [], [], [], [], [], []
    s1, s2, zaznam = 0, 0, []
    for kolo in range(kola):
        info["kolo"] = kolo
        v1 = spocitej_viditelnou_historii(perc1, fog1, kolo, cfg.delay)
        v2 = spocitej_viditelnou_historii(perc2, fog2, kolo, cfg.delay)
        tah1 = f1(true1, v2, info)
        tah2 = f2(true2, v1, info)
        p1, p2, b1, b2, m1, m2 = vyhodnot_kolo(tah1, tah2, cfg.zkresleni, cfg.mlha)
        s1 += b1
        s2 += b2
        zaznam.append({"round": kolo + 1, "move1": tah1, "move2": tah2, "arrived1": p1, "arrived2": p2,
                       "fog1": m1, "fog2": m2, "points1": b1, "points2": b2})
        true1.append(tah1); true2.append(tah2)
        perc1.append(p1); perc2.append(p2)
        fog1.append(m1); fog2.append(m2)
    return s1, s2, zaznam


PRAVIDLOVY = {
    "schema_version": 2,
    "initial_state": {"bot_mode": "COOP"},
    "rules": [
        {"conditions": [{"metric": "timer", "op": ">", "value": 0}], "action": {"type": "PROBABILITY", "cooperate_prob": 0}},
        {"conditions": [{"metric": "opp_last_move", "op": "==", "value": "?"}], "action": {"type": "REPEAT_MY_LAST"}},
        {"conditions": [{"metric": "opp_defections_last_5", "op": ">=", "value": 2}, {"metric": "score_diff", "op": "<", "value": 0}],
         "action": {"type": "PROBABILITY", "cooperate_prob": 0.15, "set_mode": "RETALIATING", "add_trust": -2, "set_timer": 3}},
        {"conditions": [{"metric": "consecutive_opp_defections", "op": ">=", "value": 2}], "action": {"type": "MIRROR_OPP_LAST_VISIBLE"}},
    ],
    "fallback_action": {"type": "PROBABILITY", "cooperate_prob": 0.9},
    "error_rate": 0.02,
}

BOTI = [registry.resolve_bot(t) for t in registry.BUILTIN_BOTS] + [
    registry.resolve_bot("custom", {"prvni_tah": "random", "zakladni_strategie": "pavlov", "reakce_mlha": "random", "chyba_pct": 5}),
    registry.resolve_bot("custom", PRAVIDLOVY),
]


@pytest.mark.parametrize("delay", [0, 1, 2, 5])
@pytest.mark.parametrize("mlha, sum_", [(0.0, 0.0), (0.3, 0.1), (1.0, 0.0), (0.7, 0.5)])
def test_stejny_prubeh_jako_puvodni(delay, mlha, sum_):
    cfg = NastaveniZapasu(kola=40, neznama_kola=False, mlha=mlha, delay=delay, zkresleni=sum_)
    for i, f1 in enumerate(BOTI):
        for f2 in BOTI[i:]:
            random.seed(1000 * delay + i)
            stary = _puvodni_zapas(f1, f2, cfg, 40)
            random.seed(1000 * delay + i)
            novy = _odehraj_kola(f1, f2, cfg, 40)
            assert novy == stary


def test_bez_zaznamu_stejne_skore():
    cfg = NastaveniZapasu(kola=60, neznama_kola=True, mlha=0.4, delay=2, zkresleni=0.1)
    for f1 in BOTI:
        random.seed(5)
        a = _odehraj_kola(f1, BOTI[2], cfg, 60)[:2]
        random.seed(5)
        b = _odehraj_kola(f1, BOTI[2], cfg, 60, zaznamenat=False)[:2]
        assert a == b


def test_dlouhy_zapas_neni_kvadraticky():
    """Kolo v zápase o 1000 kolech nesmí být o moc dražší než v zápase o 50."""
    tft, pav = registry.resolve_bot("tit_for_tat"), registry.resolve_bot("pavlov")

    def za_kolo(kola, zapasu):
        cfg = NastaveniZapasu(kola=kola, neznama_kola=False, mlha=0.1, delay=1, zkresleni=0.05)
        t = time.perf_counter()
        for _ in range(zapasu):
            odehraj_simulovany_zapas(tft, pav, cfg)
        return (time.perf_counter() - t) / (kola * zapasu)

    kratky, dlouhy = za_kolo(50, 400), za_kolo(1000, 20)
    assert dlouhy < 2.5 * kratky, (kratky, dlouhy)


# --------------------------------------------------------------------------
# custom_player: zrychlená verze rozhoduje stejně jako původní
# --------------------------------------------------------------------------

from app.game import bots as _bots  # noqa: E402


def _puvodni_custom_player(my_hist, opp_hist, info, config=None):
    """Doslovná kopie custom_player před zrychlením."""
    n = {**_bots.DEFAULT_CUSTOM_CONFIG, **(config or {})}

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


def test_custom_player_rozhoduje_stejne():
    rng = random.Random(11)
    for _ in range(400):
        config = {
            "prvni_tah": rng.choice(["C", "D", "random"]),
            "zakladni_strategie": rng.choice(["tit_for_tat", "pavlov", "pravdepodobnost", "opak"]),
            "pravdepodobnost_c": rng.choice([0, 30, 100]),
            "tolerance_d": rng.choice([1, 2, 4, 7]),
            "zrada_pri_pomeru": rng.choice([0, 35, 60, 100]),
            "reakce_mlha": rng.choice(["zradit", "spolupracovat", "random", "opakovat_sebe"]),
            "posledni_tah": rng.choice(["normal", "vzdy_d", "vzdy_c"]),
            "nikdy_neodpoustet": rng.random() < 0.3,
            "chyba_pct": rng.choice([0, 0, 10]),
        }
        n = rng.randint(0, 30)
        opp = [rng.choice("CDD??") for _ in range(n)]
        my = [rng.choice("CD") for _ in range(n)]
        info = {"kolo": n, "celkem_kol": rng.choice([None, n + 1, n + 5])}
        seed = rng.random()
        random.seed(seed)
        a = _puvodni_custom_player(my, opp, info, config)
        random.seed(seed)
        b = _bots.custom_player(my, opp, info, config)
        assert a == b, (config, opp, info)


def test_mezisoucty_pravidloveho_bota_sedi():
    """Průběžné počty dvojic musí dát stejné metriky jako výpočet od nuly."""
    from app.game import rules
    rng = random.Random(3)
    for _ in range(200):
        mezi = {}
        my, opp = [], []
        skryte = []
        for k in range(rng.randint(1, 60)):
            my.append(rng.choice("CD"))
            opp.append("?" if rng.random() < 0.4 else rng.choice("CD"))
            skryte.append(k)
            # mlha se náhodně rozplývá (jen '?' se mění na C/D)
            for i in list(skryte):
                if opp[i] == "?" and rng.random() < 0.3:
                    opp[i] = rng.choice("CD")
            info = {"kolo": k + 1, "celkem_kol": None}
            a = rules.spocitej_metriky(my, opp, info, dict(rules.VYCHOZI_STAV))
            b = rules.spocitej_metriky(my, opp, info, dict(rules.VYCHOZI_STAV), None, mezi)
            assert a == b
