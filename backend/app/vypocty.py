"""Velké simulace běží v odděleném procesu s časovým limitem.

Proč: stránku i API obsluhuje jeden proces na malém stroji (free instance
Renderu má desetinu procesoru). Kdyby velký turnaj nebo evoluce běžely přímo
v něm, zpomalily by všechno ostatní - načtení stránky, přihlášení i health
check, podle kterého Render pozná, že aplikace žije. V odděleném procesu se
o procesor dělí férově a výpočet, který trvá příliš dlouho, se dá ukončit.

Současně běží nejvýš jedna velká simulace; další čeká chvíli ve frontě a pak
dostane odpověď "server je zaneprázdněný". Malé simulace (příběh, běžný duel)
se počítají rovnou, protože spuštění procesu by trvalo déle než ony.

Proces se startuje přes "forkserver": jednovláknový pomocný proces, který
má herní moduly už načtené a jen se rozdvojí. Je to rychlé a bezpečné i ve
vícevláknovém serveru (obyčejný fork z vlákna serveru by mohl zdědit
zamčený zámek).
"""

from __future__ import annotations

import multiprocessing as mp
import threading
from typing import Any, Callable

_PRELOAD = ["app.game.simulation", "app.game.evolution", "app.game.turnaj", "app.game.rules", "app.game.bots"]

if "forkserver" in mp.get_all_start_methods():
    _ctx = mp.get_context("forkserver")
    _ctx.set_forkserver_preload(_PRELOAD)
else:  # Windows
    _ctx = mp.get_context("spawn")

_jedna_naraz = threading.BoundedSemaphore(1)


class Zaneprazdneno(Exception):
    """Právě běží jiná velká simulace."""


class PrilisDlouho(Exception):
    """Simulace nestihla časový limit a byla ukončena."""


def _pracant(spojeni, fn, args, kwargs) -> None:
    try:
        spojeni.send(("ok", fn(*args, **kwargs)))
    except BaseException as exc:  # noqa: BLE001 - chybu předáme rodiči jako text
        spojeni.send(("chyba", f"{type(exc).__name__}: {exc}"))
    finally:
        spojeni.close()


def spust_oddelene(fn: Callable, *args: Any, casovy_limit: float, cekani: float = 20.0, **kwargs: Any) -> Any:
    """Zavolá `fn(*args, **kwargs)` v odděleném procesu a vrátí výsledek.

    `fn` musí být funkce na úrovni modulu a argumenty i výsledek se musí dát
    předat mezi procesy (pickle) - boti z registry to splňují.
    """
    if not _jedna_naraz.acquire(timeout=cekani):
        raise Zaneprazdneno
    try:
        prijem, odesilani = _ctx.Pipe(duplex=False)
        proces = _ctx.Process(target=_pracant, args=(odesilani, fn, args, kwargs), daemon=True)
        proces.start()
        odesilani.close()
        try:
            if not prijem.poll(casovy_limit):
                proces.terminate()
                proces.join(2)
                raise PrilisDlouho
            try:
                stav, vysledek = prijem.recv()
            except EOFError:
                raise RuntimeError("The simulation process ended unexpectedly.") from None
        finally:
            prijem.close()
            proces.join(2)
            if proces.is_alive():
                proces.kill()
        if stav != "ok":
            raise RuntimeError(vysledek)
        return vysledek
    finally:
        _jedna_naraz.release()
