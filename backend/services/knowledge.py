"""Bank wiedzy: one entry per curriculum skill (21.10.2026).

Before this the "Bank wiedzy" page showed topics the model extracted from each
lesson: 30 on 17.10.2026, with duplicates under different names (5 for the
present tense), names in two languages, one sentence of text each, none reviewed
and none linked to the plan or to errors.

Now every skill id of services/curriculum.py has one entry with a short rule,
examples with a translation and the typical errors of Polish speakers. The entry
is a Topic row with ``skill_id`` (``sync_knowledge_base``), so the existing page,
tree and lesson links keep working. What changes over time is not stored in the
entry but computed when it is read (``entry_details``): the days of the active
plan that practise the skill (so a new plan or a repair day shows at once), the
mastery status and the learner's own recent errors. Old model-made topics are
not deleted; they are moved under the entry they belong to.

Content: standard German grammar at A1–B1 as in the Goethe-Institut and
Grimm Grammar (University of Texas, CC BY) descriptions; the speaking entries
follow the published format of the Goethe-Zertifikat B1 Sprechen (Teil 1 plan
together, Teil 2 present a topic, Teil 3 react to the partner's presentation).
The rules and examples were written for this file, not copied.
"""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.exercise import Exercise
from backend.models.skill_attempt import SkillAttempt
from backend.models.study_plan import StudyPlan
from backend.models.topic import Topic, TopicItem
from backend.services.curriculum import MODULES, SKILLS, skill_name

# Umbrella entries of the tree, in the order a learner meets them
GROUPS: dict[str, tuple[str, str]] = {
    "szyk": ("grammar", "Szyk zdania i zdania złożone"),
    "czasowniki": ("grammar", "Czasowniki i czasy"),
    "przypadki": ("grammar", "Rodzajniki, przypadki i przyimki"),
    "przymiotniki": ("grammar", "Przymiotniki i porównania"),
    "mowienie": ("speaking", "Mówienie: zadania egzaminu B1"),
    "slownictwo": ("vocabulary", "Słownictwo (tematy ze starych lekcji)"),
    "inne": ("grammar", "Inne tematy gramatyczne (ze starych lekcji)"),
}
_ON_DEMAND = {"inne"}  # created only when an old topic needs it

