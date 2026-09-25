import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
import random

# ==========================================
# 1. PŘEKLADY A LOKALIZACE (i18n)
# ==========================================
CURRENT_LANG = "cz"

TRANSLATIONS = {
    "cz": {
        "app_title": "The Game Theory",
        "app_subtitle": "Teorie her, iterované vězňovo dilema a evoluční dynamika v zašuměném prostředí",
        "menu_human": "Hrát proti botovi",
        "menu_pvp": "Hrát proti člověku (PvP na 1 PC)",
        "menu_duel": "Sledovat souboj botů",
        "menu_tour": "Statický turnaj botů",
        "menu_evo": "Evoluční simulace (Ekologie)",
        "menu_custom": "Navrhnout vlastního bota",
        "menu_desc": "Přečíst si profily botů",
        "btn_lang": "🇬🇧 Switch to English",

        "mode_human": "Člověk vs Bot",
        "mode_pvp": "Hráč vs Hráč",
        "mode_duel": "Souboj botů",
        "mode_tour": "Statický turnaj",
        "mode_evo": "Evoluční dynamika",
        "mode_desc": "Profily a chování botů",

        "set_opp": "Vyber soupeře:",
        "set_p1": "Hráč 1:",
        "set_p2": "Hráč 2:",
        "set_b1": "Bot 1:",
        "set_b2": "Bot 2:",
        "set_gen": "Počet generací (vývoj v čase):",
        "set_pop": "Počáteční populace:",
        "set_mut": "Šance na mutaci v generaci:",
        "set_rounds": "Počet kol (v jednom setkání):",
        "set_unknown_r": "Skrýt počet kol (Náhodný konec eliminuje kalkul posledního tahu)",
        "set_fog": "Šance na MLHU (Zpoždění info):",
        "set_delay": "Odhalení mlhy po (kol):",
        "set_noise": "Šance na ZKRESLENÍ (Chyba vnímání):",
        "set_bots": "Zúčastnění boti:",

        "btn_back": "Zpět",
        "btn_start": "Spustit",
        "btn_save": "Uložit konfiguraci",
        "btn_sel_bots": "Vybrat boty ▼",
        "btn_hide_bots": "Skrýt výběr botů ▲",
        "btn_menu": "Odejít do menu",

        "err_min_bots": "Pro turnaj/evoluci musíš vybrat alespoň 2 boty!",
        "pop_even": "Vyrovnané",
        "pop_rand": "Náhodné",
        "pop_man": "Manuální",
        "weight": "(váha):",

        "bot_all_c": "Vždy spolupracuj",
        "bot_all_d": "Vždy zraď",
        "bot_tft": "Půjčka za oplátku",
        "bot_grudger": "Záštník",
        "bot_pavlov": "Pavlov",
        "bot_zde": "ZD Vyděrač",
        "bot_zdg": "ZD Štědrý",
        "bot_custom_def": "Bezejmenný",

        "cb_title": "Pokročilý návrh vlastního bota",
        "cb_sub": "Sestav si chování na míru pomocí prioritních pravidel.",
        "cb_name": "Jméno bota:",
        "cb_first": "První tah v zápase:",
        "cb_base_strat": "Základní strategie:",
        "cb_prob_c": "Pravděpodobnost spolupráce (pokud je zvolena výše):",
        "cb_tol": "Tolerance (Odpustit N zrad za sebou, než začnu oplácet):",
        "cb_ratio": "Limit chamtivosti (Zradit vždy, pokud soupeř zrazuje ve více než X % případů):",
        "cb_fog": "Při mlze (neznámý tah oponenta):",
        "cb_last": "V posledním kole zápasu:",
        "cb_grudge": "Nikdy neodpouštět (Grudger mód - jedna zrada znamená věčnou zradu)",
        "cb_tremble": "Šance na chybu PROVEDENÍ (Trembling hand v %):",
        "cb_saved": "Konfigurace úspěšně uložena a připravena do turnajů.",

        "opt_c": "Spolupracuj",
        "opt_d": "Zraď",
        "opt_random": "Náhodně (50/50)",
        "opt_tit_for_tat": "Půjčka za oplátku (Tit-for-Tat)",
        "opt_pavlov": "Pavlov (Výhra = Zopakuj tah, Prohra = Změň tah)",
        "opt_pravdepodobnost": "Házet kostkou (Pravděpodobnost)",
        "opt_opak": "Dělej pravý opak soupeře",
        "opt_zradit": "Zraď (opatrnost)",
        "opt_spolupracovat": "Spolupracuj (důvěra)",
        "opt_opakovat_sebe": "Zopakuj svůj poslední tah",
        "opt_normal": "Zachovat normální logiku",
        "opt_vzdy_c": "Vždy spolupracuj",
        "opt_vzdy_d": "Vždy zraď",

        "match_run": "Probíhá zápas",
        "match_info": "Zkreslení: {0}% • Mlha: {1}%",
        "match_round": "Kolo {0} / {1}",
        "btn_coop": "Spolupracuj",
        "btn_def": "Zraď",
        "status_hidden": "Zadáno (Skryto)",
        "log_init": "--- Zápas inicializován ---\n",
        "log_perc": "(vnímáno {0}) ",
        "log_end": "\n--- KONEC: {0} ---\n",
        "win": "Vyhrává {0}!",
        "tie": "Remíza.",

        "tour_score": "Skóre",
        "tour_w": "V",
        "tour_t": "R",
        "tour_l": "P",
        "evo_title": "Evoluční dynamika s mutacemi",
        "evo_gen": "Generace: {0} / {1}",
        "evo_done": "HOTOVO",
        "evo_pop": "Zastoupení populací",
        "evo_final": "Konečné pořadí",

        "desc_all_c": "Vždy spolupracuje, bez ohledu na to, co dělá soupeř. Slouží jako ztělesnění naivity, které je často zneužito predátory, ale ve světě plném jiných altruistů dokáže získat maximální body.",
        "desc_all_d": "Vždy zradí. Snaží se maximalizovat svůj zisk na úkor ostatních. V evoluci často rychle vyhubí altruisty, ale jakmile zbudou jen samí zrádci, celá populace začne tratit.",
        "desc_tft": "Začne spoluprací, poté přesně opakuje poslední viditelný tah soupeře. Je to robustní, přátelská, ale tvrdá strategie. Její největší slabinou je prostředí se šumem, kde může spustit nekonečnou 'spirálu odplaty'.",
        "desc_grudger": "Začíná mírumilovně a spolupracuje. Pokud ho ale soupeř byť jen jednou jedinkrát zradí, Grudger nezapomíná a až do konce zápasu bude už jen zrazovat.",
        "desc_pavlov": "Drží se strategie 'Když vyhráváš, neměň to. Když prohráváš, změň to.' Pokud v minulém kole on i soupeř udělali totéž (C-C nebo D-D), spolupracuje. Pokud se rozešli (C-D nebo D-C), zradí. Dobře se vyrovnává s náhodným šumem.",
        "desc_zde": "Zero-Determinant Extortioner. Pomocí komplexní pravděpodobnostní matice reaguje tak, aby matematicky garantoval, že jeho skóre bude vždy vyšší než skóre soupeře. Vynucuje si nespravedlivý podíl na zisku.",
        "desc_zdg": "Zero-Determinant Generous. Podobná matematika jako Vyděrač, ale používá ji k opaku: systematicky odměňuje spolupráci a dovoluje soupeři získat více bodů než on sám, čímž motivuje oponenty k neustálé spolupráci.",
        "desc_custom": "Toto je bot definovaný hráčem. Jeho pravidla reagují na vlastní nastavení v editoru."
    },
    "en": {
        "app_title": "The Game Theory",
        "app_subtitle": "Game theory, Iterated Prisoner's Dilemma, and Evolutionary Dynamics in noisy environments",
        "menu_human": "Play against bot",
        "menu_pvp": "Play against human (Local PvP)",
        "menu_duel": "Watch bot duel",
        "menu_tour": "Static bot tournament",
        "menu_evo": "Evolutionary simulation (Ecology)",
        "menu_custom": "Design custom bot",
        "menu_desc": "Read bot profiles",
        "btn_lang": "🇨🇿 Přepnout do češtiny",

        "mode_human": "Human vs Bot",
        "mode_pvp": "Player vs Player",
        "mode_duel": "Bot Duel",
        "mode_tour": "Static Tournament",
        "mode_evo": "Evolutionary Dynamics",
        "mode_desc": "Bot Profiles and Behavior",

        "set_opp": "Select opponent:",
        "set_p1": "Player 1:",
        "set_p2": "Player 2:",
        "set_b1": "Bot 1:",
        "set_b2": "Bot 2:",
        "set_gen": "Generations (evolution over time):",
        "set_pop": "Initial population:",
        "set_mut": "Mutation chance per generation:",
        "set_rounds": "Rounds (per encounter):",
        "set_unknown_r": "Hide rounds (Random end to eliminate last-round calculus)",
        "set_fog": "FOG chance (Information delay):",
        "set_delay": "Fog clears after (rounds):",
        "set_noise": "NOISE chance (Perception error):",
        "set_bots": "Participating bots:",

        "btn_back": "Back",
        "btn_start": "Start",
        "btn_save": "Save configuration",
        "btn_sel_bots": "Select bots ▼",
        "btn_hide_bots": "Hide bot selection ▲",
        "btn_menu": "Return to menu",

        "err_min_bots": "You must select at least 2 bots for tournament/evolution!",
        "pop_even": "Even",
        "pop_rand": "Random",
        "pop_man": "Manual",
        "weight": "(weight):",

        "bot_all_c": "Always Cooperate",
        "bot_all_d": "Always Defect",
        "bot_tft": "Tit-for-Tat",
        "bot_grudger": "Grudger",
        "bot_pavlov": "Pavlov",
        "bot_zde": "ZD Extortioner",
        "bot_zdg": "ZD Generous",
        "bot_custom_def": "Nameless",

        "cb_title": "Advanced Custom Bot Design",
        "cb_sub": "Build custom behavior using priority rules.",
        "cb_name": "Bot name:",
        "cb_first": "First move in match:",
        "cb_base_strat": "Base strategy:",
        "cb_prob_c": "Probability of cooperation (if chosen above):",
        "cb_tol": "Tolerance (Forgive N consecutive defects before retaliating):",
        "cb_ratio": "Greed limit (Always defect if opponent defect ratio > X %):",
        "cb_fog": "In fog (unknown move):",
        "cb_last": "In the last round:",
        "cb_grudge": "Never forgive (Grudger mode - one defect triggers eternal defection)",
        "cb_tremble": "EXECUTION error chance (Trembling hand %):",
        "cb_saved": "Configuration successfully saved and ready for tournaments.",

        "opt_c": "Cooperate",
        "opt_d": "Defect",
        "opt_random": "Random (50/50)",
        "opt_tit_for_tat": "Tit-for-Tat",
        "opt_pavlov": "Pavlov (Win = Repeat, Lose = Switch)",
        "opt_pravdepodobnost": "Roll dice (Probability)",
        "opt_opak": "Do the exact opposite",
        "opt_zradit": "Defect (caution)",
        "opt_spolupracovat": "Cooperate (trust)",
        "opt_opakovat_sebe": "Repeat your own last move",
        "opt_normal": "Keep normal logic",
        "opt_vzdy_c": "Always cooperate",
        "opt_vzdy_d": "Always defect",

        "match_run": "Match in progress",
        "match_info": "Noise: {0}% • Fog: {1}%",
        "match_round": "Round {0} / {1}",
        "btn_coop": "Cooperate",
        "btn_def": "Defect",
        "status_hidden": "Entered (Hidden)",
        "log_init": "--- Match initialized ---\n",
        "log_perc": "(perceived {0}) ",
        "log_end": "\n--- END: {0} ---\n",
        "win": "{0} wins!",
        "tie": "Tie.",

        "tour_score": "Score",
        "tour_w": "W",
        "tour_t": "T",
        "tour_l": "L",
        "evo_title": "Evolutionary Dynamics with Mutations",
        "evo_gen": "Generation: {0} / {1}",
        "evo_done": "DONE",
        "evo_pop": "Population Distribution",
        "evo_final": "Final ranking",

        "desc_all_c": "Always cooperates, regardless of what the opponent does. Serves as the embodiment of naivety, often exploited by predators, but thrives in a world full of other altruists.",
        "desc_all_d": "Always defects. Tries to maximize its gain at the expense of others. In evolution, it quickly wipes out altruists, but once only defectors remain, the entire population suffers.",
        "desc_tft": "Starts by cooperating, then exactly repeats the opponent's last visible move. It is a robust, friendly, but tough strategy. Its biggest weakness is a noisy environment where it can trigger a 'death spiral' of retaliation.",
        "desc_grudger": "Starts peacefully and cooperates. But if the opponent defects even once, the Grudger never forgets and will defect forever.",
        "desc_pavlov": "Follows the 'Win-Stay, Lose-Shift' strategy. If both players made the same move last round (C-C or D-D), it cooperates. If they diverged (C-D or D-C), it defects. Handles random noise well.",
        "desc_zde": "Zero-Determinant Extortioner. Uses a complex probability matrix to mathematically guarantee that its score will always be higher than the opponent's. It forces an unfair share of the payoff.",
        "desc_zdg": "Zero-Determinant Generous. Uses similar math to the Extortioner, but to the opposite effect: it systematically rewards cooperation and allows the opponent to score higher than itself, motivating continuous cooperation.",
        "desc_custom": "This is a player-defined bot. Its rules react to the custom settings in the editor."
    }
}


