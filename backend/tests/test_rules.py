"""Testy pravidlového bota (schema_version 2).

Spuštění z backend/:  python -m pytest tests -q
Potřebuje jen proměnné DATABASE_URL a SECRET_KEY (stačí cokoli - testy
na databázi nesahají, ale aplikace si je při importu načte).
"""

from __future__ import annotations

import os
import random

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret")

import pytest
from fastapi.testclient import TestClient

from app.game import registry, rules
from app.game.evolution import odehraj_evoluci
from app.game.simulation import NastaveniZapasu, odehraj_simulovany_zapas, odehraj_zapas_s_poctem_kol
from app.main import app

client = TestClient(app)

PRIKLAD = {
    "schema_version": 2,
    "name": "Custom Strategy",
    "initial_state": {"bot_mode": "COOP", "trust_score": 0, "timer": 0},
    "rules": [
        {
            "conditions": [{"metric": "opp_last_move", "op": "==", "value": "?"}],
            "action": {"type": "REPEAT_MY_LAST", "cooperate_prob": 1.0, "set_mode": None, "add_trust": 0, "set_timer": None},
        },
        {
            "conditions": [
                {"metric": "opp_defections_last_5", "op": ">=", "value": 2},
                {"metric": "score_diff", "op": "<", "value": 0},
            ],
            "action": {"type": "PROBABILITY", "cooperate_prob": 0.15, "set_mode": "RETALIATING", "add_trust": -2, "set_timer": 3},
        },
    ],
    "fallback_action": {"type": "PROBABILITY", "cooperate_prob": 1.0},
}


def bot(config):
    return registry.resolve_bot("custom", config)


def pravidlo(podminky, akce):
    return {"conditions": podminky, "action": akce}


def P(p, **kw):
    return {"type": "PROBABILITY", "cooperate_prob": p, **kw}


def v2(rules_, fallback=None, **kw):
    return {"schema_version": 2, "rules": rules_, "fallback_action": fallback or P(1.0), **kw}


# --------------------------------------------------------------------------
# Kontrola konfigurace
# --------------------------------------------------------------------------

def test_priklad_ze_zadani_projde():
    cfg = rules.zkontroluj_v2(PRIKLAD)
    assert cfg["initial_state"] == {"bot_mode": "COOP", "trust_score": 0, "timer": 0}
    assert len(cfg["rules"]) == 2
    assert isinstance(bot(PRIKLAD), rules.RuleBot)


@pytest.mark.parametrize("config, kus_chyby", [
    (v2([pravidlo([{"metric": "nesmysl", "op": "==", "value": 1}], P(1.0))]), "metric must be one of"),
    (v2([pravidlo([{"metric": "opp_last_move", "op": ">", "value": "C"}], P(1.0))]), "only be compared with == or !="),
    (v2([pravidlo([{"metric": "opp_last_move", "op": "==", "value": "X"}], P(1.0))]), "must be one of: C, D, ?"),
    (v2([pravidlo([{"metric": "opp_defections_last_5", "op": ">=", "value": 6}], P(1.0))]), "between 0 and 5"),
    (v2([pravidlo([{"metric": "opp_defections_last_5", "op": ">=", "value": 2.5}], P(1.0))]), "whole number"),
    (v2([pravidlo([{"metric": "opp_defections_last_5", "op": ">=", "value": True}], P(1.0))]), "must be a number"),
    (v2([pravidlo([{"metric": "round_number", "op": "=", "value": 1}], P(1.0))]), "op must be one of"),
    (v2([pravidlo([], {"type": "PROBABILITY"})]), "needs cooperate_prob"),
    (v2([pravidlo([], P(1.5))]), "between 0.0 and 1.0"),
    (v2([pravidlo([], {"type": "EVAL", "cooperate_prob": 1})]), "type must be one of"),
    (v2([pravidlo([], P(1.0, set_mode="ANGRY"))]), "set_mode"),
    (v2([pravidlo([], P(1.0, set_timer=21))]), "between 0 and 20"),
    (v2([pravidlo([], P(1.0))] * 21), "at most 20 rules"),
    (v2([pravidlo([{"metric": "timer", "op": ">", "value": 0}] * 7, P(1.0))]), "at most 6 conditions"),
    (v2([], initial_state={"trust_score": 11}), "between -10 and 10"),
    (v2([], error_rate=2), "error_rate"),
    ({"schema_version": 2, "rules": []}, "fallback_action is required"),
    ({**v2([]), "code": "import os"}, "unknown fields: code"),
    ({"schema_version": 3}, "Unknown schema_version"),
])
def test_spatna_konfigurace_se_odmitne(config, kus_chyby):
    with pytest.raises(registry.NevalidniKonfiguraceError) as exc:
        registry.zkontroluj_custom_config(config)
    assert kus_chyby in str(exc.value)


