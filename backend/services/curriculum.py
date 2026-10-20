"""Fixed A2→B1 German curriculum aimed at speaking (goal "Mówienie B1").

Replaces the 30-day plan the model used to invent: the study plan is built from
this file, so every lesson knows its module, its skills and what kind of day it is.

Sources (report "Gotowe lekcje i funkcje dla LinguaAI", sections 5–7, 21.10.2026):
- target = CEFR B1 spoken production/interaction and the format of the Goethe/ÖSD
  B1 speaking exam (Teil 1 plan together, Teil 2 present a topic in 5 points,
  Teil 3 answer questions). Only the format is used, no exam texts.
- themes follow the 14 areas of Threshold 1990 (Council of Europe); word order
  follows Pienemann's stages (V2/inversion before verb-final clauses).
- one module = 2 weeks, one communicative task + 1–2 grammar points
  (task-based teaching, Bryfonski & McKay 2019); phase 4 returns to earlier
  themes (spacing). Proportions and module length are assumptions, not results.

Every skill has a fixed id. Lessons, exercises and (later) review errors are
tagged with these ids instead of names the model makes up, so mastery can be
summed per skill.
"""
from __future__ import annotations

import re

CURRICULUM_ID = "de-a2-b1-mowienie-v1"
DAYS_PER_MODULE = 14

# id: (kind, Polish name shown in the plan and given to the lesson prompt)
SKILLS: dict[str, tuple[str, str]] = {
    "G-V2": ("grammar", "Szyk zdania: czasownik na 2. miejscu i inwersja"),
    "G-TRENN": ("grammar", "Czasowniki rozdzielnie złożone (aufstehen, einkaufen)"),
    "G-MODAL": ("grammar", "Czasowniki modalne w zdaniu (können, müssen, wollen, dürfen, sollen)"),
    "G-AKK": ("grammar", "Biernik (Akkusativ): rodzajniki i zaimki"),
    "G-DAT": ("grammar", "Celownik (Dativ): rodzajniki, zaimki, czasowniki z celownikiem"),
    "G-WECHSEL": ("grammar", "Przyimki z celownikiem lub biernikiem (in, an, auf…: wo? / wohin?)"),
    "G-PERFEKT": ("grammar", "Czas przeszły Perfekt z haben i sein"),
    "G-REFL": ("grammar", "Czasowniki zwrotne (sich waschen, sich freuen)"),
    "G-WEIL-DASS": ("grammar", "Zdania podrzędne z weil i dass: czasownik na końcu"),
    "G-WENN-ALS-OB": ("grammar", "Zdania z wenn, als i ob (także pytania pośrednie)"),
    "G-PRAET": ("grammar", "Präteritum: war, hatte i czasowniki modalne"),
    "G-KONNEKT": ("grammar", "Łączniki: deshalb, trotzdem, denn, obwohl"),
    "G-ZU": ("grammar", "Bezokolicznik z zu oraz um … zu"),
    "G-K2": ("grammar", "Konjunktiv II: würde, hätte, wäre, könnte (propozycje i prośby)"),
    "G-KOMP": ("grammar", "Stopniowanie i porównania (größer als, so groß wie)"),
    "G-REL": ("grammar", "Zdania względne (der Mann, der …; das Buch, das …)"),
    "G-ADJ": ("grammar", "Odmiana przymiotnika po rodzajniku"),
    "G-TEMP": ("grammar", "Zdania czasowe: bevor, nachdem, während, seit"),
    "G-PASSIV": ("grammar", "Strona bierna w czasie teraźniejszym (wird gemacht)"),
    # A1 foundations: not taught by a module, but old lessons practised them and
    # errors in them still show up, so their mastery is tracked too.
    "G-PRAES": ("grammar", "Czas teraźniejszy: odmiana czasowników, sein i haben"),
    "G-ARTIKEL": ("grammar", "Rodzajniki i rodzaj rzeczownika w mianowniku (der/die/das, ein/eine)"),
    "S-OPIS": ("speaking", "Opowiadanie o doświadczeniu i zdarzeniu"),
    "S-T1": ("speaking", "Wspólne planowanie: propozycja, reakcja, decyzja (jak Teil 1)"),
    "S-T2": ("speaking", "Prezentacja tematu w 5 punktach z opinią (jak Teil 2)"),
    "S-T3": ("speaking", "Odpowiedzi na pytania i uzasadnianie zdania (jak Teil 3)"),
    "S-PROBLEM": ("speaking", "Wyjaśnianie problemu i załatwianie sprawy"),
    "S-OPINIA": ("speaking", "Wyrażanie i uzasadnianie opinii"),
}