def t(key, *args):
    text = TRANSLATIONS.get(CURRENT_LANG, TRANSLATIONS["en"]).get(key, key)
    if args:
        return text.format(*args)
    return text


KEYS_PRVNI = ["C", "D", "random"]
KEYS_STRATEGIE = ["tit_for_tat", "pavlov", "pravdepodobnost", "opak"]
KEYS_MLHA = ["zradit", "spolupracovat", "random", "opakovat_sebe"]
KEYS_POSLEDNI = ["normal", "vzdy_d", "vzdy_c"]

VLASTNI_NASTAVENI = {
    "jmeno": "Custom Bot",
    "prvni_tah": "C",
    "zakladni_strategie": "tit_for_tat",
    "pravdepodobnost_c": 100,
    "tolerance_d": 1,
    "zrada_pri_pomeru": 100,
    "reakce_mlha": "zradit",
    "posledni_tah": "normal",
    "nikdy_neodpoustet": False,
    "chyba_pct": 0,
}

# ==========================================
# 2. BOTI A JEJICH LOGIKA
#
# Všechny strategie sdílí stejný podpis:
#   funkce(moje_historie, souperova_historie, info) -> 'C' nebo 'D'
# `info` obsahuje "kolo" (index aktuálního kola od 0) a "celkem_kol"
# (celkový počet kol, nebo None, pokud je počet kol v zápase neznámý).
# ==========================================

def always_cooperate(my_hist, opp_hist, info):
    return 'C'


def always_defect(my_hist, opp_hist, info):
    return 'D'


def tit_for_tat(my_hist, opp_hist, info):
    for tah in reversed(opp_hist):
        if tah != '?':
            return tah
    return 'C'


def grudger(my_hist, opp_hist, info):
    if 'D' in opp_hist:
        return 'D'
    return 'C'


def pavlov(my_hist, opp_hist, info):
    if not my_hist:
        return 'C'
    if opp_hist[-1] == '?':
        return my_hist[-1]
    my_last, opp_last = my_hist[-1], opp_hist[-1]
    if (my_last == 'C' and opp_last == 'C') or (my_last == 'D' and opp_last == 'C'):
        return my_last
    return 'C' if my_last == 'D' else 'D'


def zd_extortioner(my_hist, opp_hist, info):
    if not my_hist or opp_hist[-1] == '?':
        return 'C'
    my_last, opp_last = my_hist[-1], opp_hist[-1]
    if my_last == 'C' and opp_last == 'C':
        p = 0.85
    elif my_last == 'C' and opp_last == 'D':
        p = 0.50
    elif my_last == 'D' and opp_last == 'C':
        p = 0.27
    else:
        p = 0.0
    return 'C' if random.random() < p else 'D'


def zd_generous(my_hist, opp_hist, info):
    if not my_hist or opp_hist[-1] == '?':
        return 'C'
    my_last, opp_last = my_hist[-1], opp_hist[-1]
    if my_last == 'C' and opp_last == 'C':
        p = 1.00
    elif my_last == 'C' and opp_last == 'D':
        p = 0.18
    elif my_last == 'D' and opp_last == 'C':
        p = 0.54
    else:
        p = 0.13
    return 'C' if random.random() < p else 'D'