def test_klasicky_bot_funguje_dal():
    fn = registry.resolve_bot("custom", {"prvni_tah": "D", "zakladni_strategie": "tit_for_tat"})
    assert not isinstance(fn, rules.RuleBot)
    assert fn([], [], {"kolo": 0, "celkem_kol": None}) == "D"


# --------------------------------------------------------------------------
# Metriky
# --------------------------------------------------------------------------

def test_metriky_na_znamem_prubehu():
    my = list("CCCDCCDCCC")
    opp = list("CD?DDC?DDD")
    m = rules.spocitej_metriky(my, opp, {"kolo": 10, "celkem_kol": 12, "sum": 0.05, "mlha": 0.1}, dict(rules.VYCHOZI_STAV))
    assert m["round_number"] == 11
    assert m["rounds_left"] == 1
    assert m["env_noise"] == 0.05 and m["env_fog"] == 0.1
    assert m["opp_last_move"] == "D" and m["my_last_move"] == "C" and m["last_outcome"] == "CD"
    assert m["opp_defections_last_5"] == 3          # C ? D D D
    assert m["opp_defections_last_10"] == 6
    assert m["fog_count_last_5"] == 1
    assert m["opp_coop_rate_recent"] == round(2 / 8, 6)
    assert m["opp_coop_rate_overall"] == round(2 / 8, 6)
    assert m["opp_defections_total"] == 6 and m["visible_moves"] == 8
    assert m["consecutive_opp_defections"] == 3
    assert m["consecutive_opp_cooperations"] == 0
    assert m["my_last_payoff"] == 0
    # páry: CC, CD, C?, DD, CD, CC, D?, CD, CD, CD
    assert m["times_exploited"] == 5 and m["times_i_exploited"] == 0
    moje = 3 + 0 + 1 + 0 + 3 + 0 + 0 + 0          # = 7 z osmi viditelných kol
    jeho = 3 + 5 + 1 + 5 + 3 + 5 + 5 + 5          # = 32
    assert m["score_diff"] == moje - jeho
    assert m["my_avg_payoff"] == round(moje / 8, 6)


def test_serie_preskakuje_mlhu():
    m = rules.spocitej_metriky(list("CCCC"), list("DD?D"), {"kolo": 4, "celkem_kol": None}, dict(rules.VYCHOZI_STAV))
    assert m["consecutive_opp_defections"] == 3
    assert m["rounds_left"] is None
    assert m["my_last_payoff"] == 0


def test_v_prvnim_kole_neplati_ani_nerovnost():
    """Neznámá hodnota = podmínka neplatí, ani "!=" (jinak by "soupeř
    naposledy nezradil" platilo dřív, než soupeř vůbec něco zahrál)."""
    fn = bot(v2([pravidlo([{"metric": "opp_last_move", "op": "!=", "value": "D"}], P(0.0))], fallback=P(1.0)))
    inst = fn.novy_zapas()
    assert inst([], [], {"kolo": 0, "celkem_kol": None}) == "C"
    assert inst(["C"], ["C"], {"kolo": 1, "celkem_kol": None}) == "D"


# --------------------------------------------------------------------------
# Akce a paměť
# --------------------------------------------------------------------------

def test_akce_repeat_a_mirror():
    rep = bot(v2([], fallback={"type": "REPEAT_MY_LAST"})).novy_zapas()
    assert rep([], [], {"kolo": 0}) == "C"
    assert rep(["D"], ["C"], {"kolo": 1}) == "D"
    mir = bot(v2([], fallback={"type": "MIRROR_OPP_LAST_VISIBLE"})).novy_zapas()
    assert mir([], [], {"kolo": 0}) == "C"
    assert mir(["C", "C"], ["D", "?"], {"kolo": 2}) == "D"
    assert mir(["C"], ["?"], {"kolo": 1}) == "C"