# Each module: id, phase, theme, two vocabulary sub-themes (week 1, week 2),
# grammar for week 1 and week 2, the speaking skill and the module's task.
MODULES: list[dict] = [
    {"id": "M00", "phase": "Diagnoza", "theme": "Ja i moja codzienność",
     "vocab": ["Przedstawianie się i praca", "Mój tydzień"],
     "grammar": ["G-V2", "G-PERFEKT"], "speaking": "S-OPIS",
     "task": "Opowiedz o sobie i swoim ostatnim weekendzie (nagranie bazowe do porównań)"},
    {"id": "M01", "phase": "Opowiadam i planuję", "theme": "Dzień codzienny",
     "vocab": ["Poranek i obowiązki", "Wieczór i weekend"],
     "grammar": ["G-V2", "G-TRENN"], "speaking": "S-OPIS",
     "task": "Opowiedz, jak wygląda Twój zwykły dzień i czym różni się weekend"},
    {"id": "M02", "phase": "Opowiadam i planuję", "theme": "Mieszkanie i okolica",
     "vocab": ["Pokoje i meble", "Okolica i sąsiedzi"],
     "grammar": ["G-AKK", "G-DAT"], "speaking": "S-OPIS",
     "task": "Opisz swoje mieszkanie i drogę do najbliższego sklepu"},
    {"id": "M03", "phase": "Opowiadam i planuję", "theme": "Czas wolny i spotkania",
     "vocab": ["Hobby i sport", "Umawianie się"],
     "grammar": ["G-MODAL", "G-WECHSEL"], "speaking": "S-T1",
     "task": "Umów się z kolegą na wspólne wyjście: kiedy, gdzie, co robicie"},
    {"id": "M04", "phase": "Opowiadam i planuję", "theme": "Jedzenie, zakupy, restauracja",
     "vocab": ["W sklepie i na targu", "W restauracji"],
     "grammar": ["G-DAT", "G-MODAL"], "speaking": "S-T1",
     "task": "Zaplanuj z kolegą zakupy na wspólną kolację dla czterech osób"},
    {"id": "M05", "phase": "Opowiadam i planuję", "theme": "Podróże i ostatnie wydarzenia",
     "vocab": ["Transport i bilety", "Hotel i zwiedzanie"],
     "grammar": ["G-PERFEKT", "G-PERFEKT"], "speaking": "S-OPIS",
     "task": "Opowiedz o swojej ostatniej podróży: dokąd, z kim, co się wydarzyło"},
    {"id": "M06", "phase": "Opowiadam i planuję", "theme": "Zdrowie i ciało",
     "vocab": ["Ciało i dolegliwości", "U lekarza i w aptece"],
     "grammar": ["G-REFL", "G-WEIL-DASS"], "speaking": "S-PROBLEM",
     "task": "Wyjaśnij lekarzowi, co Ci dolega, od kiedy i dlaczego przyszedłeś"},
    {"id": "M07", "phase": "Opowiadam i planuję", "theme": "Rodzina i wspomnienia",
     "vocab": ["Rodzina i relacje", "Dzieciństwo i szkoła"],
     "grammar": ["G-PRAET", "G-WENN-ALS-OB"], "speaking": "S-OPIS",
     "task": "Opowiedz o ważnym wydarzeniu z dzieciństwa"},
    {"id": "M08", "phase": "Uzasadniam i porównuję", "theme": "Praca i zawód",
     "vocab": ["Mój zawód i obowiązki", "Szukanie pracy"],
     "grammar": ["G-WEIL-DASS", "G-KONNEKT"], "speaking": "S-T2",
     "task": "Przedstaw temat „Praca w domu czy w biurze?”: doświadczenie, sytuacja w Polsce, zalety, wady, opinia"},
    {"id": "M09", "phase": "Uzasadniam i porównuję", "theme": "Nauka i kursy",
     "vocab": ["Szkoła, studia, kursy", "Nauka języków"],
     "grammar": ["G-ZU", "G-ZU"], "speaking": "S-T1",
     "task": "Zaplanuj z kolegą weekendowy kurs językowy: termin, dojazd, nocleg, koszty"},
    {"id": "M10", "phase": "Uzasadniam i porównuję", "theme": "Relacje i święta",
     "vocab": ["Przyjaciele i znajomi", "Święta i uroczystości"],
     "grammar": ["G-K2", "G-K2"], "speaking": "S-T1",
     "task": "Zaplanuj z kolegą przyjęcie urodzinowe dla wspólnej znajomej"},
    {"id": "M11", "phase": "Uzasadniam i porównuję", "theme": "Media i technologia",
     "vocab": ["Telefon i internet", "Media społecznościowe i wiadomości"],
     "grammar": ["G-KOMP", "G-KONNEKT"], "speaking": "S-T2",
     "task": "Przedstaw temat „Smartfon dla dzieci?”: doświadczenie, sytuacja w Polsce, zalety, wady, opinia"},
    {"id": "M12", "phase": "Uzasadniam i porównuję", "theme": "Usługi i urzędy",
     "vocab": ["Bank, poczta, urząd", "Reklamacja i naprawa"],
     "grammar": ["G-WENN-ALS-OB", "G-K2"], "speaking": "S-PROBLEM",
     "task": "Złóż reklamację wadliwego produktu i grzecznie poproś o rozwiązanie"},
    {"id": "M13", "phase": "Uzasadniam i porównuję", "theme": "Miasto i środowisko",
     "vocab": ["Życie w mieście i na wsi", "Ekologia na co dzień"],
     "grammar": ["G-REL", "G-REL"], "speaking": "S-T2",
     "task": "Przedstaw temat „Samochód w mieście – potrzebny czy nie?”: doświadczenie, sytuacja w Polsce, zalety, wady, opinia"},
    {"id": "M14", "phase": "Uzasadniam i porównuję", "theme": "Życie w innym kraju",
     "vocab": ["Przeprowadzka i formalności", "Kultura i zwyczaje"],
     "grammar": ["G-ADJ", "G-ADJ"], "speaking": "S-OPINIA",
     "task": "Powiedz, co Ci się podoba, a co nie w życiu w Niemczech i dlaczego"},
    {"id": "M15", "phase": "Rozmawiam swobodnie", "theme": "Zmiany w życiu (powrót: codzienność)",
     "vocab": ["Przeprowadzki i nowe początki", "Plany na przyszłość"],
     "grammar": ["G-TEMP", "G-PRAET"], "speaking": "S-OPIS",
     "task": "Opowiedz o dużej zmianie w swoim życiu: co było przedtem, co potem"},
    {"id": "M16", "phase": "Rozmawiam swobodnie", "theme": "Konsumpcja (powrót: zakupy)",
     "vocab": ["Zakupy w internecie", "Produkcja i jakość"],
     "grammar": ["G-PASSIV", "G-KOMP"], "speaking": "S-T2",
     "task": "Przedstaw temat „Zakupy w internecie czy w sklepie?”: doświadczenie, sytuacja w Polsce, zalety, wady, opinia"},
    {"id": "M17", "phase": "Rozmawiam swobodnie", "theme": "Kariera (powrót: praca)",
     "vocab": ["Rozmowa o pracę", "Marzenia zawodowe"],
     "grammar": ["G-K2", "G-ZU"], "speaking": "S-T3",
     "task": "Odpowiedz na pytania o swoje plany zawodowe i uzasadnij wybory"},
    {"id": "M18", "phase": "Rozmawiam swobodnie", "theme": "Zdrowy tryb życia (powrót: zdrowie)",
     "vocab": ["Sport i ruch", "Odżywianie i sen"],
     "grammar": ["G-KONNEKT", "G-REFL"], "speaking": "S-OPINIA",
     "task": "Powiedz, co robisz dla zdrowia, mimo czego i dlaczego"},
    {"id": "M19", "phase": "Rozmawiam swobodnie", "theme": "Wyjazd (powrót: podróże)",
     "vocab": ["Planowanie urlopu", "Problemy w podróży"],
     "grammar": ["G-WECHSEL", "G-DAT"], "speaking": "S-T1",
     "task": "Zaplanuj z kolegą wspólny tygodniowy urlop: dokąd, czym, gdzie śpicie, budżet"},
    {"id": "M20", "phase": "Rozmawiam swobodnie", "theme": "Społeczeństwo (powrót: media)",
     "vocab": ["Wolontariat i sąsiedztwo", "Wiadomości i debaty"],
     "grammar": ["G-REL", "G-PASSIV"], "speaking": "S-T3",
     "task": "Odpowiedz na pytania o pomaganie innym i swoje zdanie o tym"},
    {"id": "M21", "phase": "Rozmawiam swobodnie", "theme": "Mój styl życia",
     "vocab": ["Wartości i przyzwyczajenia", "Porównanie: Polska i Niemcy"],
     "grammar": ["G-ADJ", "G-WENN-ALS-OB"], "speaking": "S-T3",
     "task": "Rozmowa bez przygotowania o swoim stylu życia"},
    {"id": "M22", "phase": "Próbne egzaminy", "theme": "Powtórka całości",
     "vocab": ["Słownictwo z całego programu", "Słownictwo z całego programu"],
     "grammar": ["G-KONNEKT", "G-K2"], "speaking": "S-T2",
     "task": "Pełny próbny egzamin ustny: planowanie, prezentacja, pytania"},
]

