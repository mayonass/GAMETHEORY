"""Evoluce: výplatní matice jednou, vymírání před mutací, součet 1000."""

from __future__ import annotations

import os
import random
import time

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-tests-0123456789")

from app.game import registry
from app.game.evolution import CELKOVA_POPULACE, evolucni_krok, odehraj_evoluci, vyplatni_matice
from app.game.simulation import NastaveniZapasu

CISTE = NastaveniZapasu(kola=10, neznama_kola=False, mlha=0.0, delay=1, zkresleni=0.0)


def boti(*typy):
    return [registry.resolve_bot(t) for t in typy]


def test_klasicky_pribeh_allc_alld_tft():
    historie, vymreli = odehraj_evoluci(boti("always_cooperate", "always_defect", "tit_for_tat"), CISTE, 60)
    konec = historie[-1]
    # Totéž, co vypráví krok 4 příběhu: AllD nejdřív roste na úkor důvěřivých,
    # pak vymře (gen. 25); TfT ovládne většinu, AllC přežije jako černý pasažér.
    assert max(r[1] for r in historie) > historie[0][1]
    assert vymreli == [None, 25, None]
    assert konec[2] > 800 and konec[0] > 100


def test_soucet_je_vzdy_1000():
    random.seed(2)
    cfg = NastaveniZapasu(kola=30, neznama_kola=True, mlha=0.2, delay=1, zkresleni=0.05)
    for mutace in (0.0, 0.1, 5.0):
        historie, _ = odehraj_evoluci(boti(*registry.BUILTIN_BOTS), cfg, 80, mutace_procenta=mutace)
        for radek in historie:
            assert abs(sum(radek) - CELKOVA_POPULACE) < 1e-6


def test_mala_mutace_vymrely_druh_neznuluje():
    """0,1 % mutace dá vymřelému druhu jen 0,5 jedince na generaci - dřív
    ho vymírání hned znovu vynulovalo, teď v populaci zůstává."""
    historie, vymreli = odehraj_evoluci(boti("always_cooperate", "always_defect", "tit_for_tat"), CISTE, 200, mutace_procenta=0.1)
    assert all(x > 0 for x in historie[-1])
    assert vymreli == [None, None, None]


def test_vymirani_bez_mutace():
    nova = evolucni_krok([999.7, 0.3], [[3.0, 3.0], [3.0, 3.0]], 0.0)
    assert nova[1] == 0.0 and abs(nova[0] - CELKOVA_POPULACE) < 1e-9


def test_matice_je_prumer_a_sebe_sama_obe_strany():
    random.seed(7)
    cfg = NastaveniZapasu(kola=100, neznama_kola=False, mlha=0.0, delay=1, zkresleni=0.0)
    m = vyplatni_matice(boti("tit_for_tat", "always_defect", "zd_extortioner"), cfg)
    assert m[0][1] == 99 and m[1][0] == 104                 # deterministický zápas
    assert m[1][1] == 100                                    # AllD × AllD
    assert 100 <= m[2][2] <= 300                             # ZD × ZD: obě strany zprůměrované


def test_pocet_generaci_skoro_nic_nestoji():
    b = boti(*registry.BUILTIN_BOTS)
    cfg = NastaveniZapasu(kola=200, neznama_kola=False, mlha=0.1, delay=1, zkresleni=0.05)
    t = time.perf_counter(); odehraj_evoluci(b, cfg, 10); kratka = time.perf_counter() - t
    t = time.perf_counter(); odehraj_evoluci(b, cfg, 1000); dlouha = time.perf_counter() - t
    assert dlouha < kratka * 2 + 0.2
