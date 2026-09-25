"""
Pevný registr povolených typů botů a kontrola jejich konfigurace.

DŮLEŽITÉ (bezpečnost): vlastní bot se NIKDY neskládá z uživatelského kódu.
Jediný způsob, jak si uživatel může "napsat vlastního bota", je přes JSON
konfiguraci typu `custom` (viz app.game.bots.CustomBotConfig) - ta se jen
dosadí jako parametry do pevně dané funkce `custom_player`. Nikde v backendu
se nevolá `eval`/`exec` ani se nenačítá a nespouští žádný kód dodaný
uživatelem.

Druhá vrstva obrany je `zkontroluj_custom_config`: hodnoty v konfiguraci se
ověří DŘÍV, než se z nich stane bot. Bez toho by třeba `prvni_tah: "Q"`
prošel až do výplatní matice a shodil celý zápas, nebo by se `tolerance_d`
jako text sečetlo s číslem a spadlo uprostřed výpočtu. Kontrola je tady
v herní vrstvě schválně - platí i pro volání mimo API.
"""

from __future__ import annotations

from functools import partial
from typing import Any, Callable, Dict, List, Optional

from . import bots

# Název typu bota -> (čistá funkce, český název, popis)
BUILTIN_BOTS: Dict[str, tuple] = {
    "always_cooperate": (bots.always_cooperate, "Vždy spolupracuj", "Vždy spolupracuje, bez ohledu na to, co dělá soupeř."),
    "always_defect": (bots.always_defect, "Vždy zraď", "Vždy zradí, snaží se maximalizovat svůj zisk na úkor ostatních."),
    "tit_for_tat": (bots.tit_for_tat, "Půjčka za oplátku", "Začne spoluprací, poté opakuje poslední viditelný tah soupeře."),
    "grudger": (bots.grudger, "Záštník", "Spolupracuje, dokud ho soupeř alespoň jednou nezradí - pak už jen zrazuje."),
    "pavlov": (bots.pavlov, "Pavlov", "Win-stay, lose-shift: při shodném výsledku opakuje tah, jinak ho změní."),
    "zd_extortioner": (bots.zd_extortioner, "ZD Vyděrač", "Zero-Determinant strategie, která si vynucuje vyšší skóre než soupeř."),
    "zd_generous": (bots.zd_generous, "ZD Štědrý", "Zero-Determinant strategie, která odměňuje spolupráci soupeře."),
}

CUSTOM_BOT_TYPE = "custom"

ALLOWED_BOT_TYPES = list(BUILTIN_BOTS.keys()) + [CUSTOM_BOT_TYPE]


# ---------------------------------------------------------------------------
# Povolené hodnoty konfigurace vlastního bota
# ---------------------------------------------------------------------------

# Klíč -> množina povolených řetězců.
VYCTOVE_PARAMETRY: Dict[str, set] = {
    "prvni_tah": {"C", "D", "random"},
    "zakladni_strategie": {"tit_for_tat", "pavlov", "pravdepodobnost", "opak"},
    "reakce_mlha": {"zradit", "spolupracovat", "random", "opakovat_sebe"},
    "posledni_tah": {"normal", "vzdy_d", "vzdy_c"},
}

# Klíč -> (minimum, maximum, celé číslo?)
CISELNE_PARAMETRY: Dict[str, tuple] = {
    "pravdepodobnost_c": (0.0, 100.0, False),
    "zrada_pri_pomeru": (0.0, 100.0, False),
    "chyba_pct": (0.0, 100.0, False),
    "tolerance_d": (1, 1000, True),
}

LOGICKE_PARAMETRY = {"nikdy_neodpoustet"}

# Klíče, které smí v konfiguraci být navíc: `type` u uložených botů
# a `jmeno` kvůli zpětné kompatibilitě se starším formátem.
POMOCNE_KLICE = {"type", "jmeno"}

POVOLENE_KLICE = (
    set(VYCTOVE_PARAMETRY) | set(CISELNE_PARAMETRY) | LOGICKE_PARAMETRY | POMOCNE_KLICE
)


class UnknownBotTypeError(ValueError):
    pass


class NevalidniKonfiguraceError(ValueError):
    """Konfigurace vlastního bota obsahuje hodnotu, se kterou se nedá hrát."""


