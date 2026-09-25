# The Game Theory - backend (FastAPI)

Backend pro webovou verzi hry "The Game Theory" (iterované vězňovo dilema).
Herní logika je 1:1 přenesená z desktopové aplikace (`mlha_valky_gui2.py`),
databáze je existující Neon Postgres projekt "the-game-theory" - tento
backend jen čte/mapuje existující tabulky, nic v databázi nemění.

## Struktura projektu

```
backend/
  app/
    main.py            # FastAPI aplikace, registrace routerů
    config.py          # čtení nastavení z .env
    db.py              # SQLAlchemy engine/session
    models.py          # SQLAlchemy modely (users, bots, forum_*) - jen mapování
    schemas.py          # Pydantic schémata pro request/response
    game/
      bots.py           # čisté strategie botů (beze změny logiky z originálu)
      simulation.py      # skutecny_pocet_kol, vyhodnot_kolo, odehraj_simulovany_zapas
      registry.py        # pevný seznam povolených typů botů (žádný eval/exec)
    routers/
      health.py          # GET /health
      simulate.py        # POST /simulate/duel, POST /simulate/tournament
      bots.py             # GET /bots
  requirements.txt
  .env                  # DATABASE_URL - NENÍ v gitu (viz .gitignore)
  .env.example          # vzor pro .env
```

## Jak to spustit lokálně

1. Otevři terminál ve složce `backend`:

   ```bash
   cd ~/Documents/game-theory/backend
   ```

2. Aktivuj virtuální prostředí (už je vytvořené a balíčky nainstalované):

   ```bash
   source venv/bin/activate
   ```

3. Spusť server:

   ```bash
   uvicorn app.main:app --reload
   ```

   Uvidíš něco jako `Uvicorn running on http://127.0.0.1:8000`.

4. Otevři v prohlížeči **http://127.0.0.1:8000/docs** - FastAPI tam automaticky
   vygeneruje interaktivní dokumentaci, ve které si můžeš každý endpoint
   rovnou vyzkoušet (tlačítko "Try it out").

## Jak otestovat endpointy z terminálu

```bash
# Health check
curl http://127.0.0.1:8000/health

# Duel dvou vestavěných botů
curl -X POST http://127.0.0.1:8000/simulate/duel \
  -H "Content-Type: application/json" \
  -d '{
        "bot1": {"type": "tit_for_tat"},
        "bot2": {"type": "always_defect"},
        "settings": {"kola": 20, "mlha": 0.05, "zkresleni": 0.02}
      }'

# Duel s vlastním (custom) botem
curl -X POST http://127.0.0.1:8000/simulate/duel \
  -H "Content-Type: application/json" \
  -d '{
        "bot1": {
          "type": "custom",
          "name": "Muj bot",
          "config": {
            "prvni_tah": "C",
            "zakladni_strategie": "tit_for_tat",
            "tolerance_d": 1,
            "reakce_mlha": "zradit"
          }
        },
        "bot2": {"type": "pavlov"},
        "settings": {"kola": 30}
      }'

# Turnaj (round-robin mezi všemi zadanými boty)
curl -X POST http://127.0.0.1:8000/simulate/tournament \
  -H "Content-Type: application/json" \
  -d '{
        "bots": [
          {"type": "tit_for_tat"},
          {"type": "always_cooperate"},
          {"type": "always_defect"},
          {"type": "grudger"}
        ],
        "settings": {"kola": 25}
      }'

# Veřejné boty z databáze (zatím bude vracet prázdný seznam, dokud v tabulce
# `bots` nebude žádný řádek s is_public = true)
curl "http://127.0.0.1:8000/bots?public=true"
```

## Co je otestované a jak

- `GET /health`, `POST /simulate/duel`, `POST /simulate/tournament` - spuštěno
  a ověřeno naživo (server běžel, requesty prošly, včetně chybové odpovědi
  HTTP 400 na neplatný typ bota a testu na dva "custom" boty bez jména v
  jednom turnaji, aby se ověřilo, že jejich skóre nesplyne do jednoho řádku).
