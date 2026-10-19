"""Konfigurace aplikace - načítá se z prostředí / souboru .env.

Citlivé hodnoty (connection string, JWT tajný klíč) se NIKDY nepíší natvrdo
do kódu - vždy se čtou z proměnných prostředí (viz .env / .env.example).
Na Renderu žádný soubor .env není a hodnoty přicházejí rovnou z prostředí;
pydantic-settings to zvládne obojí bez úpravy.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    app_name: str = "The Game Theory API"

    # Frontend servíruje ta samá aplikace, takže požadavky chodí ze stejné
    # adresy a CORS není potřeba - proto prázdný seznam. Nastav jen tehdy,
    # když frontend poběží jinde (např. při vývoji na jiném portu):
    #   CORS_ORIGINS='["http://localhost:5500"]'
    cors_origins: list[str] = []

    # Auth / JWT
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 den
    # "Stay logged in" - prohlížeč si token uloží a server ho vydá na delší dobu.
    remember_token_days: int = 30

    # Strop na velikost jedné simulace, měřeno v odehraných kolech
    # (dvojice x kola x opakování, u evoluce x generace). Chrání server před
    # tím, aby jediný požadavek vytížil procesor na několik minut - na malé
    # instanci by to položilo celou stránku všem ostatním.
    max_simulation_rounds: int = 3_000_000

    # Jak dlouho smí běžet jedna velká simulace v odděleném procesu, než se
    # ukončí (viz app/vypocty.py). Hlídá to i případ, kdy by odhad v kolech
    # podcenil skutečnou náročnost.
    simulation_timeout_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()