# skill id -> group, rule, examples (German, Polish), typical errors of Polish speakers
KNOWLEDGE: dict[str, dict] = {
    "G-PRAES": {
        "group": "czasowniki",
        "rule": "Czasownik w czasie teraźniejszym dostaje końcówkę osoby: ich -e, du -st, er/sie/es -t, "
                "wir -en, ihr -t, sie/Sie -en. Sein i haben są nieregularne: ich bin, du bist, er ist; "
                "ich habe, du hast, er hat. Część czasowników zmienia samogłoskę w 2. i 3. osobie "
                "liczby pojedynczej: fahren → du fährst, essen → er isst.",
        "examples": [("Ich wohne in Krakau.", "Mieszkam w Krakowie."),
                     ("Du hast heute frei.", "Masz dziś wolne."),
                     ("Er fährt mit dem Zug.", "On jedzie pociągiem.")],
        "errors": ["„du habst” zamiast du hast", "„er fahrt” zamiast er fährt",
                   "pominięcie końcówki: „ich wohn”"],
    },
    "G-ARTIKEL": {
        "group": "przypadki",
        "rule": "Każdy rzeczownik ma rodzaj: der (męski), die (żeński), das (nijaki); w liczbie mnogiej "
                "zawsze die. Rodzajnik nieokreślony: ein (der, das), eine (die). Rodzaj często różni się "
                "od polskiego, dlatego rzeczownik uczy się razem z rodzajnikiem. Pomaga kilka końcówek: "
                "-ung, -heit, -keit → die; -chen → das.",
        "examples": [("der Tisch, die Lampe, das Fenster", "stół, lampa, okno"),
                     ("Das ist eine Wohnung.", "To jest mieszkanie."),
                     ("Das Mädchen ist nett.", "Dziewczyna jest miła (das, bo -chen).")],
        "errors": ["rodzaj przeniesiony z polskiego: „der Auto” (samochód) zamiast das Auto, "
                   "„das Sonne” (słońce) zamiast die Sonne", "„der Mädchen” zamiast das Mädchen",
                   "brak rodzajnika: „Ich habe Auto”"],
    },
    "G-V2": {
        "group": "szyk",
        "rule": "W zdaniu oznajmującym odmieniony czasownik stoi zawsze na 2. miejscu. Jeśli zdanie zaczyna "
                "się od czegoś innego niż podmiot (czas, miejsce, dopełnienie), podmiot przechodzi za "
                "czasownik (inwersja). W pytaniu bez słowa pytającego czasownik jest na 1. miejscu.",
        "examples": [("Ich arbeite heute zu Hause.", "Pracuję dziś w domu."),
                     ("Heute arbeite ich zu Hause.", "Dziś pracuję w domu (inwersja)."),
                     ("Arbeitest du heute?", "Pracujesz dziś?")],
        "errors": ["„Heute ich arbeite” zamiast Heute arbeite ich",
                   "„Gestern ich habe gearbeitet” zamiast Gestern habe ich gearbeitet"],
    },
    "G-TRENN": {
        "group": "czasowniki",
        "rule": "Czasownik z akcentowanym przedrostkiem (auf-, ein-, an-, mit-, zurück-…) rozdziela się: "
                "odmieniona część stoi na 2. miejscu, przedrostek idzie na koniec zdania. W zdaniu "
                "podrzędnym i w bezokoliczniku czasownik jest znowu w całości, a w Perfekt -ge- wchodzi "
                "między przedrostek a rdzeń.",
        "examples": [("Ich stehe um sieben Uhr auf.", "Wstaję o siódmej."),
                     ("Kaufst du heute ein?", "Robisz dziś zakupy?"),
                     ("Ich bin um sieben aufgestanden.", "Wstałem o siódmej.")],
        "errors": ["„Ich aufstehe um sieben”", "przedrostek nie na końcu: „Ich stehe auf um sieben” "
                   "(możliwe tylko w mowie potocznej)", "„geaufstanden” zamiast aufgestanden"],
    },
    "G-MODAL": {
        "group": "czasowniki",
        "rule": "Czasownik modalny (können, müssen, wollen, dürfen, sollen, mögen/möchten) stoi na 2. miejscu, "
                "a drugi czasownik w bezokoliczniku na końcu zdania, bez zu. W 1. i 3. osobie liczby "
                "pojedynczej modalne nie mają końcówki: ich kann, er muss.",
        "examples": [("Ich kann heute nicht kommen.", "Nie mogę dziś przyjść."),
                     ("Du musst den Arzt anrufen.", "Musisz zadzwonić do lekarza."),
                     ("Hier darf man nicht rauchen.", "Tu nie wolno palić.")],
        "errors": ["„Ich kann nicht kommen heute”", "„er kannt” zamiast er kann",
                   "„Ich muss zu arbeiten” (z modalnym bez zu)",
                   "„nicht müssen” w znaczeniu „nie wolno”: nicht müssen = nie trzeba, nicht dürfen = nie wolno"],
    },
    "G-AKK": {
        "group": "przypadki",
        "rule": "Biernik (Akkusativ) to dopełnienie bliższe: kogo? co? Zmienia się tylko rodzaj męski: "
                "der → den, ein → einen, kein → keinen; die, das i liczba mnoga zostają. Zaimki: "
                "mich, dich, ihn, sie, es, uns, euch, sie/Sie. Biernik wymagają m.in. haben, brauchen, "
                "sehen, kaufen, es gibt i przyimki durch, für, gegen, ohne, um.",
        "examples": [("Ich habe einen Bruder.", "Mam brata."),
                     ("Ich sehe den Bus.", "Widzę autobus."),
                     ("Das Geschenk ist für dich.", "Prezent jest dla ciebie.")],
        "errors": ["„Ich habe ein Bruder”", "„Es gibt ein Supermarkt” zamiast einen Supermarkt",
                   "„für du” zamiast für dich"],
    },
    "G-DAT": {
        "group": "przypadki",
        "rule": "Celownik (Dativ) odpowiada na pytanie komu? czemu? Rodzajniki: dem (der, das), der (die), "
                "den + -n (liczba mnoga: den Kindern); ein → einem/einer. Zaimki: mir, dir, ihm, ihr, ihm, "
                "uns, euch, ihnen/Ihnen. Celownik zawsze po aus, bei, mit, nach, seit, von, zu oraz po "
                "czasownikach helfen, danken, gefallen, gehören, antworten.",
        "examples": [("Ich gebe dem Mann das Buch.", "Daję mężczyźnie książkę."),
                     ("Ich fahre mit der Bahn.", "Jadę koleją."),
                     ("Kannst du mir helfen?", "Możesz mi pomóc?")],
        "errors": ["„mit der Mann” zamiast mit dem Mann", "„Ich helfe dich” zamiast Ich helfe dir",
                   "„mit meine Freunde” zamiast mit meinen Freunden"],
    },
    "G-WECHSEL": {
        "group": "przypadki",
        "rule": "Przyimki in, an, auf, über, unter, vor, hinter, neben, zwischen łączą się z celownikiem, gdy "
                "chodzi o miejsce (wo? gdzie?), i z biernikiem, gdy o kierunek ruchu (wohin? dokąd?). "
                "Pary czasowników: liegen/legen, stehen/stellen, sitzen/setzen, hängen.",
        "examples": [("Das Buch liegt auf dem Tisch.", "Książka leży na stole (wo? Dativ)."),
                     ("Ich lege das Buch auf den Tisch.", "Kładę książkę na stół (wohin? Akkusativ)."),
                     ("Wir gehen ins Kino. Wir sind im Kino.", "Idziemy do kina. Jesteśmy w kinie.")],
        "errors": ["„Ich gehe in dem Park” zamiast in den Park",
                   "„Das Bild hängt an die Wand” zamiast an der Wand"],
    },
    "G-PERFEKT": {
        "group": "czasowniki",
        "rule": "Perfekt = haben albo sein na 2. miejscu + imiesłów (Partizip II) na końcu. Sein mają "
                "czasowniki ruchu i zmiany stanu (gehen, fahren, kommen, aufstehen, werden) oraz sein i "
                "bleiben; pozostałe haben. Imiesłów: ge- + rdzeń + -t (gemacht) lub nieregularny ge- … -en "
                "(gefahren); bez ge- po -ieren i przedrostkach be-, ver-, er- (studiert, besucht).",
        "examples": [("Ich habe gestern lange gearbeitet.", "Wczoraj długo pracowałem."),
                     ("Wir sind nach Berlin gefahren.", "Pojechaliśmy do Berlina."),
                     ("Sie hat Medizin studiert.", "Studiowała medycynę.")],
        "errors": ["„Ich habe nach Berlin gefahren” zamiast bin … gefahren",
                   "„Ich habe gearbeitet gestern” (imiesłów nie na końcu)", "„gestudiert” zamiast studiert"],
    },
    "G-REFL": {
        "group": "czasowniki",
        "rule": "Czasownik zwrotny ma zaimek sich w odpowiedniej osobie: ich mich, du dich, er/sie sich, "
                "wir uns, ihr euch, sie sich. Gdy jest też dopełnienie w bierniku, zaimek przechodzi "
                "w celownik: ich wasche mich, ale ich wasche mir die Hände. Niektóre czasowniki są zwrotne "
                "tylko po niemiecku (sich beeilen, sich erinnern an + Akk.).",
        "examples": [("Ich freue mich auf das Wochenende.", "Cieszę się na weekend."),
                     ("Du musst dich beeilen.", "Musisz się pospieszyć."),
                     ("Ich putze mir die Zähne.", "Myję zęby.")],
        "errors": ["„Ich freue sich” zamiast mich", "pominięcie zaimka: „Ich erinnere an dich”",
                   "„Ich wasche mich die Hände” zamiast mir die Hände"],
    },
    "G-WEIL-DASS": {
        "group": "szyk",
        "rule": "Po weil (bo, ponieważ) i dass (że) zaczyna się zdanie podrzędne: odmieniony czasownik idzie "
                "na sam koniec, przed nim przecinek. Czasownik rozdzielny łączy się z powrotem "
                "(…, weil ich früh aufstehe). Gdy zdanie podrzędne stoi pierwsze, zdanie główne zaczyna "
                "się od czasownika.",
        "examples": [("Ich lerne Deutsch, weil ich in Wien arbeiten möchte.",
                      "Uczę się niemieckiego, bo chcę pracować w Wiedniu."),
                     ("Ich glaube, dass er recht hat.", "Myślę, że on ma rację."),
                     ("Weil es regnet, bleibe ich zu Hause.", "Ponieważ pada, zostaję w domu.")],
        "errors": ["„weil ich möchte in Wien arbeiten”", "„Ich denke, dass er hat recht”",
                   "„Weil es regnet, ich bleibe zu Hause”"],
    },
    "G-WENN-ALS-OB": {
        "group": "szyk",
        "rule": "Wenn = gdy/kiedy (powtarzalnie lub w przyszłości) i jeśli; als = kiedy (jedno zdarzenie "
                "w przeszłości); ob = czy (pytanie pośrednie). Pytanie pośrednie ze słowem pytającym: "
                "Ich weiß nicht, wo er wohnt. Wszystkie te zdania mają czasownik na końcu.",
        "examples": [("Wenn ich Zeit habe, rufe ich dich an.", "Jeśli będę miał czas, zadzwonię."),
                     ("Als ich zehn war, wohnten wir in Danzig.", "Kiedy miałem dziesięć lat, mieszkaliśmy w Gdańsku."),
                     ("Weißt du, ob der Laden heute offen ist?", "Wiesz, czy sklep jest dziś otwarty?")],
        "errors": ["„Wenn ich zehn war” o jednym zdarzeniu z przeszłości (powinno być als)",
                   "„Ich weiß nicht, wenn er kommt” w znaczeniu „czy” (powinno być ob)",
                   "„Ich weiß nicht, wo wohnt er”"],
    },
    "G-PRAET": {
        "group": "czasowniki",
        "rule": "W mowie o przeszłości Niemcy używają głównie Perfekt, ale sein, haben i czasowniki modalne "
                "zwykle w Präteritum: ich war, ich hatte, ich konnte, ich musste, ich wollte. W 1. i 3. osobie "
                "liczby pojedynczej brak końcówki: ich war, er war. Präteritum jest też w tekstach "
                "pisanych i opowiadaniach.",
        "examples": [("Gestern war ich krank.", "Wczoraj byłem chory."),
                     ("Ich hatte keine Zeit.", "Nie miałem czasu."),
                     ("Wir mussten lange warten.", "Musieliśmy długo czekać.")],
        "errors": ["„Ich habe Zeit gehabt”: poprawne, ale w mowie zwykle mówi się Ich hatte Zeit",
                   "Perfekt modalnego ze złym szykiem: „Ich habe müssen arbeiten” zamiast Ich musste arbeiten",
                   "„er musstet” zamiast er musste"],
    },
    "G-KONNEKT": {
        "group": "szyk",
        "rule": "Łączniki działają na trzy sposoby. Und, aber, oder, denn (bo) stoją na pozycji 0: szyk się "
                "nie zmienia. Deshalb (dlatego), trotzdem (mimo to), dann zajmują 1. miejsce, więc czasownik "
                "jest zaraz po nich (inwersja). Obwohl (chociaż) i weil zaczynają zdanie podrzędne "
                "z czasownikiem na końcu.",
        "examples": [("Ich bleibe zu Hause, denn ich bin müde.", "Zostaję w domu, bo jestem zmęczony."),
                     ("Ich bin müde, deshalb bleibe ich zu Hause.", "Jestem zmęczony, dlatego zostaję w domu."),
                     ("Obwohl ich müde bin, gehe ich mit.", "Chociaż jestem zmęczony, idę z wami.")],
        "errors": ["„deshalb ich bleibe”", "„denn ich müde bin” (po denn zwykły szyk)",
                   "„Obwohl ich bin müde”"],
    },
    "G-ZU": {
        "group": "szyk",
        "rule": "Po wielu czasownikach i zwrotach (versuchen, vergessen, anfangen, Lust haben, es ist wichtig) "
                "drugi czasownik idzie na koniec z zu: zu lernen; przy rozdzielnych zu w środku: "
                "anzurufen. Um … zu = żeby (cel), gdy podmiot jest ten sam; przy innym podmiocie damit.",
        "examples": [("Ich habe vergessen, dich anzurufen.", "Zapomniałem do ciebie zadzwonić."),
                     ("Es ist wichtig, regelmäßig zu üben.", "Ważne jest regularne ćwiczenie."),
                     ("Ich lerne Deutsch, um in Österreich zu arbeiten.", "Uczę się niemieckiego, żeby pracować w Austrii.")],
        "errors": ["„Ich versuche lernen” bez zu", "„zu anrufen” zamiast anzurufen",
                   "„für zu arbeiten” zamiast um … zu", "zu po czasowniku modalnym: „Ich kann zu schwimmen”"],
    },
    "G-K2": {
        "group": "czasowniki",
        "rule": "Konjunktiv II wyraża życzenie, uprzejmą prośbę, radę i sytuację nierealną. Formy: würde + "
                "bezokolicznik (ich würde gern reisen), wäre, hätte, könnte, sollte. Prośba: Könnten Sie …? "
                "Rada: Du solltest … Propozycja: Wir könnten … Warunek nierealny: Wenn ich Zeit hätte, "
                "würde ich kommen.",
        "examples": [("Könnten Sie mir bitte helfen?", "Czy mógłby mi pan pomóc?"),
                     ("Wir könnten am Samstag ins Kino gehen.", "Moglibyśmy w sobotę pójść do kina."),
                     ("Wenn ich mehr Zeit hätte, würde ich mehr lesen.", "Gdybym miał więcej czasu, czytałbym więcej.")],
        "errors": ["„Wenn ich mehr Zeit habe, würde ich …” (pomieszanie trybów)",
                   "„ich würde sein” zamiast ich wäre", "prośba bez trybu: „Können Sie …” brzmi mniej uprzejmie"],
    },
    "G-KOMP": {
        "group": "przymiotniki",
        "rule": "Stopień wyższy: -er (schneller), najwyższy: am -sten (am schnellsten) lub der/die/das -ste. "
                "Krótkie przymiotniki często dostają przegłos: alt → älter, groß → größer. Nieregularne: "
                "gut, besser, am besten; viel, mehr, am meisten; gern, lieber, am liebsten. Porównanie: "
                "größer als (większy niż), so groß wie (tak duży jak).",
        "examples": [("Berlin ist größer als München.", "Berlin jest większy niż Monachium."),
                     ("Der Zug ist so schnell wie das Auto.", "Pociąg jest tak szybki jak samochód."),
                     ("Am liebsten trinke ich Tee.", "Najchętniej piję herbatę.")],
        "errors": ["„größer wie” zamiast größer als", "„mehr gut” zamiast besser",
                   "„am größte” zamiast am größten"],
    },
    "G-REL": {
        "group": "szyk",
        "rule": "Zdanie względne dopowiada coś o rzeczowniku. Zaimek względny ma rodzaj i liczbę rzeczownika, "
                "a przypadek bierze ze swojego zdania: der, den, dem; die, der; das, dem; mnoga die, denen. "
                "Czasownik idzie na koniec, a zdanie względne oddziela się przecinkami.",
        "examples": [("Das ist der Mann, der neben mir wohnt.", "To jest mężczyzna, który mieszka obok mnie."),
                     ("Das ist der Film, den ich gesehen habe.", "To jest film, który widziałem."),
                     ("Die Kollegin, mit der ich arbeite, ist nett.", "Koleżanka, z którą pracuję, jest miła.")],
        "errors": ["„der Film, der ich gesehen habe” zamiast den", "„was” zamiast das po rzeczowniku: "
                   "„das Buch, was ich lese”", "czasownik nie na końcu: „der Mann, der wohnt neben mir”"],
    },
    "G-ADJ": {
        "group": "przymiotniki",
        "rule": "Przymiotnik przed rzeczownikiem dostaje końcówkę. Po der/die/das: -e w mianowniku liczby "
                "pojedynczej (i w bierniku die/das), w pozostałych -en (der alte Mann, den alten Mann). Po "
                "ein/kein/mein przymiotnik przejmuje sygnał rodzaju: ein alter Mann, ein altes Haus, "
                "eine alte Frau. Bez rodzajnika końcówki jak rodzajnik: kalter Kaffee, frisches Brot.",
        "examples": [("Ich suche eine große Wohnung.", "Szukam dużego mieszkania."),
                     ("Das ist ein neues Auto.", "To jest nowy samochód."),
                     ("Ich spreche mit dem netten Nachbarn.", "Rozmawiam z miłym sąsiadem.")],
        "errors": ["„ein neue Auto” zamiast ein neues Auto", "„mit dem nette Nachbarn”",
                   "końcówka po orzeczeniu: „Das Auto ist neues” (po sein bez końcówki)"],
    },
    "G-TEMP": {
        "group": "szyk",
        "rule": "Bevor (zanim), nachdem (po tym jak), während (podczas gdy), seit (odkąd), bis (aż) zaczynają "
                "zdanie podrzędne z czasownikiem na końcu. Po nachdem czas jest „o krok wcześniejszy”: "
                "Perfekt przy teraźniejszym w zdaniu głównym, Plusquamperfekt przy przeszłym.",
        "examples": [("Bevor ich frühstücke, gehe ich joggen.", "Zanim zjem śniadanie, idę pobiegać."),
                     ("Nachdem ich gegessen habe, trinke ich Kaffee.", "Po tym jak zjem, piję kawę."),
                     ("Seit ich in Berlin wohne, fahre ich Rad.", "Odkąd mieszkam w Berlinie, jeżdżę na rowerze.")],
        "errors": ["„Bevor ich frühstücke, ich gehe joggen”", "„nachdem ich esse” (brak wcześniejszego czasu)",
                   "pomylenie während (podczas gdy) z wenn"],
    },
    "G-PASSIV": {
        "group": "czasowniki",
        "rule": "Strona bierna (Vorgangspassiv): werden w odpowiedniej osobie na 2. miejscu + imiesłów na końcu: "
                "Das Haus wird gebaut. Wykonawcę można dodać przez von + celownik. Strona bierna jest częsta "
                "w opisach procesów i informacjach („Hier wird nicht geraucht”).",
        "examples": [("Die Post wird morgens gebracht.", "Pocztę przynosi się rano."),
                     ("Das Formular wird online ausgefüllt.", "Formularz wypełnia się online."),
                     ("Der Brief wird von der Sekretärin geschrieben.", "List pisze sekretarka.")],
        "errors": ["„Das Haus ist gebaut” w znaczeniu procesu (to stan, Zustandspassiv)",
                   "von … po imiesłowie: „Der Brief wird geschrieben von der Sekretärin” zamiast "
                   "wird von der Sekretärin geschrieben", "„er werdet” zamiast er wird"],
    },
    "S-OPIS": {
        "group": "mowienie",
        "rule": "Opowiadanie o zdarzeniu: kolejność (zuerst, dann, danach, am Ende), czas przeszły (Perfekt, "
                "a war/hatte w Präteritum), szczegóły (wann, wo, mit wem) i ocena na końcu (Es war toll, "
                "weil …). Cel B1: kilka połączonych zdań bez dłuższych przerw.",
        "examples": [("Zuerst sind wir an den See gefahren, danach haben wir gegrillt.",
                      "Najpierw pojechaliśmy nad jezioro, potem grillowaliśmy."),
                     ("Am Ende war ich müde, aber es hat Spaß gemacht.", "Na koniec byłem zmęczony, ale było fajnie.")],
        "errors": ["same zdania „und dann … und dann”", "czas teraźniejszy w opowieści o przeszłości",
                   "brak oceny i uzasadnienia na końcu"],
    },
    "S-T1": {
        "group": "mowienie",
        "rule": "Jak Teil 1 egzaminu B1 (gemeinsam etwas planen): z partnerem planujecie coś (wycieczkę, "
                "prezent, spotkanie). Proponuj (Wir könnten …, Was hältst du von …?), reaguj (Gute Idee! / "
                "Das finde ich nicht so gut, weil …), dopytuj (Wann passt es dir?) i doprowadź do decyzji "
                "(Also machen wir es so: …). Liczy się rozmowa w obie strony, nie monolog.",
        "examples": [("Wir könnten am Samstag zusammen kochen. Was meinst du?",
                      "Moglibyśmy w sobotę razem gotować. Co myślisz?"),
                     ("Samstag passt mir leider nicht. Wie wäre es mit Sonntag?",
                      "Sobota niestety mi nie pasuje. Co powiesz na niedzielę?")],
        "errors": ["tylko propozycje, bez reakcji na partnera", "brak końcowej decyzji",
                   "„Ich will …” zamiast uprzejmego „Ich würde gern …”"],
    },
    "S-T2": {
        "group": "mowienie",
        "rule": "Jak Teil 2 egzaminu B1 (ein Thema präsentieren): prezentacja w 5 częściach: temat i plan, "
                "własne doświadczenie, sytuacja w twoim kraju, zalety i wady z własną opinią, zakończenie "
                "i podziękowanie. Zwroty porządkujące: Zuerst möchte ich …, Jetzt komme ich zu …, "
                "Zum Schluss …, Vielen Dank fürs Zuhören.",
        "examples": [("Ich möchte heute über das Thema „Homeoffice” sprechen.",
                      "Chciałbym dziś mówić o pracy z domu."),
                     ("Ein Vorteil ist …, ein Nachteil ist aber …", "Zaletą jest …, ale wadą jest …")],
        "errors": ["pominięcie części (najczęściej sytuacji w kraju albo opinii)",
                   "czytanie listy bez zdań łączących", "brak zakończenia"],
    },
    "S-T3": {
        "group": "mowienie",
        "rule": "Jak Teil 3 egzaminu B1 (über ein Thema sprechen): po prezentacji partnera daj krótką "
                "informację zwrotną (Danke, das war sehr interessant …) i zadaj jedno pytanie; potem "
                "odpowiedz na pytanie do twojej prezentacji z uzasadnieniem (weil, deshalb, zum Beispiel).",
        "examples": [("Danke für die Präsentation. Ich habe eine Frage: Wie ist das in deiner Firma?",
                      "Dziękuję za prezentację. Mam pytanie: jak to jest w twojej firmie?"),
                     ("Das ist eine gute Frage. Ich denke, dass …, weil …", "Dobre pytanie. Myślę, że …, ponieważ …")],
        "errors": ["odpowiedź jednym słowem bez uzasadnienia", "pytanie niezwiązane z prezentacją",
                   "brak informacji zwrotnej przed pytaniem"],
    },
    "S-PROBLEM": {
        "group": "mowienie",
        "rule": "Załatwianie sprawy (urząd, sklep, lekarz, wynajmujący): powitanie, opis problemu (Ich habe "
                "ein Problem mit …), prośba w trybie przypuszczającym (Könnten Sie …?), dopytanie o szczegóły "
                "(Bis wann …? Was muss ich mitbringen?) i potwierdzenie ustaleń.",
        "examples": [("Ich habe die Waschmaschine letzte Woche gekauft, aber sie funktioniert nicht.",
                      "Kupiłem pralkę w zeszłym tygodniu, ale nie działa."),
                     ("Könnten Sie sie bitte reparieren oder umtauschen?", "Czy mogliby ją państwo naprawić albo wymienić?")],
        "errors": ["żądanie zamiast prośby: „Sie müssen …”", "brak szczegółów (kiedy, co dokładnie)",
                   "brak potwierdzenia na koniec"],
    },
    "S-OPINIA": {
        "group": "mowienie",
        "rule": "Opinia z uzasadnieniem: zdanie (Ich finde / Ich bin der Meinung, dass …), powód (weil, denn), "
                "przykład (zum Beispiel), druga strona (Andererseits …) i wniosek (Deshalb …). "
                "Zgoda i niezgoda: Da hast du recht. / Da bin ich anderer Meinung.",
        "examples": [("Ich bin der Meinung, dass Homeoffice viele Vorteile hat, weil man Zeit spart.",
                      "Uważam, że praca z domu ma wiele zalet, bo oszczędza się czas."),
                     ("Andererseits fehlt der Kontakt mit Kollegen.", "Z drugiej strony brakuje kontaktu ze współpracownikami.")],
        "errors": ["opinia bez powodu", "„Ich bin der Meinung, dass Homeoffice hat Vorteile” (szyk po dass)",
                   "„Ich habe Meinung” zamiast Ich bin der Meinung"],
    },
}

