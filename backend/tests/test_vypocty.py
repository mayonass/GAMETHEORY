"""Velké simulace v odděleném procesu (app/vypocty.py)."""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-tests-0123456789")

import pytest
from fastapi.testclient import TestClient

from app import vypocty
from app.config import get_settings
from app.game import registry
from app.game.simulation import NastaveniZapasu
from app.game.turnaj import odehraj_turnaj
from app.main import app
from app.routers import simulate

client = TestClient(app)

VELKY_TURNAJ = {
    "bots": [{"type": t} for t in ["always_cooperate", "always_defect", "tit_for_tat", "grudger", "pavlov"]],
    "settings": {"kola": 500},
    "repeats": 5,          # 10 dvojic × 500 kol × 5 = 25 000 kol -> odděleně
}


def test_velky_turnaj_v_oddelenem_procesu_da_stejny_vysledek():
    r = client.post("/simulate/tournament", json=VELKY_TURNAJ)
    assert r.status_code == 200, r.text
    # Deterministické strategie bez šumu - výsledek musí přesně sedět s přímým výpočtem.
    funkce = [registry.resolve_bot(b["type"]) for b in VELKY_TURNAJ["bots"]]
    prime = odehraj_turnaj(funkce, NastaveniZapasu(500, False, 0.0, 1, 0.0), 5)
    skore = {s["name"]: s["score"] for s in r.json()["standings"]}
    for i, b in enumerate(VELKY_TURNAJ["bots"]):
        assert skore[registry.bot_display_name(b["type"], None, None)] == round(prime["body_celkem"][i] / 5, 1)


def test_pravidlovy_bot_projde_do_procesu():
    bot = {"type": "custom", "config": {
        "schema_version": 2,
        "rules": [{"conditions": [{"metric": "score_diff", "op": "<", "value": 0}], "action": {"type": "PROBABILITY", "cooperate_prob": 0}}],
        "fallback_action": {"type": "MIRROR_OPP_LAST_VISIBLE"},
    }}
    telo = {**VELKY_TURNAJ, "bots": VELKY_TURNAJ["bots"] + [bot], "settings": {"kola": 300, "mlha": 0.2, "zkresleni": 0.05}}
    r = client.post("/simulate/tournament", json=telo)
    assert r.status_code == 200, r.text
    assert len(r.json()["standings"]) == 6


def test_casovy_limit_ukonci_vypocet(monkeypatch):
    monkeypatch.setattr(get_settings(), "simulation_timeout_seconds", 0.2)
    r = client.post("/simulate/evolution", json={
        "bots": [{"type": t} for t in registry.BUILTIN_BOTS],
        "settings": {"kola": 300, "zkresleni": 0.05},
        "generations": 200,
    })
    assert r.status_code == 503
    assert "took longer than 0.2 seconds" in r.json()["detail"]
    # Po ukončení musí jít spustit další simulace.
    monkeypatch.setattr(get_settings(), "simulation_timeout_seconds", 60)
    assert client.post("/simulate/tournament", json=VELKY_TURNAJ).status_code == 200


def test_druha_velka_simulace_ceka_a_pak_odmitne():
    assert vypocty._jedna_naraz.acquire(timeout=1)
    try:
        with pytest.raises(vypocty.Zaneprazdneno):
            vypocty.spust_oddelene(odehraj_turnaj, [], None, 1, casovy_limit=5, cekani=0.1)
    finally:
        vypocty._jedna_naraz.release()


def test_zaneprazdneny_server_vrati_503(monkeypatch):
    def obsazeno(*a, **k):
        raise vypocty.Zaneprazdneno
    monkeypatch.setattr(simulate, "spust_oddelene", obsazeno)
    r = client.post("/simulate/tournament", json=VELKY_TURNAJ)
    assert r.status_code == 503 and "busy" in r.json()["detail"]
    assert r.headers.get("retry-after") == "10"


def test_mala_simulace_bezi_rovnou(monkeypatch):
    def nesmi(*a, **k):
        raise AssertionError("malá simulace nemá startovat proces")
    monkeypatch.setattr(simulate, "spust_oddelene", nesmi)
    r = client.post("/simulate/tournament", json={**VELKY_TURNAJ, "settings": {"kola": 10}, "repeats": 1})
    assert r.status_code == 200