# Two-week rhythm (report section 5): days 1–2 new material and listening,
# 3–5 the spoken task with correction, 6 the same task faster (fluency),
# 7 mini-test and own-error list. Every 3rd module ends with a mock exam.
DAY_TYPES = ["nowy_material", "nowy_material", "zadanie_mowione", "zadanie_mowione",
             "zadanie_mowione", "plynnosc", "test_bledy"]
DAY_TYPE_PROMPT = {
    "nowy_material": "New material day: introduce the grammar point and the vocabulary; listening/reading text; short speaking at the end.",
    "zadanie_mowione": "Speaking-task day: most of the lesson prepares and practises the module task out loud; explicit correction after each attempt.",
    "plynnosc": "Fluency day: no new grammar; the learner repeats the same module task 3 times with less time (e.g. 90/60/45 s) using known words only.",
    "test_bledy": "Mini-test day: short test of this week's skills and a review of the learner's own recent mistakes; little new vocabulary.",
    "probny_egzamin": "Mock speaking exam day: plan together (Teil 1), present a topic in 5 points (Teil 2), answer questions (Teil 3); 15 minutes of preparation first.",
    "naprawa": "Repair day (mastery gate): the learner has not mastered the skills below yet. No new grammar; re-teach them another way (new examples, a contrast with the learner's own wrong forms), then retrieval practice and the module task again.",
}
DAY_TYPE_PL = {
    "nowy_material": "nowy materiał", "zadanie_mowione": "zadanie mówione",
    "plynnosc": "płynność", "test_bledy": "test i własne błędy",
    "probny_egzamin": "próbny egzamin ustny", "naprawa": "powtórka naprawcza",
}