# A1 basics no module teaches (services/curriculum.py): they come back through
# errors, the warm-up and the hub's deck, not through plan days
FOUNDATIONS = {s for s, (kind, _) in SKILLS.items()
               if kind == "grammar" and not any(s in m["grammar"] for m in MODULES)}

# Old model-made topic names -> skill, checked in order; vocabulary topics go to "slownictwo"
_OLD_TOPIC_RULES: list[tuple[str, re.Pattern]] = [
    ("G-V2", re.compile(r"satzstellung|verbposition|wortstellung|szyk|aussagesatz", re.I)),
    ("G-PERFEKT", re.compile(r"perfekt", re.I)),
    ("G-PRAES", re.compile(r"pr[äa]sens|konjugation|koniugac|czasownik|czasy tera|\bsein\b|'sein'|"
                           r"hei[ßs]en|regelm[äa][ßs]ig", re.I)),
    ("G-ARTIKEL", re.compile(r"geschlecht|artikel|rodzajnik|nominativ", re.I)),
    ("G-AKK", re.compile(r"akkusativ|biernik", re.I)),
    ("G-DAT", re.compile(r"dativ|celownik", re.I)),
    ("G-MODAL", re.compile(r"modal", re.I)),
    ("G-TRENN", re.compile(r"trennbar", re.I)),
    ("G-K2", re.compile(r"konjunktiv", re.I)),
]

