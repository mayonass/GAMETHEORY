"""
Pravidlový vlastní bot (schema_version 2) - "no code, just values".

Uživatel posílá jen JSON: seznam pravidel (podmínky + akce) a záložní akci.
Tenhle modul ho zkontroluje (`zkontroluj_v2`) a dosadí do jedné pevné
vyhodnocovací funkce (`RuleBot`). Nikde se nevolá eval/exec - metriky,
operátory, akce i změny paměti jsou pevné výčty definované níže.

Jak bot rozhoduje v každém kole:
  1. časovač (`timer`) se sníží o 1 (nejméně na 0),
  2. pravidla se procházejí v pořadí; první, jehož VŠECHNY podmínky platí,
     rozhodne (prázdný seznam podmínek platí vždy),
  3. když nesedí žádné, použije se `fallback_action`,
  4. akce určí tah a případně změní paměť (`set_mode`, `add_trust`, `set_timer`),
  5. nakonec se uplatní `error_rate` (třesoucí se ruka).

Důležité rozhodnutí: metriky skóre (`my_last_payoff`, `score_diff`,
`my_avg_payoff`) se počítají jen z toho, co bot VIDĚL - z vlastních tahů
a soupeřových tahů, které k němu dorazily (možná převrácené šumem) a nebyly
skryté mlhou. Kdyby bot znal skutečné skóre, dopočítal by si z něj
soupeřův skutečný tah a mlha i šum by pro něj přestaly existovat.

Metrika, kterou zatím nejde určit (třeba podíl spolupráce, když bot ještě
nic neviděl), má hodnotu None a každá podmínka s ní je nepravdivá.

Stav (`bot_mode`, `trust_score`, `timer`) patří jednomu zápasu. Proto je
`RuleBot` továrna: `novy_zapas()` vrátí čerstvou instanci a simulace si ji
vyrobí na začátku každého zápasu. Bez toho by si bot v turnaji nesl paměť
ze zápasu do zápasu a v evoluci (kde hraje i sám se sebou) by obě strany
sdílely jednu paměť.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from operator import add
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = 2

MAX_PRAVIDEL = 20
MAX_PODMINEK = 6
MAX_NAZEV = 100

REZIMY = ("DEFAULT", "COOP", "PROBING", "RETALIATING", "GRUDGE")
DUVERA_MIN, DUVERA_MAX = -10, 10
TIMER_MIN, TIMER_MAX = 0, 20

AKCE = ("PROBABILITY", "REPEAT_MY_LAST", "MIRROR_OPP_LAST_VISIBLE")

CISELNE_OPERATORY = ("==", "!=", "<", "<=", ">", ">=")
VYCTOVE_OPERATORY = ("==", "!=")

# Body z pohledu "mě" podle dvojice (můj tah, soupeřův tah).
_MOJE_BODY = {"CC": 3, "CD": 0, "DC": 5, "DD": 1}
_JEHO_BODY = {"CC": 3, "CD": 5, "DC": 0, "DD": 1}

# ---------------------------------------------------------------------------
# Katalog metrik. Musí odpovídat METRIKY v frontend/index.html
# (kontroluje to backend/tests/test_rules.py).
#   "num":  (min, max, celé číslo?)
#   "enum": povolené řetězce
# ---------------------------------------------------------------------------

METRIKY: Dict[str, Dict[str, Any]] = {
    # A. Klouzavá okna (filtr šumu a mlhy)
    "opp_defections_last_5": {"typ": "num", "min": 0, "max": 5, "cele": True},
    "opp_defections_last_10": {"typ": "num", "min": 0, "max": 10, "cele": True},
    "opp_coop_rate_recent": {"typ": "num", "min": 0.0, "max": 1.0, "cele": False},
    "opp_coop_rate_overall": {"typ": "num", "min": 0.0, "max": 1.0, "cele": False},
    "consecutive_opp_defections": {"typ": "num", "min": 0, "max": 1000, "cele": True},
    "consecutive_opp_cooperations": {"typ": "num", "min": 0, "max": 1000, "cele": True},
    "fog_count_last_5": {"typ": "num", "min": 0, "max": 5, "cele": True},
    "opp_defections_total": {"typ": "num", "min": 0, "max": 1000, "cele": True},
    "visible_moves": {"typ": "num", "min": 0, "max": 1000, "cele": True},
    # B. Body (odhad z toho, co bot viděl)
    "my_last_payoff": {"typ": "num", "min": 0, "max": 5, "cele": True},
    "score_diff": {"typ": "num", "min": -5000, "max": 5000, "cele": True},
    "my_avg_payoff": {"typ": "num", "min": 0.0, "max": 5.0, "cele": False},
    # C. Společná historie
    "opp_last_move": {"typ": "enum", "hodnoty": ("C", "D", "?")},
    "my_last_move": {"typ": "enum", "hodnoty": ("C", "D")},
    "last_outcome": {"typ": "enum", "hodnoty": ("CC", "CD", "DC", "DD", "C?", "D?")},
    "times_exploited": {"typ": "num", "min": 0, "max": 1000, "cele": True},
    "times_i_exploited": {"typ": "num", "min": 0, "max": 1000, "cele": True},
    # D. Paměť bota
    "bot_mode": {"typ": "enum", "hodnoty": REZIMY},
    "trust_score": {"typ": "num", "min": DUVERA_MIN, "max": DUVERA_MAX, "cele": True},
    "timer": {"typ": "num", "min": TIMER_MIN, "max": TIMER_MAX, "cele": True},
    # E. Prostředí
    "round_number": {"typ": "num", "min": 1, "max": 1000, "cele": True},
    "rounds_left": {"typ": "num", "min": 0, "max": 1000, "cele": True},
    "env_noise": {"typ": "num", "min": 0.0, "max": 1.0, "cele": False},
    "env_fog": {"typ": "num", "min": 0.0, "max": 1.0, "cele": False},
}

VYCHOZI_STAV = {"bot_mode": "DEFAULT", "trust_score": 0, "timer": 0}

POVOLENE_KLICE = {"schema_version", "type", "name", "initial_state", "rules", "fallback_action", "error_rate"}
_KLICE_AKCE = {"type", "cooperate_prob", "set_mode", "add_trust", "set_timer"}
_KLICE_PODMINKY = {"metric", "op", "value"}
_KLICE_PRAVIDLA = {"conditions", "action", "label"}


class ChybaPravidel(ValueError):
    """Pravidlová konfigurace obsahuje něco, s čím se nedá hrát."""


def je_v2(config: Any) -> bool:
    return isinstance(config, dict) and config.get("schema_version") == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Kontrola konfigurace
# ---------------------------------------------------------------------------

def _je_cislo(x: Any) -> bool:
    # bool je v Pythonu podtyp int - True jako práh nedává smysl.
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _cele_v_rozsahu(x: Any, mini: int, maxi: int, kde: str) -> int:
    if not _je_cislo(x) or not float(x).is_integer():
        raise ChybaPravidel(f"{kde} must be a whole number between {mini} and {maxi}. Got {x!r}.")
    if not (mini <= x <= maxi):
        raise ChybaPravidel(f"{kde} must be between {mini} and {maxi}. Got {x!r}.")
    return int(x)


def _podil(x: Any, kde: str) -> float:
    if not _je_cislo(x) or not (0.0 <= x <= 1.0):
        raise ChybaPravidel(f"{kde} must be a number between 0.0 and 1.0. Got {x!r}.")
    return float(x)


def _zkontroluj_stav(stav: Any, kde: str) -> dict:
    if stav is None:
        return dict(VYCHOZI_STAV)
    if not isinstance(stav, dict):
        raise ChybaPravidel(f"{kde} must be an object.")
    nezname = sorted(set(stav) - set(VYCHOZI_STAV))
    if nezname:
        raise ChybaPravidel(f"{kde} contains unknown fields: {', '.join(nezname)}.")
    vysledek = dict(VYCHOZI_STAV)
    if "bot_mode" in stav:
        if stav["bot_mode"] not in REZIMY:
            raise ChybaPravidel(f"{kde}.bot_mode must be one of: {', '.join(REZIMY)}. Got {stav['bot_mode']!r}.")
        vysledek["bot_mode"] = stav["bot_mode"]
    if "trust_score" in stav:
        vysledek["trust_score"] = _cele_v_rozsahu(stav["trust_score"], DUVERA_MIN, DUVERA_MAX, f"{kde}.trust_score")
    if "timer" in stav:
        vysledek["timer"] = _cele_v_rozsahu(stav["timer"], TIMER_MIN, TIMER_MAX, f"{kde}.timer")
    return vysledek


def zkontroluj_stav(stav: Any) -> dict:
    """Veřejná kontrola stavu (paměti) bota - používá ji /play/move."""
    return _zkontroluj_stav(stav, "bot_state")


def _zkontroluj_akci(akce: Any, kde: str) -> dict:
    if not isinstance(akce, dict):
        raise ChybaPravidel(f"{kde} must be an object.")
    nezname = sorted(set(akce) - _KLICE_AKCE)
    if nezname:
        raise ChybaPravidel(f"{kde} contains unknown fields: {', '.join(nezname)}.")
    typ = akce.get("type")
    if typ not in AKCE:
        raise ChybaPravidel(f"{kde}.type must be one of: {', '.join(AKCE)}. Got {typ!r}.")

    vysledek: Dict[str, Any] = {"type": typ, "cooperate_prob": 1.0, "set_mode": None, "add_trust": 0, "set_timer": None}

    if "cooperate_prob" in akce and akce["cooperate_prob"] is not None:
        vysledek["cooperate_prob"] = _podil(akce["cooperate_prob"], f"{kde}.cooperate_prob")
    elif typ == "PROBABILITY":
        raise ChybaPravidel(f"{kde}: type PROBABILITY needs cooperate_prob (0.0 to 1.0).")

    if akce.get("set_mode") is not None:
        if akce["set_mode"] not in REZIMY:
            raise ChybaPravidel(f"{kde}.set_mode must be null or one of: {', '.join(REZIMY)}. Got {akce['set_mode']!r}.")
        vysledek["set_mode"] = akce["set_mode"]
    if akce.get("add_trust") is not None:
        rozsah = DUVERA_MAX - DUVERA_MIN
        vysledek["add_trust"] = _cele_v_rozsahu(akce["add_trust"], -rozsah, rozsah, f"{kde}.add_trust")
    if akce.get("set_timer") is not None:
        vysledek["set_timer"] = _cele_v_rozsahu(akce["set_timer"], TIMER_MIN, TIMER_MAX, f"{kde}.set_timer")
    return vysledek


def _zkontroluj_podminku(podminka: Any, kde: str) -> tuple:
    if not isinstance(podminka, dict):
        raise ChybaPravidel(f"{kde} must be an object with metric, op and value.")
    nezname = sorted(set(podminka) - _KLICE_PODMINKY)
    if nezname:
        raise ChybaPravidel(f"{kde} contains unknown fields: {', '.join(nezname)}.")
    metrika = podminka.get("metric")
    if metrika not in METRIKY:
        raise ChybaPravidel(f"{kde}.metric must be one of: {', '.join(METRIKY)}. Got {metrika!r}.")
    popis = METRIKY[metrika]
    op = podminka.get("op")
    hodnota = podminka.get("value")

    if popis["typ"] == "enum":
        if op not in VYCTOVE_OPERATORY:
            raise ChybaPravidel(f"{kde}: {metrika} can only be compared with == or !=. Got {op!r}.")
        if hodnota not in popis["hodnoty"]:
            raise ChybaPravidel(f"{kde}: {metrika} must be one of: {', '.join(popis['hodnoty'])}. Got {hodnota!r}.")
        return (metrika, op, hodnota)

    if op not in CISELNE_OPERATORY:
        raise ChybaPravidel(f"{kde}.op must be one of: {' '.join(CISELNE_OPERATORY)}. Got {op!r}.")
    if not _je_cislo(hodnota):
        raise ChybaPravidel(f"{kde}: the value for {metrika} must be a number. Got {hodnota!r}.")
    if not (popis["min"] <= hodnota <= popis["max"]):
        raise ChybaPravidel(f"{kde}: the value for {metrika} must be between {popis['min']} and {popis['max']}. Got {hodnota!r}.")
    if popis["cele"] and not float(hodnota).is_integer():
        raise ChybaPravidel(f"{kde}: the value for {metrika} must be a whole number. Got {hodnota!r}.")
    return (metrika, op, float(hodnota))


def zkontroluj_v2(config: Any) -> dict:
    """Ověří pravidlovou konfiguraci a vrátí ji v normalizovaném tvaru.

    Vyhodí `ChybaPravidel` s anglickým vysvětlením (uživatel ho vidí ve
    hře), nikdy nic tiše neopravuje.
    """
    if not isinstance(config, dict):
        raise ChybaPravidel("The bot configuration must be an object (a JSON dictionary).")
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ChybaPravidel("schema_version must be 2.")
    nezname = sorted(set(config) - POVOLENE_KLICE)
    if nezname:
        raise ChybaPravidel(
            "The configuration contains unknown fields: " + ", ".join(nezname)
            + ". Allowed fields are: " + ", ".join(sorted(POVOLENE_KLICE)) + "."
        )

    jmeno = config.get("name")
    if jmeno is not None and (not isinstance(jmeno, str) or len(jmeno) > MAX_NAZEV):
        raise ChybaPravidel(f"name must be text of at most {MAX_NAZEV} characters.")

    pravidla = config.get("rules", [])
    if not isinstance(pravidla, list):
        raise ChybaPravidel("rules must be a list.")
    if len(pravidla) > MAX_PRAVIDEL:
        raise ChybaPravidel(f"A bot can have at most {MAX_PRAVIDEL} rules. Got {len(pravidla)}.")

    normalizovana = []
    for i, pravidlo in enumerate(pravidla, start=1):
        kde = f"Rule {i}"
        if not isinstance(pravidlo, dict):
            raise ChybaPravidel(f"{kde} must be an object with conditions and action.")
        nezname = sorted(set(pravidlo) - _KLICE_PRAVIDLA)
        if nezname:
            raise ChybaPravidel(f"{kde} contains unknown fields: {', '.join(nezname)}.")
        podminky = pravidlo.get("conditions", [])
        if not isinstance(podminky, list):
            raise ChybaPravidel(f"{kde}: conditions must be a list.")
        if len(podminky) > MAX_PODMINEK:
            raise ChybaPravidel(f"{kde} can have at most {MAX_PODMINEK} conditions. Got {len(podminky)}.")
        if "action" not in pravidlo:
            raise ChybaPravidel(f"{kde} needs an action.")
        normalizovana.append({
            "conditions": [_zkontroluj_podminku(p, f"{kde}, condition {j}") for j, p in enumerate(podminky, start=1)],
            "action": _zkontroluj_akci(pravidlo["action"], f"{kde} action"),
        })

    if "fallback_action" not in config:
        raise ChybaPravidel("fallback_action is required - it decides when no rule matches.")

    chyba = config.get("error_rate", 0)
    return {
        "schema_version": SCHEMA_VERSION,
        "name": jmeno,
        "initial_state": _zkontroluj_stav(config.get("initial_state"), "initial_state"),
        "rules": normalizovana,
        "fallback_action": _zkontroluj_akci(config["fallback_action"], "fallback_action"),
        "error_rate": _podil(chyba, "error_rate") if chyba is not None else 0.0,
    }


# ---------------------------------------------------------------------------
# Výpočet metrik
# ---------------------------------------------------------------------------

def _serie(historie: List[str], tah: str) -> int:
    """Kolik posledních VIDITELNÝCH tahů soupeře je `tah` - mlha ('?') se
    přeskakuje, nepřerušuje. Jde se jen od konce, ne přes celou historii."""
    n = 0
    for x in reversed(historie):
        if x == "?":
            continue
        if x != tah:
            break
        n += 1
    return n


def spocitej_metriky(my_hist: List[str], opp_hist: List[str], info: dict, stav: dict, potreba: Optional[set] = None,
                     mezisoucty: Optional[dict] = None) -> dict:
    """Spočítá metriky pro aktuální kolo.

    `potreba` = množina metrik, které pravidla opravdu používají; ostatní se
    nepočítají (v evoluci se tahle funkce volá stotisíckrát). None = všechny.
    """
    m: Dict[str, Any] = {}
    chce = (lambda k: True) if potreba is None else potreba.__contains__

    n = len(opp_hist)
    kolo = info.get("kolo", n) + 1
    m["round_number"] = kolo
    celkem = info.get("celkem_kol")
    m["rounds_left"] = (celkem - kolo) if celkem is not None else None
    m["env_noise"] = info.get("sum", 0.0)
    m["env_fog"] = info.get("mlha", 0.0)
    m["bot_mode"] = stav["bot_mode"]
    m["trust_score"] = stav["trust_score"]
    m["timer"] = stav["timer"]

    m["opp_last_move"] = opp_hist[-1] if n else None
    m["my_last_move"] = my_hist[-1] if my_hist else None
    m["last_outcome"] = (my_hist[-1] + opp_hist[-1]) if n else None

    posl5 = opp_hist[-5:]
    posl10 = opp_hist[-10:]
    m["opp_defections_last_5"] = posl5.count("D")
    m["opp_defections_last_10"] = posl10.count("D")
    m["fog_count_last_5"] = posl5.count("?")

    if chce("opp_coop_rate_recent"):
        c, d = posl10.count("C"), posl10.count("D")
        m["opp_coop_rate_recent"] = round(c / (c + d), 6) if (c + d) else None

    if chce("opp_coop_rate_overall") or chce("opp_defections_total") or chce("visible_moves"):
        c, d = opp_hist.count("C"), opp_hist.count("D")
        m["opp_defections_total"] = d
        m["visible_moves"] = c + d
        m["opp_coop_rate_overall"] = round(c / (c + d), 6) if (c + d) else None

    if chce("consecutive_opp_defections") or chce("consecutive_opp_cooperations"):
        m["consecutive_opp_defections"] = _serie(opp_hist, "D")
        m["consecutive_opp_cooperations"] = _serie(opp_hist, "C")

    if chce("my_last_payoff"):
        m["my_last_payoff"] = _MOJE_BODY.get(m["last_outcome"]) if n else None

    if any(chce(k) for k in ("score_diff", "my_avg_payoff", "times_exploited", "times_i_exploited")):
        # Jeden průchod v C: spočítá dvojice "CC", "CD", "C?", ... přes celou historii.
        if mezisoucty is None:
            vysledky = Counter(map(add, my_hist, opp_hist))
            cc, cd, dc, dd = vysledky["CC"], vysledky["CD"], vysledky["DC"], vysledky["DD"]
        else:
            cc, cd, dc, dd = _pocty_dvojic(my_hist, opp_hist, mezisoucty)
        m["times_exploited"] = cd
        m["times_i_exploited"] = dc
        moje = 3 * cc + 5 * dc + dd
        jeho = 3 * cc + 5 * cd + dd
        m["score_diff"] = moje - jeho
        videno = cc + cd + dc + dd
        m["my_avg_payoff"] = round(moje / videno, 6) if videno else None

    return m


def _pocty_dvojic(my_hist: List[str], opp_hist: List[str], mezi: dict) -> tuple:
    """Počty dvojic CC/CD/DC/DD přes celý zápas, bez procházení celé historie.

    Viděný tah soupeře se už nikdy nezmění - mění se jen '?' (mlha se
    rozplyne). Hotový začátek historie (až po první '?') si proto instance
    bota pamatuje v `mezi` a v každém kole dopočítá jen nové tahy a krátký
    konec, kde ještě může být mlha.
    """
    n = len(opp_hist)
    z = mezi.get("z", 0)
    if z > n:                       # jiný zápas - začni znovu
        mezi.clear()
        z = 0
    pocty = mezi.setdefault("pocty", {"CC": 0, "CD": 0, "DC": 0, "DD": 0})
    while z < n and opp_hist[z] != "?":
        pocty[my_hist[z] + opp_hist[z]] += 1
        z += 1
    mezi["z"] = z
    cc, cd, dc, dd = pocty["CC"], pocty["CD"], pocty["DC"], pocty["DD"]
    for i in range(z, n):
        par = my_hist[i] + opp_hist[i]
        if par == "CC":
            cc += 1
        elif par == "CD":
            cd += 1
        elif par == "DC":
            dc += 1
        elif par == "DD":
            dd += 1
    return cc, cd, dc, dd


_POROVNANI = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def _plati(podminka: tuple, metriky: dict) -> bool:
    metrika, op, hodnota = podminka
    aktualni = metriky.get(metrika)
    if aktualni is None:
        # Neznámá hodnota (ještě nic neviděl) - žádná podmínka neplatí,
        # ani "!=". Jinak by "opp_last_move != D" platilo v prvním kole.
        return False
    return _POROVNANI[op](aktualni, hodnota)


# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------

def _posledni_viditelny(opp_hist: List[str]) -> Optional[str]:
    for x in reversed(opp_hist):
        if x != "?":
            return x
    return None


class RuleBotZapas:
    """Jedna instance pravidlového bota pro jeden zápas (drží paměť)."""

    __slots__ = ("cfg", "potreba", "stav", "posledni_pravidlo", "mezisoucty")

    def __init__(self, cfg: dict, potreba: set, stav: Optional[dict] = None):
        self.cfg = cfg
        self.potreba = potreba
        self.stav = dict(stav if stav is not None else cfg["initial_state"])
        self.posledni_pravidlo: Optional[int] = None
        self.mezisoucty: dict = {}

    def __call__(self, my_hist, opp_hist, info) -> str:
        stav = self.stav
        stav["timer"] = max(0, stav["timer"] - 1)

        metriky = spocitej_metriky(my_hist, opp_hist, info, stav, self.potreba, self.mezisoucty)

        akce = self.cfg["fallback_action"]
        self.posledni_pravidlo = None
        for i, pravidlo in enumerate(self.cfg["rules"]):
            if all(_plati(p, metriky) for p in pravidlo["conditions"]):
                akce = pravidlo["action"]
                self.posledni_pravidlo = i
                break

        typ = akce["type"]
        if typ == "PROBABILITY":
            p = akce["cooperate_prob"]
            tah = "C" if p >= 1.0 else "D" if p <= 0.0 else ("C" if random.random() < p else "D")
        elif typ == "REPEAT_MY_LAST":
            tah = my_hist[-1] if my_hist else "C"
        else:  # MIRROR_OPP_LAST_VISIBLE
            tah = _posledni_viditelny(opp_hist) or "C"

        if akce["set_mode"] is not None:
            stav["bot_mode"] = akce["set_mode"]
        if akce["add_trust"]:
            stav["trust_score"] = max(DUVERA_MIN, min(DUVERA_MAX, stav["trust_score"] + akce["add_trust"]))
        if akce["set_timer"] is not None:
            stav["timer"] = akce["set_timer"]

        chyba = self.cfg["error_rate"]
        if chyba > 0 and random.random() < chyba:
            tah = "D" if tah == "C" else "C"
        return tah


class RuleBot:
    """Továrna na pravidlové boty. Simulace volá `novy_zapas()` na začátku
    každého zápasu, aby měl každý zápas (a každá strana) vlastní paměť.

    Zavolat ji přímo jako funkci jde taky (chová se jako jedna dlouhá
    instance) - jen kvůli kompatibilitě s kódem, který o továrnách neví.
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.potreba = {p[0] for r in cfg["rules"] for p in r["conditions"]}
        self._vychozi = None

    def novy_zapas(self, stav: Optional[dict] = None) -> RuleBotZapas:
        return RuleBotZapas(self.cfg, self.potreba, stav)

    def __call__(self, my_hist, opp_hist, info) -> str:
        if self._vychozi is None or not my_hist:
            self._vychozi = self.novy_zapas()
        return self._vychozi(my_hist, opp_hist, info)