SKILL_ID_RE = re.compile(r"\b([GS]-[A-Z0-9]+(?:-[A-Z0-9]+)*)\b")


def find_skill_id(text: str | None) -> str | None:
    """The first catalog id written in ``text`` (alone or inside a longer tag), else None."""
    for match in SKILL_ID_RE.findall(str(text or "")):
        if match in SKILLS:
            return match
    return None


def module_index(module_id: str | None) -> int | None:
    for i, m in enumerate(MODULES):
        if m["id"] == module_id:
            return i
    return None


def skill_name(skill_id: str) -> str:
    return SKILLS[skill_id][1]


def module_days(module: dict, index: int) -> list[dict]:
    """The 14 plan entries of one module (without the day numbers)."""
    days = []
    for i in range(DAYS_PER_MODULE):
        week = i // 7
        day_type = DAY_TYPES[i % 7]
        if i == DAYS_PER_MODULE - 1 and index % 3 == 0 and index > 0:
            day_type = "probny_egzamin"
        elif module["id"] == "M22" and day_type == "zadanie_mowione":
            day_type = "probny_egzamin"  # the last module rehearses the whole exam
        grammar_id = module["grammar"][week]
        if day_type == "probny_egzamin":
            conversation = "Próbny egzamin ustny w formacie B1 (3 części)"
        elif day_type in ("zadanie_mowione", "plynnosc"):
            conversation = module["task"]
        else:
            conversation = f"{skill_name(module['speaking'])}: {module['vocab'][week]}"
        days.append({
            "module_id": module["id"],
            "phase": module["phase"],
            "day_in_module": i + 1,
            "day_type": day_type,
            "day_type_pl": DAY_TYPE_PL[day_type],
            "grammar_topic": skill_name(grammar_id),
            "vocabulary_theme": f"{module['theme']}: {module['vocab'][week]}",
            "conversation_topic": conversation,
            "skill_ids": [grammar_id, module["speaking"]],
            "module_task": module["task"],
        })
    return days