def custom_player(my_hist, opp_hist, info):
    n = VLASTNI_NASTAVENI

    def aplikuj_chybu(tah):
        if n["chyba_pct"] > 0 and random.random() * 100 < n["chyba_pct"]:
            return 'D' if tah == 'C' else 'C'
        return tah

    if info["celkem_kol"] is not None and info["kolo"] == info["celkem_kol"] - 1:
        if n["posledni_tah"] == "vzdy_c":
            return aplikuj_chybu('C')
        elif n["posledni_tah"] == "vzdy_d":
            return aplikuj_chybu('D')

    if n["nikdy_neodpoustet"] and 'D' in [x for x in opp_hist if x != '?']:
        return aplikuj_chybu('D')

    if not opp_hist:
        prvni = n["prvni_tah"]
        if prvni == "random":
            return aplikuj_chybu('C' if random.random() < 0.5 else 'D')
        return aplikuj_chybu(prvni)

    viditelna_historie = [x for x in opp_hist if x != '?']

    if len(viditelna_historie) >= 5:
        opp_d_count = sum(1 for x in viditelna_historie if x == 'D')
        d_ratio = (opp_d_count / len(viditelna_historie)) * 100
        if d_ratio >= n["zrada_pri_pomeru"]:
            return aplikuj_chybu('D')

    # Tolerance k po sobě jdoucím zradám: tolerance_d = kolik zrad v řadě
    # bot odpustí, než začne oplácet (retaliace nastává až při tolerance_d + 1).
    limit = n["tolerance_d"] + 1
    if len(viditelna_historie) >= limit:
        if all(x == 'D' for x in viditelna_historie[-limit:]):
            return aplikuj_chybu('D')

    if opp_hist[-1] == '?':
        reakce = n["reakce_mlha"]
        if reakce == "zradit":
            return aplikuj_chybu('D')
        elif reakce == "spolupracovat":
            return aplikuj_chybu('C')
        elif reakce == "random":
            return aplikuj_chybu('C' if random.random() < 0.5 else 'D')
        else:
            return aplikuj_chybu(my_hist[-1] if my_hist else 'C')

    posledni = opp_hist[-1]
    strategie = n["zakladni_strategie"]
    if strategie == "tit_for_tat":
        tah = posledni
    elif strategie == "pavlov":
        ml = my_hist[-1]
        if (ml == 'C' and posledni == 'C') or (ml == 'D' and posledni == 'C'):
            tah = ml
        else:
            tah = 'C' if ml == 'D' else 'D'
    elif strategie == "opak":
        tah = 'D' if posledni == 'C' else 'C'
    elif strategie == "pravdepodobnost":
        tah = 'C' if random.random() * 100 < n["pravdepodobnost_c"] else 'D'
    else:
        tah = 'C'

    return aplikuj_chybu(tah)


def get_boti():
    return [
        (t("bot_all_c"), always_cooperate, t("desc_all_c")),
        (t("bot_all_d"), always_defect, t("desc_all_d")),
        (t("bot_tft"), tit_for_tat, t("desc_tft")),
        (t("bot_grudger"), grudger, t("desc_grudger")),
        (t("bot_pavlov"), pavlov, t("desc_pavlov")),
        (t("bot_zde"), zd_extortioner, t("desc_zde")),
        (t("bot_zdg"), zd_generous, t("desc_zdg")),
        (VLASTNI_NASTAVENI["jmeno"], custom_player, t("desc_custom")),
    ]


BOT_COLORS = ["#10b981", "#ef4444", "#3b82f6", "#f59e0b", "#8b5cf6", "#f43f5e", "#14b8a6", "#06b6d4"]
PAYOFFS = {('C', 'C'): (3, 3), ('D', 'D'): (1, 1), ('D', 'C'): (5, 0), ('C', 'D'): (0, 5)}


# ==========================================
# 3. ČISTÁ HERNÍ LOGIKA (žádná závislost na tkinteru)
#
# Tyto funkce se dají otestovat samostatně, bez GUI. Používá je jak
# interaktivní zápas, tak turnaj a evoluce - pravidla hry jsou tedy
# definovaná přesně na jednom místě.
# ==========================================

@dataclass
class NastaveniZapasu:
    """Sdílené nastavení jednoho zápasu / jednoho střetnutí v simulaci."""
    kola: int
    neznama_kola: bool
    mlha: float
    delay: int
    zkresleni: float


def skutecny_pocet_kol(cfg: NastaveniZapasu) -> int:
    """Reálný počet kol zápasu. Při neznámém počtu kol je náhodný, ale vždy >= 1."""
    if not cfg.neznama_kola:
        return max(1, cfg.kola)
    rozptyl = max(1, int(cfg.kola * 0.3))
    return max(1, random.randint(cfg.kola - rozptyl, cfg.kola + rozptyl))


def spocitej_viditelnou_historii(vnimana_historie, fog, aktualni_kolo, delay):
    """Z historie (může už být zkreslená šumem) odstraní tahy skryté mlhou."""
    vysledek = []
    for i, tah in enumerate(vnimana_historie):
        if fog[i] and (aktualni_kolo - i) <= delay:
            vysledek.append('?')
        else:
            vysledek.append(tah)
    return vysledek


def vyhodnot_kolo(tah1, tah2, zkresleni, mlha):
    """Spočítá výsledek jednoho kola: co soupeři VNÍMAJÍ (šum), body a novou mlhu."""
    p1 = ('D' if tah1 == 'C' else 'C') if (random.random() < zkresleni) else tah1
    p2 = ('D' if tah2 == 'C' else 'C') if (random.random() < zkresleni) else tah2
    b1, b2 = PAYOFFS[(tah1, tah2)]
    nova_mlha1 = random.random() < mlha
    nova_mlha2 = random.random() < mlha
    return p1, p2, b1, b2, nova_mlha1, nova_mlha2


def odehraj_simulovany_zapas(f1, f2, cfg: NastaveniZapasu):
    """Odehraje jeden neinteraktivní zápas mezi dvěma boty a vrátí (skóre1, skóre2)."""
    kola = skutecny_pocet_kol(cfg)
    info = {"celkem_kol": None if cfg.neznama_kola else kola}
    true1, true2, perc1, perc2, fog1, fog2 = [], [], [], [], [], []
    s1, s2 = 0, 0

    for kolo in range(kola):
        info["kolo"] = kolo
        v1 = spocitej_viditelnou_historii(perc1, fog1, kolo, cfg.delay)
        v2 = spocitej_viditelnou_historii(perc2, fog2, kolo, cfg.delay)

        tah1 = f1(true1, v2, info)
        tah2 = f2(true2, v1, info)

        p1, p2, b1, b2, f1_bool, f2_bool = vyhodnot_kolo(tah1, tah2, cfg.zkresleni, cfg.mlha)
        s1 += b1
        s2 += b2

        true1.append(tah1)
        true2.append(tah2)
        perc1.append(p1)
        perc2.append(p2)
        fog1.append(f1_bool)
        fog2.append(f2_bool)

    return s1, s2


def _log_pripoj(widget, text, tag=None):
    """Připojí text na konec tk.Text logu (chráněno proti zápisu do smazaného widgetu)."""
    if not widget.winfo_exists():
        return
    widget.configure(state="normal")
    if tag:
        widget.insert("end", text, tag)
    else:
        widget.insert("end", text)
    widget.see("end")
    widget.configure(state="disabled")


# ==========================================
# 4. DESIGN A JÁDRO APLIKACE
# ==========================================
BG = "#09090b"
PANEL = "#18181b"
TEXT = "#fafafa"
MUTED = "#a1a1aa"
ACCENT = "#3b82f6"
ACCENT_HOVER = "#2563eb"
GREEN = "#10b981"
GREEN_HOVER = "#059669"
RED = "#ef4444"
RED_HOVER = "#dc2626"
BORDER = "#27272a"


class MlhaValkyApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1100x820")
        self.root.minsize(950, 750)
        self.root.configure(bg=BG)
        self.style = ttk.Style(root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self._nastav_styl()
        self.show_hlavni_menu()

    def _nastav_styl(self):
        s = self.style
        s.configure("TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        font_main = ("Helvetica", 12)
        font_title = ("Helvetica", 28, "bold")
        font_subtitle = ("Helvetica", 12)
        font_score = ("Helvetica", 36, "bold")

        s.configure("TLabel", background=BG, foreground=TEXT, font=font_main)
        s.configure("Nadpis.TLabel", background=BG, foreground=TEXT, font=font_title)
        s.configure("Podnadpis.TLabel", background=BG, foreground=MUTED, font=font_subtitle)
        s.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=font_main)
        s.configure("Skore.TLabel", background=PANEL, foreground=TEXT, font=font_score)
        s.configure("Error.TLabel", background=BG, foreground=RED, font=("Helvetica", 12, "bold"))

        s.configure("TButton", font=("Helvetica", 12, "bold"), padding=12,
                    background=PANEL, foreground=TEXT, borderwidth=0, focuscolor=BG)
        s.map("TButton", background=[("active", BORDER)])
        s.configure("Accent.TButton", background=ACCENT, foreground="white")
        s.map("Accent.TButton", background=[("active", ACCENT_HOVER)])
        s.configure("Zelena.TButton", background=GREEN, foreground="white")
        s.map("Zelena.TButton", background=[("active", GREEN_HOVER)])
        s.configure("Cervena.TButton", background=RED, foreground="white")
        s.map("Cervena.TButton", background=[("active", RED_HOVER)])

        s.configure("TCombobox", padding=8, font=font_main)
        s.configure("TCheckbutton", background=PANEL, foreground=TEXT, font=font_main)
        s.map("TCheckbutton", background=[("active", PANEL)], indicatorcolor=[("selected", ACCENT)])
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT,
                    rowheight=32, font=font_main, borderwidth=0)
        s.configure("Treeview.Heading", font=("Helvetica", 12, "bold"), background=BG, foreground=TEXT)

        self.root.option_add("*TButton.cursor", "hand2")

    def _vycistit(self):
        self.ukonceno = True
        self.root.title(t("app_title"))
        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")
        for w in self.root.winfo_children():
            w.destroy()

    def _vytvor_scrollable_ramec(self):
        self._vycistit()
        self.ukonceno = False
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(main_frame, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style="TFrame")
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", tags="frame")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("frame", width=e.width))
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            if event.delta:
                kroky = int(-1 * (event.delta / 120)) if abs(event.delta) >= 120 else int(-1 * event.delta)
                canvas.yview_scroll(kroky, "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        return scrollable_frame

    def _toggle_lang(self):
        global CURRENT_LANG
        CURRENT_LANG = "en" if CURRENT_LANG == "cz" else "cz"
        self.show_hlavni_menu()

    def _vytvor_posuvnik(self, form, radek, text, var, max_val, is_float=False, nasobic=1):
        ttk.Label(form, text=text, style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=10)
        wrap = ttk.Frame(form, style="Panel.TFrame")
        wrap.grid(row=radek, column=1, sticky="w", pady=10, padx=15)
        lbl = ttk.Label(wrap, style="Panel.TLabel", width=8)

        def update_lbl(val=None):
            v = var.get() * nasobic
            lbl.configure(text=f"{v:.1f} %" if is_float else f"{int(v)} %")

        update_lbl()
        ttk.Scale(wrap, from_=0, to=max_val, variable=var, orient="horizontal", length=200,
                 command=update_lbl).pack(side="left")
        lbl.pack(side="left", padx=10)
        return radek + 1

    def _vytvor_skore_panel(self, parent, jmeno, padx):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=20)
        panel.pack(side="left", expand=True, fill="both", padx=padx)
        ttk.Label(panel, text=jmeno.upper(), style="Panel.TLabel", foreground=MUTED).pack()
        lbl = ttk.Label(panel, text="0", style="Skore.TLabel")
        lbl.pack(pady=10)
        return lbl

    def show_hlavni_menu(self):
        self._vycistit()
        self.ukonceno = False
        wrap = ttk.Frame(self.root, padding=60)
        wrap.pack(expand=True, fill="both")

        lang_btn = ttk.Button(wrap, text=t("btn_lang"), command=self._toggle_lang, padding=6)
        lang_btn.pack(anchor="ne")

        ttk.Label(wrap, text=t("app_title"), style="Nadpis.TLabel").pack(pady=(10, 8))
        ttk.Label(wrap, text=t("app_subtitle"), style="Podnadpis.TLabel").pack(pady=(0, 50))

        btn_frame = ttk.Frame(wrap)
        btn_frame.pack()

        ttk.Button(btn_frame, text=t("menu_human"), width=40,
                   command=lambda: self.show_nastaveni("human")).pack(pady=10)
        ttk.Button(btn_frame, text=t("menu_pvp"), width=40,
                   command=lambda: self.show_nastaveni("pvp")).pack(pady=10)
        ttk.Button(btn_frame, text=t("menu_duel"), width=40,
                   command=lambda: self.show_nastaveni("duel")).pack(pady=10)
        ttk.Button(btn_frame, text=t("menu_tour"), width=40,
                   command=lambda: self.show_nastaveni("turnaj")).pack(pady=10)
        ttk.Button(btn_frame, text=t("menu_evo"), width=40, style="Accent.TButton",
                   command=lambda: self.show_nastaveni("evoluce")).pack(pady=10)

        ttk.Frame(btn_frame, height=20).pack()
        ttk.Button(btn_frame, text=t("menu_custom"), width=40, command=self.show_vlastni_bot).pack(pady=10)
        ttk.Button(btn_frame, text=t("menu_desc"), width=40, command=self.show_bot_descriptions).pack(pady=10)

    def show_bot_descriptions(self):
        scroll_frame = self._vytvor_scrollable_ramec()
        wrap = ttk.Frame(scroll_frame, padding=40)
        wrap.pack(expand=True, fill="both")

        ttk.Label(wrap, text=t("mode_desc"), style="Nadpis.TLabel").pack(pady=(0, 30))

        for i, (jmeno, _, popis) in enumerate(get_boti()):
            barva = BOT_COLORS[i % len(BOT_COLORS)]

            karta = ttk.Frame(wrap, style="Panel.TFrame")
            karta.pack(fill="x", pady=10)

            hlavicka_frame = tk.Frame(karta, bg=PANEL)
            hlavicka_frame.pack(fill="x", padx=20, pady=(20, 5))

            ctverecek = tk.Canvas(hlavicka_frame, width=16, height=16, bg=PANEL, highlightthickness=0)
            ctverecek.pack(side="left", pady=2)
            ctverecek.create_rectangle(0, 0, 16, 16, fill=barva, outline=barva)

            ttk.Label(hlavicka_frame, text=jmeno, style="Panel.TLabel",
                      font=("Helvetica", 16, "bold"), foreground=barva).pack(side="left", padx=10)

            txt = tk.Text(karta, height=4, bg=PANEL, fg=TEXT, bd=0, font=("Helvetica", 12),
                          wrap="word", highlightthickness=0)
            txt.insert("1.0", popis)
            txt.configure(state="disabled")
            txt.pack(fill="x", padx=20, pady=(0, 20))

        btns = ttk.Frame(wrap)
        btns.pack(pady=30)
        ttk.Button(btns, text=t("btn_back"), command=self.show_hlavni_menu).pack()

    def show_nastaveni(self, mode):
        self.mode = mode
        self.manual_vars = {}
        self.rozlozeni_var = tk.StringVar(value=t("pop_even"))
        self.bot_vars = {}

        scroll_frame = self._vytvor_scrollable_ramec()
        wrap = ttk.Frame(scroll_frame, padding=40)
        wrap.pack(expand=True, fill="both")

        nadpisy = {"human": t("mode_human"), "pvp": t("mode_pvp"), "duel": t("mode_duel"),
                   "turnaj": t("mode_tour"), "evoluce": t("mode_evo")}
        ttk.Label(wrap, text=nadpisy[mode], style="Nadpis.TLabel").pack(pady=(0, 30))

        form = ttk.Frame(wrap, style="Panel.TFrame", padding=30)
        form.pack(fill="x", pady=10)
        form.columnconfigure(1, weight=1)

        radek = 0
        boti_aktualni = get_boti()
        jmena_botu = [j for j, _, _ in boti_aktualni]

        if mode == "human":
            ttk.Label(form, text=t("set_opp"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=12)
            self.combo1 = ttk.Combobox(form, values=jmena_botu, state="readonly", width=30)
            self.combo1.current(2)
            self.combo1.grid(row=radek, column=1, pady=12, padx=15, sticky="w")
            radek += 1

        elif mode == "pvp":
            ttk.Label(form, text=t("set_p1"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=12)
            self.p1_name_var = tk.StringVar(value="Player 1")
            ttk.Entry(form, textvariable=self.p1_name_var, width=32, font=("Helvetica", 12)).grid(
                row=radek, column=1, pady=12, padx=15, sticky="w")
            radek += 1
            ttk.Label(form, text=t("set_p2"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=12)
            self.p2_name_var = tk.StringVar(value="Player 2")
            ttk.Entry(form, textvariable=self.p2_name_var, width=32, font=("Helvetica", 12)).grid(
                row=radek, column=1, pady=12, padx=15, sticky="w")
            radek += 1

        elif mode == "duel":
            ttk.Label(form, text=t("set_b1"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=12)
            self.combo1 = ttk.Combobox(form, values=jmena_botu, state="readonly", width=30)
            self.combo1.current(5)
            self.combo1.grid(row=radek, column=1, pady=12, padx=15, sticky="w")
            radek += 1
            ttk.Label(form, text=t("set_b2"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=12)
            self.combo2 = ttk.Combobox(form, values=jmena_botu, state="readonly", width=30)
            self.combo2.current(4)
            self.combo2.grid(row=radek, column=1, pady=12, padx=15, sticky="w")
            radek += 1

        elif mode in ("turnaj", "evoluce"):
            ttk.Label(form, text=t("set_bots"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=12)
            self.btn_toggle_boti = ttk.Button(form, text=t("btn_sel_bots"), command=self._toggle_bot_selection)
            self.btn_toggle_boti.grid(row=radek, column=1, sticky="w", pady=12, padx=15)
            radek += 1

            self.boti_frame = ttk.Frame(form, style="Panel.TFrame")
            self.boti_frame.grid(row=radek, column=0, columnspan=2, sticky="w", padx=(30, 15), pady=0)
            self.boti_frame.grid_remove()

            for i, (jmeno, _, _) in enumerate(boti_aktualni):
                var = tk.BooleanVar(value=True)
                self.bot_vars[jmeno] = var
                ttk.Checkbutton(self.boti_frame, text=jmeno, variable=var, style="TCheckbutton").grid(
                    row=i // 2, column=i % 2, sticky="w", padx=10, pady=4)
            radek += 1

        if mode == "evoluce":
            ttk.Label(form, text=t("set_gen"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=12)
            self.generace_var = tk.IntVar(value=100)
            ttk.Spinbox(form, from_=10, to=1000, textvariable=self.generace_var, width=10,
                       font=("Helvetica", 12)).grid(row=radek, column=1, sticky="w", pady=12, padx=15)
            radek += 1

            ttk.Label(form, text=t("set_pop"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=12)
            self.combo_rozlozeni = ttk.Combobox(form, textvariable=self.rozlozeni_var,
                                                values=[t("pop_even"), t("pop_rand"), t("pop_man")],
                                                state="readonly", width=28, font=("Helvetica", 12))
            self.combo_rozlozeni.grid(row=radek, column=1, sticky="w", pady=12, padx=15)
            self.combo_rozlozeni.bind("<<ComboboxSelected>>", self._toggle_manualni_populace)
            radek += 1

            self.manual_frame = ttk.Frame(form, style="Panel.TFrame")
            self.manual_frame.grid(row=radek, column=0, columnspan=2, sticky="w", padx=(30, 15), pady=0)
            self.manual_frame.grid_remove()

            for i, (jmeno, _, _) in enumerate(boti_aktualni):
                ttk.Label(self.manual_frame, text=f"{jmeno} {t('weight')}", style="Panel.TLabel").grid(
                    row=i, column=0, sticky="w", pady=4)
                var = tk.IntVar(value=10)
                ttk.Spinbox(self.manual_frame, from_=0, to=999, textvariable=var, width=6,
                           font=("Helvetica", 12)).grid(row=i, column=1, sticky="w", padx=10, pady=4)
                self.manual_vars[jmeno] = var
            radek += 1

            self.mutace_var = tk.DoubleVar(value=0.0)
            radek = self._vytvor_posuvnik(form, radek, t("set_mut"), self.mutace_var, max_val=10.0, is_float=True)

        ttk.Label(form, text=t("set_rounds"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=12)
        self.kola_var = tk.IntVar(value=10)
        ttk.Spinbox(form, from_=1, to=200, textvariable=self.kola_var, width=10, font=("Helvetica", 12)).grid(
            row=radek, column=1, sticky="w", pady=12, padx=15)
        radek += 1

        self.neznama_kola_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(form, text=t("set_unknown_r"), variable=self.neznama_kola_var,
                        style="TCheckbutton").grid(row=radek, column=0, columnspan=2, sticky="w", pady=6)
        radek += 1

        self.mlha_var = tk.DoubleVar(value=0.0)
        radek = self._vytvor_posuvnik(form, radek, t("set_fog"), self.mlha_var, max_val=1.0, nasobic=100)

        ttk.Label(form, text=t("set_delay"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=12)
        self.delay_var = tk.IntVar(value=2)
        ttk.Spinbox(form, from_=0, to=50, textvariable=self.delay_var, width=10, font=("Helvetica", 12)).grid(
            row=radek, column=1, sticky="w", pady=12, padx=15)
        radek += 1

        self.zkresleni_var = tk.DoubleVar(value=0.0)
        radek = self._vytvor_posuvnik(form, radek, t("set_noise"), self.zkresleni_var, max_val=1.0, nasobic=100)

        self.chyba_label = ttk.Label(wrap, text="", style="Error.TLabel")
        self.chyba_label.pack(pady=5)

        btns = ttk.Frame(wrap)
        btns.pack(pady=30)
        ttk.Button(btns, text=t("btn_back"), command=self.show_hlavni_menu).pack(side="left", padx=10)
        ttk.Button(btns, text=t("btn_start"), style="Accent.TButton", command=self.spustit).pack(side="left", padx=10)

    def _toggle_bot_selection(self):
        if self.boti_frame.winfo_viewable():
            self.boti_frame.grid_remove()
            self.btn_toggle_boti.configure(text=t("btn_sel_bots"))
        else:
            self.boti_frame.grid()
            self.btn_toggle_boti.configure(text=t("btn_hide_bots"))

    def _toggle_manualni_populace(self, event=None):
        if hasattr(self, 'rozlozeni_var') and self.rozlozeni_var.get() == t("pop_man"):
            self.manual_frame.grid()
        else:
            self.manual_frame.grid_remove()

    def show_vlastni_bot(self):
        scroll_frame = self._vytvor_scrollable_ramec()
        wrap = ttk.Frame(scroll_frame, padding=40)
        wrap.pack(expand=True, fill="both")

        ttk.Label(wrap, text=t("cb_title"), style="Nadpis.TLabel").pack(pady=(0, 8))
        ttk.Label(wrap, text=t("cb_sub"), style="Podnadpis.TLabel").pack(pady=(0, 30))

        form = ttk.Frame(wrap, style="Panel.TFrame", padding=30)
        form.pack(fill="x", pady=10)
        form.columnconfigure(1, weight=1)

        n = VLASTNI_NASTAVENI
        radek = 0

        ttk.Label(form, text=t("cb_name"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=10)
        self.jmeno_bota_var = tk.StringVar(value=n["jmeno"])
        ttk.Entry(form, textvariable=self.jmeno_bota_var, width=42, font=("Helvetica", 12)).grid(
            row=radek, column=1, sticky="w", pady=10, padx=15)
        radek += 1

        ttk.Label(form, text=t("cb_first"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=10)
        self.combo_prvni = ttk.Combobox(form, values=[t(f"opt_{k.lower()}") for k in KEYS_PRVNI],
                                        state="readonly", width=40)
        self.combo_prvni.current(KEYS_PRVNI.index(n["prvni_tah"]))
        self.combo_prvni.grid(row=radek, column=1, sticky="w", pady=10, padx=15)
        radek += 1

        ttk.Separator(form, orient="horizontal").grid(row=radek, column=0, columnspan=2, sticky="ew", pady=15)
        radek += 1

        ttk.Label(form, text=t("cb_base_strat"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=10)
        self.combo_reakce = ttk.Combobox(form, values=[t(f"opt_{k}") for k in KEYS_STRATEGIE],
                                         state="readonly", width=40)
        self.combo_reakce.current(KEYS_STRATEGIE.index(n["zakladni_strategie"]))
        self.combo_reakce.grid(row=radek, column=1, sticky="w", pady=10, padx=15)
        radek += 1

        self.prob_var = tk.IntVar(value=n["pravdepodobnost_c"])
        radek = self._vytvor_posuvnik(form, radek, t("cb_prob_c"), self.prob_var, max_val=100)

        ttk.Separator(form, orient="horizontal").grid(row=radek, column=0, columnspan=2, sticky="ew", pady=15)
        radek += 1

        ttk.Label(form, text=t("cb_tol"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=10)
        self.tol_var = tk.IntVar(value=n["tolerance_d"])
        ttk.Spinbox(form, from_=1, to=10, textvariable=self.tol_var, width=10, font=("Helvetica", 12)).grid(
            row=radek, column=1, sticky="w", pady=10, padx=15)
        radek += 1

        self.ratio_var = tk.IntVar(value=n["zrada_pri_pomeru"])
        radek = self._vytvor_posuvnik(form, radek, t("cb_ratio"), self.ratio_var, max_val=100)

        self.neodpoustet_var = tk.BooleanVar(value=n["nikdy_neodpoustet"])
        ttk.Checkbutton(form, text=t("cb_grudge"), variable=self.neodpoustet_var, style="TCheckbutton").grid(
            row=radek, column=0, columnspan=2, sticky="w", pady=10)
        radek += 1

        ttk.Separator(form, orient="horizontal").grid(row=radek, column=0, columnspan=2, sticky="ew", pady=15)
        radek += 1

        ttk.Label(form, text=t("cb_fog"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=10)
        self.combo_mlha = ttk.Combobox(form, values=[t(f"opt_{k}") for k in KEYS_MLHA],
                                       state="readonly", width=40)
        self.combo_mlha.current(KEYS_MLHA.index(n["reakce_mlha"]))
        self.combo_mlha.grid(row=radek, column=1, sticky="w", pady=10, padx=15)
        radek += 1

        ttk.Label(form, text=t("cb_last"), style="Panel.TLabel").grid(row=radek, column=0, sticky="w", pady=10)
        self.combo_posledni = ttk.Combobox(form, values=[t(f"opt_{k}") for k in KEYS_POSLEDNI],
                                           state="readonly", width=40)
        self.combo_posledni.current(KEYS_POSLEDNI.index(n["posledni_tah"]))
        self.combo_posledni.grid(row=radek, column=1, sticky="w", pady=10, padx=15)
        radek += 1

        self.chyba_var = tk.DoubleVar(value=n["chyba_pct"])
        radek = self._vytvor_posuvnik(form, radek, t("cb_tremble"), self.chyba_var, max_val=100)

        btns = ttk.Frame(wrap)
        btns.pack(pady=30)
        ttk.Button(btns, text=t("btn_back"), command=self.show_hlavni_menu).pack(side="left", padx=10)
        ttk.Button(btns, text=t("btn_save"), style="Accent.TButton", command=self._uloz_vlastniho_bota).pack(
            side="left", padx=10)

        self.vlastni_bot_status = ttk.Label(wrap, text="", style="Podnadpis.TLabel")
        self.vlastni_bot_status.pack()

    def _uloz_vlastniho_bota(self):
        VLASTNI_NASTAVENI["jmeno"] = self.jmeno_bota_var.get().strip() or t("bot_custom_def")
        VLASTNI_NASTAVENI["prvni_tah"] = KEYS_PRVNI[self.combo_prvni.current()]
        VLASTNI_NASTAVENI["zakladni_strategie"] = KEYS_STRATEGIE[self.combo_reakce.current()]
        VLASTNI_NASTAVENI["pravdepodobnost_c"] = self.prob_var.get()
        VLASTNI_NASTAVENI["tolerance_d"] = self.tol_var.get()
        VLASTNI_NASTAVENI["zrada_pri_pomeru"] = self.ratio_var.get()
        VLASTNI_NASTAVENI["reakce_mlha"] = KEYS_MLHA[self.combo_mlha.current()]
        VLASTNI_NASTAVENI["posledni_tah"] = KEYS_POSLEDNI[self.combo_posledni.current()]
        VLASTNI_NASTAVENI["nikdy_neodpoustet"] = self.neodpoustet_var.get()
        VLASTNI_NASTAVENI["chyba_pct"] = self.chyba_var.get()
        self.vlastni_bot_status.configure(text=t("cb_saved"))

    def spustit(self):
        self.chyba_label.configure(text="")
        cfg = NastaveniZapasu(
            kola=self.kola_var.get(),
            neznama_kola=self.neznama_kola_var.get(),
            mlha=round(self.mlha_var.get(), 2),
            delay=self.delay_var.get(),
            zkresleni=round(self.zkresleni_var.get(), 2),
        )
        boti_aktualni = get_boti()

        if self.mode in ("turnaj", "evoluce"):
            vybrani_boti = [(jmeno, funkce, popis) for jmeno, funkce, popis in boti_aktualni
                            if self.bot_vars.get(jmeno, tk.BooleanVar(value=True)).get()]
            if len(vybrani_boti) < 2:
                self.chyba_label.configure(text=t("err_min_bots"))
                return
            boti_aktualni = vybrani_boti

        if self.mode == "human":
            jmeno, funkce, _ = get_boti()[self.combo1.current()]
            self.pripravit_zapas("Player", None, jmeno, funkce, cfg)
        elif self.mode == "pvp":
            j1 = self.p1_name_var.get().strip() or "Player 1"
            j2 = self.p2_name_var.get().strip() or "Player 2"
            self.pripravit_zapas(j1, None, j2, None, cfg)
        elif self.mode == "duel":
            vsechny_boty = get_boti()
            j1, f1, _ = vsechny_boty[self.combo1.current()]
            j2, f2, _ = vsechny_boty[self.combo2.current()]
            self.pripravit_zapas(j1, f1, j2, f2, cfg)
        elif self.mode == "turnaj":
            self.spustit_turnaj(cfg, boti_aktualni)
        elif self.mode == "evoluce":
            generaci = self.generace_var.get()
            rozlozeni = self.rozlozeni_var.get() if hasattr(self, 'rozlozeni_var') else t("pop_even")
            manual_hody = ({j: self.manual_vars[j].get() for j, _, _ in boti_aktualni}
                          if hasattr(self, 'manual_vars') else {})
            mutace = self.mutace_var.get() if hasattr(self, 'mutace_var') else 0.0
            self.spustit_evoluci(cfg, boti_aktualni, generaci, rozlozeni, manual_hody, mutace)

    def pripravit_zapas(self, jmeno1, funkce1, jmeno2, funkce2, cfg: NastaveniZapasu):
        self.j1, self.f1 = jmeno1, funkce1
        self.j2, self.f2 = jmeno2, funkce2
        self.cfg = cfg
        self.skutecna_kola = skutecny_pocet_kol(cfg)
        self.text_kol = "?" if cfg.neznama_kola else str(self.skutecna_kola)

        self.true1, self.true2 = [], []
        self.perc1_hist, self.perc2_hist = [], []
        self.fog1, self.fog2 = [], []
        self.skore1, self.skore2, self.kolo = 0, 0, 0
        self.p1_tah, self.p2_tah = None, None

        self._vycistit()
        self.ukonceno = False
        wrap = ttk.Frame(self.root, padding=30)
        wrap.pack(expand=True, fill="both")

        hlavicka = ttk.Frame(wrap)
        hlavicka.pack(fill="x", pady=(0, 20))
        ttk.Label(hlavicka, text=t("match_run"), style="Podnadpis.TLabel").pack(side="left")
        ttk.Label(hlavicka, text=t("match_info", int(cfg.zkresleni * 100), int(cfg.mlha * 100)),
                  style="Podnadpis.TLabel").pack(side="right")

        skore_frame = ttk.Frame(wrap)
        skore_frame.pack(fill="x", pady=10)
        self.skore1_label = self._vytvor_skore_panel(skore_frame, jmeno1, (0, 10))
        self.skore2_label = self._vytvor_skore_panel(skore_frame, jmeno2, (10, 0))

        self.kolo_label = ttk.Label(wrap, text=t("match_round", 0, self.text_kol), style="Podnadpis.TLabel")
        self.kolo_label.pack(pady=10)

        log_frame = ttk.Frame(wrap, style="Panel.TFrame", padding=10)
        log_frame.pack(fill="both", expand=True, pady=10)
        self.log = tk.Text(log_frame, height=10, bg=PANEL, fg=TEXT, bd=0, font=("Consolas", 12),
                           wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=5, pady=5)
        self.log.tag_configure("C", foreground=GREEN)
        self.log.tag_configure("D", foreground=RED)
        self.log.tag_configure("info", foreground=MUTED)
        self.log.tag_configure("alert", foreground="#f59e0b")

        self.bottom_bar = ttk.Frame(wrap)
        self.bottom_bar.pack(fill="x", pady=(20, 0))
        self.ovladani_frame = ttk.Frame(self.bottom_bar)
        self.ovladani_frame.pack(side="top", fill="x")

        exit_frame = ttk.Frame(self.bottom_bar)
        exit_frame.pack(side="bottom", pady=20)
        ttk.Button(exit_frame, text=t("btn_menu"), command=self.show_hlavni_menu).pack()

        self._sestav_ovladani()
        self._pridat_log(t("log_init"), "info")
        self.dalsi_kolo()

    def _sestav_ovladani(self):
        if self.mode == "human":
            r = ttk.Frame(self.ovladani_frame)
            r.pack()
            self.btn_c1 = ttk.Button(r, text=t("btn_coop"), style="Zelena.TButton",
                                     command=lambda: self.human_tah("C"))
            self.btn_c1.pack(side="left", padx=10)
            self.btn_d1 = ttk.Button(r, text=t("btn_def"), style="Cervena.TButton",
                                     command=lambda: self.human_tah("D"))
            self.btn_d1.pack(side="left", padx=10)

        elif self.mode == "pvp":
            p1_ovl = ttk.Frame(self.ovladani_frame, style="Panel.TFrame", padding=15)
            p1_ovl.pack(side="left", expand=True, fill="x", padx=(0, 10))
            ttk.Label(p1_ovl, text=self.j1, style="Panel.TLabel", font=("Helvetica", 12, "bold")).pack(pady=(0, 10))
            fr1 = ttk.Frame(p1_ovl, style="Panel.TFrame")
            fr1.pack()
            self.btn_c1 = ttk.Button(fr1, text=t("btn_coop"), style="Zelena.TButton",
                                     command=lambda: self.pvp_tah(1, "C"))
            self.btn_c1.pack(side="left", padx=5)
            self.btn_d1 = ttk.Button(fr1, text=t("btn_def"), style="Cervena.TButton",
                                     command=lambda: self.pvp_tah(1, "D"))
            self.btn_d1.pack(side="left", padx=5)
            self.stav_p1 = ttk.Label(p1_ovl, text="", style="Panel.TLabel", foreground=ACCENT)
            self.stav_p1.pack(pady=(10, 0))

            p2_ovl = ttk.Frame(self.ovladani_frame, style="Panel.TFrame", padding=15)
            p2_ovl.pack(side="right", expand=True, fill="x", padx=(10, 0))
            ttk.Label(p2_ovl, text=self.j2, style="Panel.TLabel", font=("Helvetica", 12, "bold")).pack(pady=(0, 10))
            fr2 = ttk.Frame(p2_ovl, style="Panel.TFrame")
            fr2.pack()
            self.btn_c2 = ttk.Button(fr2, text=t("btn_coop"), style="Zelena.TButton",
                                     command=lambda: self.pvp_tah(2, "C"))
            self.btn_c2.pack(side="left", padx=5)
            self.btn_d2 = ttk.Button(fr2, text=t("btn_def"), style="Cervena.TButton",
                                     command=lambda: self.pvp_tah(2, "D"))
            self.btn_d2.pack(side="left", padx=5)
            self.stav_p2 = ttk.Label(p2_ovl, text="", style="Panel.TLabel", foreground=ACCENT)
            self.stav_p2.pack(pady=(10, 0))

    def _pridat_log(self, text, tag=None):
        if not hasattr(self, 'log'):
            return
        _log_pripoj(self.log, text, tag)

    def _vypocitej_viditelnou_historii(self):
        v1 = spocitej_viditelnou_historii(self.perc1_hist, self.fog1, self.kolo, self.cfg.delay)
        v2 = spocitej_viditelnou_historii(self.perc2_hist, self.fog2, self.kolo, self.cfg.delay)
        return v1, v2

    def dalsi_kolo(self):
        if self.ukonceno or not hasattr(self, 'kolo_label') or not self.kolo_label.winfo_exists():
            return
        if self.kolo >= self.skutecna_kola:
            self.konec_zapasu()
            return

        self.kolo_label.configure(text=t("match_round", self.kolo + 1, self.text_kol))
        self.vis1, self.vis2 = self._vypocitej_viditelnou_historii()
        self.p1_tah, self.p2_tah = None, None
        self.info_pro_boty = {"kolo": self.kolo, "celkem_kol": None if self.cfg.neznama_kola else self.skutecna_kola}

        if self.mode == "human":
            self.btn_c1.configure(state="normal")
            self.btn_d1.configure(state="normal")
        elif self.mode == "pvp":
            self.btn_c1.configure(state="normal")
            self.btn_d1.configure(state="normal")
            self.btn_c2.configure(state="normal")
            self.btn_d2.configure(state="normal")
            self.stav_p1.configure(text="")
            self.stav_p2.configure(text="")
        elif self.mode == "duel":
            tah1 = self.f1(self.true1, self.vis2, self.info_pro_boty)
            tah2 = self.f2(self.true2, self.vis1, self.info_pro_boty)
            self.dokoncit_kolo(tah1, tah2)
            self.root.after(150, self.dalsi_kolo)

    def human_tah(self, tah1):
        self.btn_c1.configure(state="disabled")
        self.btn_d1.configure(state="disabled")
        tah2 = self.f2(self.true2, self.vis1, self.info_pro_boty)
        self.dokoncit_kolo(tah1, tah2)
        self.root.after(200, self.dalsi_kolo)

    def pvp_tah(self, hrac, tah):
        if hrac == 1:
            self.p1_tah = tah
            self.btn_c1.configure(state="disabled")
            self.btn_d1.configure(state="disabled")
            self.stav_p1.configure(text=t("status_hidden"))
        else:
            self.p2_tah = tah
            self.btn_c2.configure(state="disabled")
            self.btn_d2.configure(state="disabled")
            self.stav_p2.configure(text=t("status_hidden"))

        if self.p1_tah and self.p2_tah:
            self.dokoncit_kolo(self.p1_tah, self.p2_tah)
            self.root.after(800, self.dalsi_kolo)

    def dokoncit_kolo(self, tah1, tah2):
        if self.ukonceno:
            return

        p1, p2, body1, body2, fog1_bool, fog2_bool = vyhodnot_kolo(tah1, tah2, self.cfg.zkresleni, self.cfg.mlha)

        self.skore1 += body1
        self.skore2 += body2
        self.true1.append(tah1)
        self.true2.append(tah2)
        self.perc1_hist.append(p1)
        self.perc2_hist.append(p2)
        self.fog1.append(fog1_bool)
        self.fog2.append(fog2_bool)

        if hasattr(self, 'skore1_label') and self.skore1_label.winfo_exists():
            self.skore1_label.configure(text=str(self.skore1))
            self.skore2_label.configure(text=str(self.skore2))

        self._pridat_log(f"[{self.kolo + 1}] ", "info")
        if tah1 != p1:
            self._pridat_log(f"{tah1} " + t("log_perc", p1), "alert")
        else:
            self._pridat_log(f"{tah1} ", tah1)
        self._pridat_log(": ", "info")
        if tah2 != p2:
            self._pridat_log(f"{tah2} " + t("log_perc", p2), "alert")
        else:
            self._pridat_log(f"{tah2}  ", tah2)

        self._pridat_log(f"(+{body1} / +{body2})\n", "info")
        self.kolo += 1

    def konec_zapasu(self):
        if hasattr(self, 'btn_c1') and self.btn_c1.winfo_exists():
            self.btn_c1.configure(state="disabled")
            self.btn_d1.configure(state="disabled")
        if hasattr(self, 'btn_c2') and self.btn_c2.winfo_exists():
            self.btn_c2.configure(state="disabled")
            self.btn_d2.configure(state="disabled")

        if self.skore1 > self.skore2:
            res = t("win", self.j1)
        elif self.skore2 > self.skore1:
            res = t("win", self.j2)
        else:
            res = t("tie")
        self._pridat_log(t("log_end", res), "info")

    def spustit_turnaj(self, cfg: NastaveniZapasu, boti_aktualni):
        self._vycistit()
        wrap = ttk.Frame(self.root, padding=40)
        wrap.pack(expand=True, fill="both")

        ttk.Label(wrap, text=t("mode_tour"), style="Nadpis.TLabel").pack(pady=(0, 20))

        cols = ("misto", "jmeno", "body", "v", "r", "p")
        strom = ttk.Treeview(wrap, columns=cols, show="headings", height=8)
        strom.heading("misto", text="#")
        strom.heading("jmeno", text="Bot")
        strom.heading("body", text=t("tour_score"))
        strom.heading("v", text=t("tour_w"))
        strom.heading("r", text=t("tour_t"))
        strom.heading("p", text=t("tour_l"))
        strom.column("misto", width=40, anchor="center")
        strom.column("jmeno", width=300)
        strom.column("body", width=100, anchor="center")
        strom.column("v", width=60, anchor="center")
        strom.column("r", width=60, anchor="center")
        strom.column("p", width=60, anchor="center")
        strom.pack(fill="x", pady=10)

        log_frame = ttk.Frame(wrap, style="Panel.TFrame", padding=10)
        log_frame.pack(fill="both", expand=True, pady=10)
        log = tk.Text(log_frame, height=10, bg=PANEL, fg=TEXT, bd=0, font=("Consolas", 12),
                      wrap="word", state="disabled")
        log.pack(fill="both", expand=True, padx=5, pady=5)

        stats = {jmeno: {"body": 0, "v": 0, "r": 0, "p": 0} for jmeno, _, _ in boti_aktualni}

        for i in range(len(boti_aktualni)):
            for j in range(i + 1, len(boti_aktualni)):
                jmeno1, funkce1, _ = boti_aktualni[i]
                jmeno2, funkce2, _ = boti_aktualni[j]

                s1, s2 = odehraj_simulovany_zapas(funkce1, funkce2, cfg)
                stats[jmeno1]["body"] += s1
                stats[jmeno2]["body"] += s2

                if s1 > s2:
                    stats[jmeno1]["v"] += 1
                    stats[jmeno2]["p"] += 1
                elif s2 > s1:
                    stats[jmeno2]["v"] += 1
                    stats[jmeno1]["p"] += 1
                else:
                    stats[jmeno1]["r"] += 1
                    stats[jmeno2]["r"] += 1

                _log_pripoj(log, f"{jmeno1}  {s1} : {s2}  {jmeno2}\n")

        poradi = sorted(stats.items(), key=lambda x: x[1]["body"], reverse=True)
        for misto, (jmeno, d) in enumerate(poradi, start=1):
            strom.insert("", "end", values=(misto, jmeno, d["body"], d["v"], d["r"], d["p"]))

        btns = ttk.Frame(wrap)
        btns.pack(pady=20)
        ttk.Button(btns, text=t("btn_menu"), command=self.show_hlavni_menu).pack(side="left")

    def spustit_evoluci(self, cfg: NastaveniZapasu, boti_aktualni, generaci, rozlozeni, manual_hody, mutace):
        self._vycistit()
        self.ukonceno = False
        self.cfg = cfg
        self.boti_aktualni = boti_aktualni
        self.celkova_populace = 1000

        if rozlozeni == t("pop_rand"):
            vahy = {jmeno: random.randint(1, 100) for jmeno, _, _ in boti_aktualni}
            suma_vah = sum(vahy.values())
            self.populace = {j: (vahy[j] / suma_vah) * self.celkova_populace for j, _, _ in boti_aktualni}
        elif rozlozeni == t("pop_man") and manual_hody:
            suma_vah = sum(manual_hody.values())
            if suma_vah == 0:
                self.populace = {j: self.celkova_populace / len(boti_aktualni) for j, _, _ in boti_aktualni}
            else:
                self.populace = {j: (manual_hody[j] / suma_vah) * self.celkova_populace for j, _, _ in boti_aktualni}
        else:
            self.populace = {j: self.celkova_populace / len(boti_aktualni) for j, _, _ in boti_aktualni}

        self.historie = [self.populace.copy()]
        self.generace, self.max_generaci = 0, generaci
        self.mutace_mira = mutace / 100.0

        wrap = ttk.Frame(self.root, padding=40)
        wrap.pack(expand=True, fill="both")

        hlavicka = ttk.Frame(wrap)
        hlavicka.pack(fill="x", pady=(0, 10))
        ttk.Label(hlavicka, text=t("evo_title"), style="Nadpis.TLabel").pack(side="left")
        self.gen_label = ttk.Label(hlavicka, text=t("evo_gen", 0, generaci), style="Podnadpis.TLabel")
        self.gen_label.pack(side="right")

        main_content = ttk.Frame(wrap)
        main_content.pack(expand=True, fill="both")

        graf_frame = ttk.Frame(main_content, style="Panel.TFrame", padding=10)
        graf_frame.pack(side="left", expand=True, fill="both", padx=(0, 10))
        self.canvas = tk.Canvas(graf_frame, bg=BG, highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")
        self.canvas.bind("<Configure>", lambda e: self.vykresli_graf())

        legenda_frame = ttk.Frame(main_content, width=250)
        legenda_frame.pack(side="right", fill="y", padx=(10, 0))
        ttk.Label(legenda_frame, text=t("evo_pop"), style="Panel.TLabel", font=("Helvetica", 14, "bold")).pack(
            anchor="w", pady=(0, 15))

        self.legend_labels = {}
        for i, (jmeno, _, _) in enumerate(self.boti_aktualni):
            barva = BOT_COLORS[i % len(BOT_COLORS)]
            radek_frame = ttk.Frame(legenda_frame)
            radek_frame.pack(fill="x", pady=6)
            ctverecek = tk.Canvas(radek_frame, width=16, height=16, bg=BG, highlightthickness=0)
            ctverecek.pack(side="left")
            ctverecek.create_rectangle(0, 0, 16, 16, fill=barva, outline=barva)
            lbl = ttk.Label(radek_frame, text=f"{jmeno}: {int(self.populace[jmeno])}", style="Panel.TLabel")
            lbl.pack(side="left", padx=10)
            self.legend_labels[jmeno] = lbl

        self.vysledek_evoluce_label = ttk.Label(wrap, text="", style="Podnadpis.TLabel",
                                                wraplength=700, justify="center")
        self.vysledek_evoluce_label.pack(pady=(10, 0))

        spodni_pruh = ttk.Frame(wrap)
        spodni_pruh.pack(fill="x", pady=(10, 0))
        ttk.Button(spodni_pruh, text=t("btn_menu"), command=self.show_hlavni_menu).pack()

        self.root.update_idletasks()
        self.vykresli_graf()
        self.root.after(200, self.evoluci_krok)

    def evoluci_krok(self):
        if self.ukonceno:
            return
        if self.generace >= self.max_generaci:
            self._evoluce_dokoncena()
            return

        vyplaty = {j: {k: 0 for k, _, _ in self.boti_aktualni} for j, _, _ in self.boti_aktualni}
        for i in range(len(self.boti_aktualni)):
            for j in range(i, len(self.boti_aktualni)):
                j1, f1, _ = self.boti_aktualni[i]
                j2, f2, _ = self.boti_aktualni[j]
                s1, s2 = odehraj_simulovany_zapas(f1, f2, self.cfg)
                vyplaty[j1][j2] = s1
                vyplaty[j2][j1] = s2

        fitness = {}
        for jmeno1, _, _ in self.boti_aktualni:
            skore_agregat = sum(vyplaty[jmeno1][jmeno2] * self.populace[jmeno2]
                                for jmeno2, _, _ in self.boti_aktualni)
            fitness[jmeno1] = skore_agregat * self.populace[jmeno1]

        celkove_fitness = sum(fitness.values())
        if celkove_fitness > 0:
            nova_populace = {jmeno: (fitness[jmeno] / celkove_fitness) * self.celkova_populace
                            for jmeno in self.populace}
        else:
            nova_populace = self.populace.copy()

        if self.mutace_mira > 0:
            mutanti_celkem = {jmeno: 0.0 for jmeno, _, _ in self.boti_aktualni}
            pocet_druhu = len(self.boti_aktualni)
            for jmeno in nova_populace:
                pocet_mutantu = nova_populace[jmeno] * self.mutace_mira
                nova_populace[jmeno] -= pocet_mutantu
                pridel = pocet_mutantu / (pocet_druhu - 1) if pocet_druhu > 1 else 0
                for ost in mutanti_celkem:
                    if ost != jmeno:
                        mutanti_celkem[ost] += pridel
            for jmeno in nova_populace:
                nova_populace[jmeno] += mutanti_celkem[jmeno]

        for jmeno in nova_populace:
            if nova_populace[jmeno] < 0.5:
                nova_populace[jmeno] = 0

        self.populace = nova_populace
        self.historie.append(self.populace.copy())
        self.generace += 1
        self.vykresli_graf()
        self.root.after(30, self.evoluci_krok)

    def _evoluce_dokoncena(self):
        self.gen_label.configure(text=f"{t('evo_gen', self.generace, self.max_generaci)} - {t('evo_done')}")
        poradi = sorted(self.populace.items(), key=lambda x: x[1], reverse=True)
        text = "   ".join(f"{jmeno}: {int(pocet)}" for jmeno, pocet in poradi)
        self.vysledek_evoluce_label.configure(text=f"{t('evo_final')}: {text}")

    def vykresli_graf(self):
        if not hasattr(self, "canvas") or not self.canvas.winfo_exists():
            return
        if not hasattr(self, "legend_labels") or not hasattr(self, "historie"):
            return

        self.canvas.delete("all")
        w, h = int(self.canvas.winfo_width()), int(self.canvas.winfo_height())
        if w <= 1 or h <= 1:
            return
        dx, dy = w / max(10, self.max_generaci), h / self.celkova_populace

        for i, (jmeno, _, _) in enumerate(self.boti_aktualni):
            barva = BOT_COLORS[i % len(BOT_COLORS)]
            body = []
            for g, pop_dict in enumerate(self.historie):
                body.extend([g * dx, h - (pop_dict[jmeno] * dy)])
            if len(body) >= 4:
                self.canvas.create_line(body, fill=barva, width=3, smooth=True)
            self.legend_labels[jmeno].configure(text=f"{jmeno}: {int(self.populace[jmeno])}")

        self.gen_label.configure(text=t("evo_gen", self.generace, self.max_generaci))


if __name__ == "__main__":
    root = tk.Tk()
    app = MlhaValkyApp(root)
    root.mainloop()
