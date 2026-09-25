# The Game Theory

Iterované vězňovo dilema s mlhou války, šumem, turnaji a evoluční dynamikou.
Webová verze desktopové hry napsané v Pythonu a Tkinteru.

## Co to umí

- **Duel** — dva boti, nastavitelná mlha, šum a počet kol, průběh kolo po kole.
- **Turnaj** — každý s každým, s opakováním a rozpětím výsledků.
- **Evoluce** — replikátorová dynamika populace 1000 jedinců.
- **Vlastní boti** — strategie se skládá z nastavení, ne z kódu; dá se uložit
  a zveřejnit v galerii.

## Struktura

```
backend/    FastAPI + SQLAlchemy; servíruje i frontend
  app/game/ čistá herní logika přenesená z desktopové verze
frontend/   jeden soubor index.html, žádný build
```

## Vývoj

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # doplň DATABASE_URL a SECRET_KEY
uvicorn app.main:app --reload
```

Aplikace pak běží na http://127.0.0.1:8000, dokumentace API na `/docs`.

## Nasazení

Viz `render.yaml`. Potřebné proměnné prostředí:

| Proměnná | K čemu |
|---|---|
| `DATABASE_URL` | connection string k PostgreSQL (Neon) |
| `SECRET_KEY` | klíč na podepisování přihlašovacích tokenů |
| `CORS_ORIGINS` | jen když frontend běží jinde než backend |
| `MAX_SIMULATION_ROUNDS` | strop na velikost jedné simulace (výchozí 3 000 000) |

Databázové schéma se z aplikace nevytváří ani nemění — tabulky `users`,
`bots`, `forum_categories`, `forum_threads` a `forum_posts` musí existovat.

## Bezpečnost

Vlastní bot je vždycky jen sada povolených hodnot dosazená do pevně napsané
funkce. Nikde se nevolá `eval` ani `exec` a nespouští se žádný kód od
uživatelů. Hesla se ukládají jako bcrypt hash.