- `GET /bots` - SQL dotaz (JOIN `bots` × `users`, filtr `is_public`) byl
  ověřený přímo v Neon konzoli proti reálné databázi a vrací správně
  strukturovaná (v tuto chvíli prázdná - v tabulce `bots` zatím nejsou žádné
  záznamy) data. Živý HTTP request na tento endpoint z tohoto prostředí
  otestovat nešlo - automatizovaný přístup na tento počítač má z bezpečnostních
  důvodů omezenou síť, která nepustí přímé TCP spojení na Postgres port. V
  běžném terminálu na tvém Macu (mimo toto propojení) to ale žádné omezení
  mít nebude - stačí spustit `uvicorn` podle návodu výše a endpoint
  vyzkoušet stejným curl příkazem.

## Bezpečnost vlastních botů

Vlastní bot se vždy skládá jen z pevně daných JSON parametrů
(`app/game/bots.py::CustomBotConfig`) dosazených do jedné předem napsané
funkce `custom_player`. Nikde v backendu se nevolá `eval`/`exec` ani se
nenačítá a nespouští žádný kód dodaný uživatelem - viz `app/game/registry.py`.

## Poznámka k databázi

Modely v `app/models.py` jen popisují existující tabulky (ověřeno přes Neon).
Nikde se nevolá `Base.metadata.create_all()` ani žádná migrace - schéma
databáze zůstává beze změny.

## Novinka: přihlašování a ukládání botů

Přibylo:

- `POST /auth/register` - registrace (username, email, password)
- `POST /auth/login` - přihlášení (username_or_email, password) -> vrátí JWT token
- `GET /auth/me` - info o přihlášeném uživateli (potřebuje token)
- `POST /bots` - uložit vlastního bota pod svůj účet (potřebuje token)
- `GET /bots/mine` - moje boty, veřejné i soukromé (potřebuje token)
- `PATCH /bots/{bot_id}` - upravit svého bota (potřebuje token, jen vlastník)

Přidal jsem dvě nové závislosti (`pyjwt`, `bcrypt`) - po stažení této verze
je potřeba je doinstalovat:

```bash
cd ~/Documents/game-theory/backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Jak vyzkoušet přes /docs

1. Otevři `http://127.0.0.1:8000/docs`.
2. `POST /auth/register` - "Try it out", vyplň username/email/password, Execute.
3. `POST /auth/login` - stejné username + heslo -> v odpovědi dostaneš `access_token`.
4. Nahoře vpravo v `/docs` je tlačítko **Authorize** - vlož tam token (bez
   uvozovek) a potvrď. Od teď `/docs` posílá token automaticky ke všem
   zamčeným endpointům.
5. `POST /bots` - vytvoř si bota, např.:
   ```json
   {
     "name": "Muj Tit-for-Tat",
     "is_public": true,
     "config": {"type": "tit_for_tat"}
   }
   ```
   nebo vlastní bot:
   ```json
   {
     "name": "Muj vlastni bot",
     "is_public": true,
     "config": {
       "type": "custom",
       "prvni_tah": "C",
       "zakladni_strategie": "tit_for_tat",
       "tolerance_d": 1
     }
   }
   ```
6. `GET /bots?public=true` - teď už uvidíš svého bota (pokud jsi dal `is_public: true`).
7. `GET /bots/mine` - uvidíš úplně všechny své boty, i soukromé.

### Bezpečnost

Hesla se ukládají jen jako bcrypt hash, nikdy v čitelné podobě. JWT token
nese jen ID uživatele a datum vypršení (výchozí platnost 24 hodin) - server
si tokeny nikde neukládá. `config.type` uloženého bota musí být jeden
z pevně povolených typů (stejná bezpečnostní zásada jako u `/simulate` -
žádný kód dodaný uživatelem se nikde nespouští).

Tuhle novou část jsem důkladně otestoval (registrace, duplicity, špatné
heslo, chybějící/neplatný token, cizí bot -> 403, neexistující bot -> 404,
verze konfigurace se zvyšuje jen při změně `config`) v izolovaném testovacím
prostředí mimo tvůj Mac - přes 30 automatických kontrol prošlo bez chyby.
SQL dotazy jsem navíc ověřil přesně proti struktuře tvé Neon databáze.
