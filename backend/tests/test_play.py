"""Testy režimu "Play yourself" (POST /play/round)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret")

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def odehraj(tahy1, *, bot=None, tahy2=None, settings=None, bot_state=None):
    """Odehraje celý zápas kolo po kole přesně jako frontend."""
    historie, celkem, odpovedi = [], None, []
    for i, t in enumerate(tahy1):
        telo = {"settings": settings or {}, "history": historie, "move1": t}
        if celkem is not None:
            telo["rounds_total"] = celkem
        if bot:
            telo["bot"] = bot
            if bot_state is not None:
                telo["bot_state"] = bot_state
        else:
            telo["move2"] = tahy2[i]
        r = client.post("/play/round", json=telo)
        assert r.status_code == 200, r.text
        o = r.json()
        historie.append(o["round"])
        celkem = o["rounds_total"]
        bot_state = o["bot_state"]
        odpovedi.append(o)
        if o["over"]:
            break
    return odpovedi


def test_proti_tit_for_tat():
    o = odehraj(list("CDDCC"), bot={"type": "tit_for_tat"}, settings={"kola": 5})
    assert len(o) == 5 and o[-1]["over"] and o[-1]["rounds_total"] == 5
    assert [x["round"]["move2"] for x in o] == list("CCDDC")
    assert (o[-1]["score1"], o[-1]["score2"]) == (3 + 5 + 1 + 0 + 3, 3 + 0 + 1 + 5 + 3)
    assert o[-1]["seen_by_1"] == list("CCDDC")
    assert o[-1]["seen_by_2"] == list("CDDCC")
    assert all(x["bot_state"] is None for x in o)


def test_dva_hraci():
    o = odehraj(list("CCD"), tahy2=list("DCD"), settings={"kola": 3})
    assert [(x["round"]["points1"], x["round"]["points2"]) for x in o] == [(0, 5), (3, 3), (1, 1)]
    assert o[-1]["over"]


def test_mlha_se_rozplyne_po_zpozdeni_a_na_konci():
    o = odehraj(list("CCCC"), tahy2=list("DDDD"), settings={"kola": 4, "mlha": 1.0, "delay": 2})
    assert o[0]["seen_by_1"] == ["?"]
    assert o[1]["seen_by_1"] == ["?", "?"]
    assert o[2]["seen_by_1"] == ["D", "?", "?"]
    assert o[3]["seen_by_1"] == list("DDDD")      # konec zápasu: nic se neskrývá


def test_neznamy_pocet_kol():
    delky = {odehraj(["C"] * 40, tahy2=["C"] * 40, settings={"kola": 10, "neznama_kola": True})[-1]["rounds_total"] for _ in range(40)}
    assert min(delky) >= 7 and max(delky) <= 13 and len(delky) > 1


def test_pravidlovy_bot_si_nese_pamet():
    bot = {"type": "custom", "config": {
        "schema_version": 2,
        "rules": [
            {"conditions": [{"metric": "bot_mode", "op": "==", "value": "GRUDGE"}], "action": {"type": "PROBABILITY", "cooperate_prob": 0}},
            {"conditions": [{"metric": "opp_last_move", "op": "==", "value": "D"}],
             "action": {"type": "PROBABILITY", "cooperate_prob": 0, "set_mode": "GRUDGE"}},
        ],
        "fallback_action": {"type": "PROBABILITY", "cooperate_prob": 1},
    }}
    o = odehraj(list("CDCCC"), bot=bot, settings={"kola": 5})
    assert [x["round"]["move2"] for x in o] == list("CCDDD")
    assert o[-1]["bot_state"]["bot_mode"] == "GRUDGE"


def test_spatne_pozadavky():
    zaklad = {"move1": "C"}
    assert client.post("/play/round", json=zaklad).status_code == 422                       # ani bot, ani hráč 2
    assert client.post("/play/round", json={**zaklad, "move2": "C", "bot": {"type": "grudger"}}).status_code == 422
    assert client.post("/play/round", json={**zaklad, "move2": "C", "settings": {"kola": 500}}).status_code == 422
    r = client.post("/play/round", json={**zaklad, "move2": "C"}).json()["round"]
    falesny = {**r, "points1": 5}
    assert client.post("/play/round", json={**zaklad, "move2": "C", "rounds_total": 10, "history": [falesny]}).status_code == 422
    assert client.post("/play/round", json={**zaklad, "move2": "C", "history": [r]}).status_code == 422   # chybí rounds_total
    assert client.post("/play/round", json={**zaklad, "move2": "C", "rounds_total": 1, "history": [r]}).status_code == 422  # konec
    r = client.post("/play/round", json={**zaklad, "bot": {"type": "custom", "config": {"schema_version": 2, "rules": []}}})
    assert r.status_code == 422
