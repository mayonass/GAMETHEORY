"""FastAPI aplikace - vstupní bod."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routers import auth, bots, health, play, simulate

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.middleware("http")
async def stranka_vzdy_cerstva(request: Request, call_next):
    """Prohlížeč si stránku smí uložit, ale před použitím se musí zeptat,
    jestli se nezměnila (no-cache = ověř si to; odpověď je pak levné 304).
    Bez toho prohlížeče stránku bez hlavičky Cache-Control drží podle
    vlastního odhadu klidně celé hodiny a nová verze webu se neukáže."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.endswith(".html"):
        response.headers["Cache-Control"] = "no-cache"
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(simulate.router)
app.include_router(bots.router)
app.include_router(play.router)

# Frontend servírujeme z téhle samé aplikace, takže stačí jeden spuštěný
# příkaz a jedna adresa (http://127.0.0.1:8000). Mount musí být AŽ ZA
# routery - zabírá kořenovou cestu "/" a chytal by jinak i /health a spol.
# Když složka frontend/ neexistuje (třeba na serveru, kde běží jen API),
# nic se nemountuje a API funguje dál.
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