def test_pravidla_v_poradi_a_and():
    cfg = v2([
        pravidlo([{"metric": "round_number", "op": ">=", "value": 2}, {"metric": "opp_last_move", "op": "==", "value": "D"}], P(0.0)),
        pravidlo([{"metric": "round_number", "op": ">=", "value": 2}], P(1.0)),
    ], fallback=P(0.0))
    inst = bot(cfg).novy_zapas()
    assert inst([], [], {"kolo": 0}) == "D"            # nic neplatí -> fallback
    assert inst(["D"], ["C"], {"kolo": 1}) == "C"      # jen druhé pravidlo
    assert inst(["D", "C"], ["C", "D"], {"kolo": 2}) == "D"  # první pravidlo vyhraje


def test_pamet_casovac_a_duvera():
    cfg = v2(
        [
            pravidlo([{"metric": "timer", "op": ">", "value": 0}], P(0.0)),
            pravidlo([{"metric": "opp_last_move", "op": "==", "value": "D"}], P(0.0, set_mode="RETALIATING", add_trust=-7, set_timer=3)),
        ],
        fallback=P(1.0, add_trust=1),
        initial_state={"bot_mode": "COOP", "trust_score": 0, "timer": 0},
    )
    inst = bot(cfg).novy_zapas()
    info = lambda k: {"kolo": k}
    assert inst([], [], info(0)) == "C" and inst.stav == {"bot_mode": "COOP", "trust_score": 1, "timer": 0}
    assert inst(["C"], ["D"], info(1)) == "D" and inst.stav == {"bot_mode": "RETALIATING", "trust_score": -6, "timer": 3}
    # Časovač se snižuje NA ZAČÁTKU kola: 3 -> 2, 2 -> 1 (pořád trestá), 1 -> 0 (už ne).
    assert inst(["C", "D"], ["D", "C"], info(2)) == "D" and inst.stav["timer"] == 2
    assert inst(["C", "D", "D"], ["D", "C", "C"], info(3)) == "D" and inst.stav["timer"] == 1
    assert inst(["C", "D", "D", "D"], ["D", "C", "C", "C"], info(4)) == "C" and inst.stav["timer"] == 0
    # Důvěra se ořízne na -10.
    inst.stav["trust_score"] = -9
    inst(["C"] * 5, ["C"] * 4 + ["D"], info(5))
    assert inst.stav["trust_score"] == -10


def test_pamet_se_nenese_mezi_zapasy_ani_mezi_stranami():
    """Bot přepne do GRUDGE po první zradě. Proti Always Defect musí být
    v GRUDGE, ale další zápas proti Always Cooperate musí začít znovu v COOP
    a spolupracovat celou dobu."""
    grudger = bot(v2(
        [
            pravidlo([{"metric": "bot_mode", "op": "==", "value": "GRUDGE"}], P(0.0)),
            pravidlo([{"metric": "opp_last_move", "op": "==", "value": "D"}], P(0.0, set_mode="GRUDGE")),
        ],
        initial_state={"bot_mode": "COOP"},
    ))
    cfg = NastaveniZapasu(kola=20, neznama_kola=False, mlha=0, delay=1, zkresleni=0)
    s1, _ = odehraj_simulovany_zapas(grudger, registry.resolve_bot("always_defect"), cfg)
    assert s1 == 19
    s1, s2 = odehraj_simulovany_zapas(grudger, registry.resolve_bot("always_cooperate"), cfg)
    assert (s1, s2) == (60, 60)
    s1, s2 = odehraj_simulovany_zapas(grudger, grudger, cfg)
    assert (s1, s2) == (60, 60)


def test_chybovost():
    random.seed(1)
    inst = bot(v2([], fallback=P(1.0), error_rate=0.3)).novy_zapas()
    tahy = [inst([], [], {"kolo": 0}) for _ in range(4000)]
    assert 0.27 < tahy.count("D") / len(tahy) < 0.33