def zkontroluj_custom_config(config: Optional[dict]) -> dict:
    """Ověří konfiguraci vlastního bota a vrátí ji doplněnou o výchozí hodnoty.

    Vyhodí `NevalidniKonfiguraceError` s českým vysvětlením, když je něco
    špatně. Nikdy nic tiše neopravuje - špatná hodnota je chyba uživatele,
    ne něco, co by se mělo mlčky přepsat na výchozí.
    """
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise NevalidniKonfiguraceError("Konfigurace bota musí být objekt (JSON slovník).")

    neznamé = sorted(set(config) - POVOLENE_KLICE)
    if neznamé:
        raise NevalidniKonfiguraceError(
            "Konfigurace obsahuje neznámé položky: " + ", ".join(neznamé)
            + ". Povolené jsou: " + ", ".join(sorted(POVOLENE_KLICE - POMOCNE_KLICE)) + "."
        )

    vysledek = dict(bots.DEFAULT_CUSTOM_CONFIG)

    for klic, povolene in VYCTOVE_PARAMETRY.items():
        if klic not in config:
            continue
        hodnota = config[klic]
        if not isinstance(hodnota, str) or hodnota not in povolene:
            raise NevalidniKonfiguraceError(
                f"Položka {klic} musí být jedna z hodnot: " + ", ".join(sorted(povolene))
                + f". Dostal jsem {hodnota!r}."
            )
        vysledek[klic] = hodnota

    for klic, (mini, maxi, celociselny) in CISELNE_PARAMETRY.items():
        if klic not in config:
            continue
        hodnota = config[klic]
        # `bool` je v Pythonu podtypem `int`, ale True jako tolerance nedává smysl.
        if isinstance(hodnota, bool) or not isinstance(hodnota, (int, float)):
            raise NevalidniKonfiguraceError(
                f"Položka {klic} musí být číslo mezi {mini} a {maxi}. Dostal jsem {hodnota!r}."
            )
        if celociselny and not float(hodnota).is_integer():
            raise NevalidniKonfiguraceError(f"Položka {klic} musí být celé číslo.")
        if not (mini <= hodnota <= maxi):
            raise NevalidniKonfiguraceError(
                f"Položka {klic} musí být mezi {mini} a {maxi}. Dostal jsem {hodnota!r}."
            )
        vysledek[klic] = int(hodnota) if celociselny else float(hodnota)

    for klic in LOGICKE_PARAMETRY:
        if klic not in config:
            continue
        hodnota = config[klic]
        if not isinstance(hodnota, bool):
            raise NevalidniKonfiguraceError(
                f"Položka {klic} musí být true nebo false. Dostal jsem {hodnota!r}."
            )
        vysledek[klic] = hodnota

    return vysledek


def zkontroluj_konfiguraci_bota(config: Any) -> dict:
    """Kontrola uložené konfigurace: povinný `type` z whitelistu + parametry.

    Používá se při ukládání bota do databáze, aby se do galerie nedostal bot,
    se kterým pak nejde hrát.
    """
    if not isinstance(config, dict):
        raise NevalidniKonfiguraceError("Konfigurace bota musí být objekt (JSON slovník).")

    bot_type = config.get("type")
    if bot_type not in ALLOWED_BOT_TYPES:
        raise UnknownBotTypeError(
            f"config.type musí být jeden z {ALLOWED_BOT_TYPES}, dostal jsem {bot_type!r}."
        )
    if bot_type == CUSTOM_BOT_TYPE:
        zkontroluj_custom_config(config)
    return config


def resolve_bot(bot_type: str, config: Optional[dict] = None, name: Optional[str] = None) -> Callable:
    """Vrátí čistou funkci bota připravenou k volání jako fn(my_hist, opp_hist, info).

    `bot_type` musí být jeden z ALLOWED_BOT_TYPES - žádný jiný řetězec (natož
    kód) není přípustný, takže uživatel nemůže spustit nic mimo tuto pevnou
    množinu strategií. U vlastního bota se navíc ověří i hodnoty parametrů.
    """
    if bot_type == CUSTOM_BOT_TYPE:
        return partial(bots.custom_player, config=zkontroluj_custom_config(config))

    entry = BUILTIN_BOTS.get(bot_type)
    if entry is None:
        raise UnknownBotTypeError(
            f"Neznámý typ bota: {bot_type!r}. Povolené typy: {ALLOWED_BOT_TYPES}"
        )
    fn, _, _ = entry
    return fn


def bot_display_name(bot_type: str, config: Optional[dict], fallback_name: Optional[str]) -> str:
    if fallback_name:
        return fallback_name
    if bot_type == CUSTOM_BOT_TYPE:
        return (config or {}).get("jmeno") or "Vlastní bot"
    entry = BUILTIN_BOTS.get(bot_type)
    return entry[1] if entry else bot_type


def list_builtin_bots() -> List[dict]:
    return [
        {"type": key, "name": name, "description": desc}
        for key, (_, name, desc) in BUILTIN_BOTS.items()
    ]