_GROUP_PREFIX = Topic.KB_GROUP_PREFIX  # marks the umbrella rows this module owns


def old_topic_skill(name: str, category: str | None) -> str | None:
    """Catalog skill an old model-made topic belongs to, else None. The patterns
    name grammar only, so the model's category is not trusted ("Verb 'heißen'"
    was filed as vocabulary). Pronoun topics stay unassigned on purpose: personal
    pronouns are spread over AKK/DAT/PRAES."""
    for skill_id, pattern in _OLD_TOPIC_RULES:
        if pattern.search(name or ""):
            return skill_id
    return None


def sync_knowledge_base(db: Session, user_id: int, language: str, commit: bool = True) -> dict[str, Topic]:
    """Make sure the learner has one entry per skill (German only), refresh its
    text from this file and move old model-made topics under the right entry.
    Idempotent; never deletes. Returns {skill_id: Topic}."""
    if (language or "").lower() not in ("german", "niemiecki", "de"):
        return {}
    rows = db.query(Topic).filter(Topic.user_id == user_id, Topic.language == language).all()
    by_skill = {t.skill_id: t for t in rows if t.skill_id}
    groups = {t.name: t for t in rows if not t.skill_id and (t.name or "").startswith(_GROUP_PREFIX)}

    group_rows: dict[str, Topic] = {}
    entry_row_ids = {t.id for t in rows if t.skill_id}
    leftover_grammar = any(
        t.category == "grammar" and t.id not in entry_row_ids and not (t.name or "").startswith(_GROUP_PREFIX)
        and not old_topic_skill(t.name, t.category) for t in rows)
    for key, (category, title) in GROUPS.items():
        name = _GROUP_PREFIX + title
        row = groups.get(name)
        if row is None and key in _ON_DEMAND and not leftover_grammar:
            continue
        if row is None:
            row = Topic(user_id=user_id, language=language, name=name, category=category,
                        description=None, cefr_level="A2-B1")
            db.add(row)
            db.flush()
        group_rows[key] = row

    entries: dict[str, Topic] = {}
    for skill_id, (kind, name) in SKILLS.items():
        k = KNOWLEDGE[skill_id]
        row = by_skill.get(skill_id)
        if row is None:
            row = Topic(user_id=user_id, language=language, skill_id=skill_id,
                        category=kind, cefr_level="A2-B1")
            db.add(row)
        row.name = f"{name} [{skill_id}]"
        row.category = kind
        row.description = k["rule"]
        row.parent_id = group_rows[k["group"]].id
        entries[skill_id] = row
    db.flush()

    own_ids = {t.id for t in entries.values()} | {t.id for t in group_rows.values()}
    for t in rows:
        if t.id in own_ids or t.skill_id:
            continue
        skill_id = old_topic_skill(t.name, t.category)
        if skill_id:
            t.parent_id = entries[skill_id].id
        elif t.category == "vocabulary":
            t.parent_id = group_rows["slownictwo"].id
        elif t.category == "grammar" and "inne" in group_rows:
            t.parent_id = group_rows["inne"].id
    if commit:
        db.commit()
    else:
        db.flush()
    return entries