def test_prostredi_se_predava_ze_simulace():
    """Bot spolupracuje jen bez šumu - se šumem 10 % musí zrazovat."""
    fn = bot(v2([pravidlo([{"metric": "env_noise", "op": ">", "value": 0.05}], P(0.0))]))
    vs = registry.resolve_bot("always_cooperate")
    _, _, _, zaznam = odehraj_zapas_s_poctem_kol(fn, vs, NastaveniZapasu(10, False, 0, 1, 0.1))
    assert all(r["move1"] == "D" for r in zaznam)
    _, _, _, zaznam = odehraj_zapas_s_poctem_kol(fn, vs, NastaveniZapasu(10, False, 0, 1, 0.0))
    assert all(r["move1"] == "C" for r in zaznam)


def test_zbyvajici_kola():
    fn = bot(v2([pravidlo([{"metric": "rounds_left", "op": "==", "value": 0}], P(0.0))]))
    vs = registry.resolve_bot("always_cooperate")
    _, _, _, zaznam = odehraj_zapas_s_poctem_kol(fn, vs, NastaveniZapasu(5, False, 0, 1, 0))
    assert [r["move1"] for r in zaznam] == list("CCCCD")
    # Neznámý počet kol = bot neví, kdy je konec.
    _, _, _, zaznam = odehraj_zapas_s_poctem_kol(fn, vs, NastaveniZapasu(5, True, 0, 1, 0))
    assert all(r["move1"] == "C" for r in zaznam)


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

def test_api_duel_turnaj_evoluce_s_pravidlovym_botem():
    spec = {"type": "custom", "config": PRIKLAD}
    r = client.post("/simulate/duel", json={"bot1": spec, "bot2": {"type": "tit_for_tat"}, "settings": {"kola": 30, "zkresleni": 0.05, "mlha": 0.1}})
    assert r.status_code == 200, r.text
    assert r.json()["bot1_name"] == "Custom Strategy"
    r = client.post("/simulate/tournament", json={"bots": [spec, {"type": "grudger"}, {"type": "pavlov"}], "settings": {"kola": 20}, "repeats": 3})
    assert r.status_code == 200, r.text
    r = client.post("/simulate/evolution", json={"bots": [spec, {"type": "always_defect"}, {"type": "tit_for_tat"}], "settings": {"kola": 20}, "generations": 20})
    assert r.status_code == 200, r.text


def test_api_spatny_bot_vrati_422_s_vysvetlenim():
    spec = {"type": "custom", "config": v2([pravidlo([{"metric": "eval", "op": "==", "value": 1}], P(1.0))])}
    r = client.post("/simulate/duel", json={"bot1": spec, "bot2": {"type": "tit_for_tat"}})
    assert r.status_code == 422
    assert "metric must be one of" in r.text


def test_api_play_move_vraci_a_prijima_pamet():
    spec = {"type": "custom", "config": v2(
        [pravidlo([{"metric": "opp_last_move", "op": "==", "value": "D"}], P(0.0, set_mode="RETALIATING", set_timer=5))],
        initial_state={"bot_mode": "COOP"},
    )}
    r = client.post("/play/move", json={"bot": spec})
    assert r.status_code == 200 and r.json() == {"move": "C", "bot_state": {"bot_mode": "COOP", "trust_score": 0, "timer": 0}}
    r = client.post("/play/move", json={"bot": spec, "bot_history": ["C"], "opponent_history": ["D"], "bot_state": r.json()["bot_state"]})
    assert r.json() == {"move": "D", "bot_state": {"bot_mode": "RETALIATING", "trust_score": 0, "timer": 5}}
    r = client.post("/play/move", json={"bot": spec, "bot_history": ["C", "D"], "opponent_history": ["D", "C"], "bot_state": r.json()["bot_state"]})
    assert r.json()["bot_state"] == {"bot_mode": "RETALIATING", "trust_score": 0, "timer": 4}
    r = client.post("/play/move", json={"bot": spec, "bot_state": {"timer": 99}})
    assert r.status_code == 400 and "between 0 and 20" in r.text
    # Vestavění boti žádnou paměť nemají.
    r = client.post("/play/move", json={"bot": {"type": "tit_for_tat"}})
    assert r.json() == {"move": "C", "bot_state": None}