def build_curriculum_plan(start_day: int = 1, cefr_level: str = "A2") -> dict:
    """Study plan in the stored shape (``daily_topics``, ``weekly_goals``,
    ``overall_goal``) whose day numbers start at ``start_day`` — the next lesson
    number — so a learner who already has lessons continues without a gap."""
    daily, weekly = [], []
    day = start_day
    for index, module in enumerate(MODULES):
        for entry in module_days(module, index):
            daily.append({"day": day, **entry})
            day += 1
        for week in (0, 1):
            weekly.append({
                "week": len(weekly) + 1,
                "module_id": module["id"],
                "goal": module["task"],
                "key_grammar": skill_name(module["grammar"][week]),
                "vocabulary_count": None,  # new cards come from the lessons, limited by the hub
            })
    return {
        "language": "German",
        "cefr_level": cefr_level,
        "curriculum_id": CURRICULUM_ID,
        "start_day": start_day,
        "daily_topics": daily,
        "weekly_goals": weekly,
        "skills": {k: {"kind": v[0], "name": v[1]} for k, v in SKILLS.items()},
        "overall_goal": ("Mówienie na poziomie B1: swobodna rozmowa o codziennych sprawach, "
                         "opowiadanie o doświadczeniach, planowanie z drugą osobą i uzasadnianie opinii."),
    }


def uses_curriculum(language: str, cefr_level: str) -> bool:
    """The curriculum covers German from A2 to B1 only; other cases keep the model's plan."""
    return (language or "").lower() in ("german", "niemiecki", "de") and cefr_level in ("A2", "B1")


def grammar_catalog_prompt(language: str) -> str:
    """Prompt line asking an error analysis to tag each error with a catalog
    grammar id. Empty for languages the catalog does not cover."""
    if (language or "").lower() not in ("german", "niemiecki", "de"):
        return ""
    ids = ", ".join(f"{k} ({v[1]})" for k, v in SKILLS.items() if v[0] == "grammar")
    return ('\nFor every error also give "skill_id": the one grammar id from this list that the '
            f'error breaks, or null if none fits: {ids}\n')