def learning_order() -> list[str]:
    """Skill ids in the order the programme first practises them; A1 basics first."""
    ids = dict.fromkeys(sorted(FOUNDATIONS))
    for m in MODULES:
        ids.update(dict.fromkeys((*m["grammar"], m["speaking"])))
    ids.update(dict.fromkeys(SKILLS))
    return list(ids)


def entry_details(db: Session, topic: Topic) -> dict | None:
    """Everything shown with an entry that changes over time, computed now: plan
    days that practise the skill (active plan), mastery, own recent errors and the
    review items of this skill."""
    skill_id = topic.skill_id
    if not skill_id or skill_id not in KNOWLEDGE:
        return None
    from backend.services.mastery import skill_mastery

    k = KNOWLEDGE[skill_id]
    plan = db.query(StudyPlan).filter(StudyPlan.user_id == topic.user_id,
                                      StudyPlan.language == topic.language,
                                      StudyPlan.is_active == True).first()  # noqa: E712
    days = []
    if plan:
        try:
            data = json.loads(plan.plan_data)
        except (TypeError, ValueError):
            data = {}
        for d in data.get("daily_topics") or []:
            if isinstance(d, dict) and skill_id in (d.get("skill_ids") or []):
                days.append({"day": d.get("day"), "module_id": d.get("module_id"),
                             "day_type_pl": d.get("day_type_pl"), "repair": d.get("day_type") == "naprawa"})
    from backend.models.lesson import Lesson
    done = {n for (n,) in db.query(Lesson.day_number).filter(
        Lesson.user_id == topic.user_id, Lesson.language == topic.language,
        Lesson.is_completed == True).all()}  # noqa: E712
    for d in days:
        d["done"] = d["day"] in done
    modules = list(dict.fromkeys(d["module_id"] for d in days if d["module_id"]))

    errors = []
    for a in db.query(SkillAttempt).filter(
            SkillAttempt.user_id == topic.user_id, SkillAttempt.language == topic.language,
            SkillAttempt.skill_id == skill_id, SkillAttempt.correct == False,  # noqa: E712
            SkillAttempt.detail.isnot(None)).order_by(SkillAttempt.occurred_at.desc()).limit(10).all():
        try:
            detail = json.loads(a.detail)
        except (TypeError, ValueError):
            continue
        errors.append({"wrong": detail.get("wrong"), "correct": detail.get("correct"),
                       "source": a.source, "at": a.occurred_at.isoformat()})

    items = db.query(Exercise).filter(Exercise.user_id == topic.user_id, Exercise.language == topic.language,
                                      Exercise.skill_id == skill_id, Exercise.is_active == True).count()  # noqa: E712
    return {
        "skill_id": skill_id,
        "skill_name": skill_name(skill_id),
        "group": GROUPS[k["group"]][1],
        "rule": k["rule"],
        "examples": [{"de": de, "pl": pl} for de, pl in k["examples"]],
        "typical_errors": k["errors"],
        "plan": {"modules": modules, "days": days, "foundation": skill_id in FOUNDATIONS,
                 "next_day": next((d["day"] for d in days if not d["done"]), None)},
        "mastery": skill_mastery(db, topic.user_id, topic.language).get(skill_id),
        "recent_errors": errors,
        "exercises": items,
    }


def entry_strength(mastery: dict | None) -> float:
    """0..1 shown as an entry's bar: first-try accuracy once there is enough data
    (services/mastery.py), else 0. Entries are not reviewed with topic FSRS: their
    items are reviewed in the hub's deck."""
    if not mastery or mastery.get("status") == "za_malo_danych":
        return 0.0
    return float(mastery.get("accuracy") or 0.0)


def rules_for_prompt(skill_ids: list[str] | None) -> str:
    """Today's knowledge-base rules for the lesson prompt, so the lesson explains a
    point the same way as the learner's Bank wiedzy (grammar entries only)."""
    lines = [f"{s}: {KNOWLEDGE[s]['rule']}" for s in (skill_ids or [])
             if s in KNOWLEDGE and SKILLS[s][0] == "grammar"]
    if not lines:
        return ""
    return ("\n  knowledge base (the learner's reference; explain consistently with it): "
            + " | ".join(lines))


SIMILAR_NAME = 0.9  # "Personalpronomina" / "Personalpronomen" = 0.91; different topics on 17.10 were below 0.6


def _name_key(name: str) -> str:
    """Lower case, words only, sorted: "Lebensmittel und Einkaufen" = "Einkaufen und Lebensmittel"."""
    return " ".join(sorted(re.findall(r"\w+", (name or "").lower())))


def find_duplicates(db: Session, user_id: int, language: str) -> list[dict]:
    """Old model-made topics that repeat something, after ``sync_knowledge_base``:

    - a topic mapped to a skill repeats that skill's entry (it goes into the entry);
    - two old topics of one category whose names are the same words or nearly the
      same (SIMILAR_NAME) repeat each other (the one with more items, then the
      older one, stays);
    - an old umbrella topic left with no items and no subtopics is empty.

    Topics with own reviews are never listed: their FSRS history would be lost.
    Returns [{"id", "name", "into_id", "into_name", "reason", "items"}], nothing changed."""
    rows = db.query(Topic).filter(Topic.user_id == user_id, Topic.language == language).all()
    by_id = {t.id: t for t in rows}
    entry_of = {t.skill_id: t for t in rows if t.skill_id}
    owned = {t.id for t in rows if t.skill_id or (t.name or "").startswith(_GROUP_PREFIX)}
    items = dict(db.query(TopicItem.topic_id, func.count(TopicItem.id)).filter(
        TopicItem.topic_id.in_(list(by_id) or [0])).group_by(TopicItem.topic_id).all())
    old = sorted((t for t in rows if t.id not in owned and not (t.total_reviews or 0)), key=lambda t: t.id)

    out, gone = [], set()

    def drop(t, into, reason):
        gone.add(t.id)
        out.append({"id": t.id, "name": t.name, "into_id": into.id if into else None,
                    "into_name": into.name if into else None, "reason": reason, "items": items.get(t.id, 0)})

    for t in old:
        skill_id = old_topic_skill(t.name, t.category)
        if skill_id and skill_id in entry_of:
            drop(t, entry_of[skill_id], f"to samo co wpis {skill_id}")
    rest = [t for t in old if t.id not in gone]
    for i, t in enumerate(rest):
        if t.id in gone:
            continue
        for other in rest[i + 1:]:
            if other.id in gone or other.category != t.category:
                continue
            a, b = _name_key(t.name), _name_key(other.name)
            if a == b or SequenceMatcher(None, a, b).ratio() >= SIMILAR_NAME:
                keep, dup = (t, other) if items.get(t.id, 0) >= items.get(other.id, 0) else (other, t)
                drop(dup, keep, "ta sama nazwa" if a == b else "prawie ta sama nazwa")
                if dup is t:
                    break
    for t in old:
        if t.id in gone or items.get(t.id, 0):
            continue
        if not any(c.parent_id == t.id and c.id not in gone for c in rows):
            drop(t, None, "pusty temat-parasol (0 lekcji, 0 podtematów)")
    return out


def merge_duplicates(db: Session, user_id: int, language: str) -> list[dict]:
    """Apply ``find_duplicates``: move each duplicate's lesson links to the topic
    that stays (without linking one lesson twice), move its subtopics there, then
    delete it. Flushes, does not commit: the caller commits or rolls back."""
    plan = find_duplicates(db, user_id, language)
    touched = set()
    for d in plan:
        into = d["into_id"]
        for item in db.query(TopicItem).filter(TopicItem.topic_id == d["id"]).all():
            exists = into is not None and db.query(TopicItem.id).filter(
                TopicItem.topic_id == into, TopicItem.item_type == item.item_type,
                TopicItem.item_id == item.item_id).first()
            if into is None or exists:
                db.delete(item)
            else:
                item.topic_id = into
        for child in db.query(Topic).filter(Topic.parent_id == d["id"]).all():
            child.parent_id = into
        db.flush()
        db.delete(db.get(Topic, d["id"]))
        db.flush()
        if into is not None:
            touched.add(into)
    for topic_id in touched:
        topic = db.get(Topic, topic_id)
        if topic is not None:
            topic.total_items = db.query(TopicItem).filter(TopicItem.topic_id == topic_id).count()
    db.flush()
    return plan
