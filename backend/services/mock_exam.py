"""Mock Goethe-Zertifikat B1 "Sprechen" (A5 of the "finished" criterion).

Structure and points follow Goethe-Institut's B1 Modellsatz / Übungssatz
(checked 26.10.2026):
- Teil 1 "Gemeinsam etwas planen" (~3 min): Erfüllung 8, Interaktion 4,
  Wortschatz/Register 8, Strukturen 8.
- Teil 2 "Ein Thema präsentieren" (~3 min, 5 slides): Erfüllung 12,
  Kohärenz 4, Wortschatz 12, Strukturen 12. Erfüllung counts the slides
  covered adequately: A all 5, B 3-4, C 2 (or all too brief), D 1.
- Teil 3 "Über ein Thema sprechen" (~2 min): Erfüllung 16 (feedback on the
  partner's presentation, a question about it, answering a question).
- Aussprache 16 over the whole exam. Total 100, pass mark 60.
Each criterion has levels A-E with points 100/75/50/25/0 % of its maximum;
E in Erfüllung makes the whole part 0.

Aussprache cannot be judged from a transcript, so it is not scored here: the
result is the share of the 84 assessed points, and 60 % of those is the pass
line. Two examiners score the real exam and their points are averaged; here
two independent model scorings are averaged the same way.
"""
import asyncio
import logging

from backend.services.gemini_service import generate_json, generate_text, with_model

logger = logging.getLogger(__name__)

RUBRIC: dict[str, list[tuple[str, int]]] = {
    "teil1": [("erfuellung", 8), ("interaktion", 4), ("wortschatz", 8), ("strukturen", 8)],
    "teil2": [("erfuellung", 12), ("kohaerenz", 4), ("wortschatz", 12), ("strukturen", 12)],
    "teil3": [("erfuellung", 16)],
}
NOT_ASSESSED = {"aussprache": 16}
LEVEL_FRACTION = {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25, "E": 0.0}
MAX_POINTS = sum(m for crit in RUBRIC.values() for _, m in crit)  # 84
PASS_PERCENT = 60.0
PREP_MINUTES = 15
TEIL1_MAX_TURNS = 12   # student turns; the real part lasts about 3 minutes

# Teil 2 slides are fixed by the exam; only the topic changes.
SLIDES = [
    "Stellen Sie Ihr Thema vor. Erklären Sie den Inhalt und die Struktur Ihrer Präsentation.",
    "Berichten Sie von Ihrer Situation oder einem Erlebnis im Zusammenhang mit dem Thema.",
    "Berichten Sie von der Situation in Ihrem Heimatland und geben Sie Beispiele.",
    "Nennen Sie die Vor- und Nachteile und sagen Sie dazu Ihre Meinung. Geben Sie auch Beispiele.",
    "Beenden Sie Ihre Präsentation und bedanken Sie sich bei den Zuhörern.",
]

FALLBACK_TASKS = {
    "teil1": {
        "situation": "Eine Kollegin hat nächste Woche Geburtstag. Sie möchten zusammen eine kleine Feier im Büro organisieren.",
        "points": ["Wann feiern?", "Was essen und trinken?", "Wer bringt was mit?", "Welches Geschenk?"],
        "partner_opening": "Hallo! Nächste Woche hat Anna Geburtstag. Sollen wir zusammen etwas organisieren? Wann hast du Zeit?",
    },
    "teil2": {"topics": [
        {"title": "Sollen Kinder ein eigenes Handy haben?"},
        {"title": "Im Homeoffice arbeiten: eine gute Idee?"},
    ]},
    "teil3": {"partner_presentation": {
        "title": "Sport in der Freizeit",
        "text": ("Mein Thema ist Sport in der Freizeit. Zuerst erzähle ich von mir, dann von meinem Heimatland, "
                 "und am Ende sage ich meine Meinung. Ich gehe zweimal pro Woche schwimmen, weil es gut für den "
                 "Rücken ist. In meinem Heimatland spielen viele Leute Fußball, aber viele Erwachsene haben keine "
                 "Zeit für Sport. Ein Vorteil ist, dass man gesund bleibt und Freunde trifft. Ein Nachteil ist, "
                 "dass manche Sportarten teuer sind. Ich finde, jeder sollte etwas Sport machen, auch nur "
                 "spazieren gehen. Vielen Dank für Ihre Aufmerksamkeit."),
    }},
}


def _valid_tasks(data: dict) -> bool:
    try:
        t1, t2, t3 = data["teil1"], data["teil2"], data["teil3"]
        return (bool(t1["situation"]) and len(t1["points"]) == 4 and bool(t1["partner_opening"])
                and len(t2["topics"]) == 2 and all(t["title"] for t in t2["topics"])
                and bool(t3["partner_presentation"]["title"]) and bool(t3["partner_presentation"]["text"]))
    except (KeyError, TypeError):
        return False


@with_model("test")
async def generate_tasks(recent_titles: list[str] | None = None) -> dict:
    """New exam tasks in the format of Goethe B1 Sprechen; fixed set on any failure."""
    avoid = ("\nDo not reuse these topics from earlier attempts: " + "; ".join(recent_titles)) if recent_titles else ""
    prompt = f"""You write a mock Goethe-Zertifikat B1 "Sprechen" exam for an adult learner of German.
All texts in German, CEFR B1, everyday adult topics (work, free time, health, media, living, travel).{avoid}

Teil 1 "Gemeinsam etwas planen": a realistic situation where two people plan something together,
and exactly 4 short guiding questions (like "Wann?", "Wo treffen?"). Also the first line of the
partner, who opens the conversation.
Teil 2 "Ein Thema präsentieren": two different discussion topics, each a short question or statement
that has pros and cons (e.g. "Sollen Kinder ein eigenes Handy haben?"). The 5 slides are fixed, do not write them.
Teil 3: the PARTNER's own presentation on a third topic, about 120 words, B1, following the same
5 slides (topic and structure, own experience, situation in the home country, pros/cons and opinion, thanks).

Return JSON:
{{"teil1": {{"situation": "...", "points": ["...", "...", "...", "..."], "partner_opening": "..."}},
 "teil2": {{"topics": [{{"title": "..."}}, {{"title": "..."}}]}},
 "teil3": {{"partner_presentation": {{"title": "...", "text": "..."}}}}}}"""
    try:
        data = await generate_json(prompt)
    except Exception as e:
        logger.error(f"Mock exam task generation failed, using fixed set: {e}")
        return FALLBACK_TASKS
    if not _valid_tasks(data):
        logger.error("Mock exam tasks had the wrong shape, using fixed set")
        return FALLBACK_TASKS
    return data


def _dialogue(history: list[dict]) -> str:
    return "\n".join(f"{'Partner' if m['role'] == 'assistant' else 'Kandidat'}: {m['content']}" for m in history)


@with_model("conversation")
async def partner_reply(teil1: dict, history: list[dict]) -> str:
    """The exam partner in Teil 1: plans along, never corrects, leaves room to speak."""
    prompt = f"""You are the other candidate in the oral part of the Goethe-Zertifikat B1 exam (Teil 1,
"Gemeinsam etwas planen"). Situation: {teil1['situation']}
Guiding points: {'; '.join(teil1['points'])}

Dialogue so far:
{_dialogue(history)}

Reply as the partner, in German at B1 level, at most 2 short sentences:
- react to what the candidate just said (agree, disagree with a reason, or make a counter-proposal),
- then move the planning on, e.g. with a question about a guiding point not yet discussed,
- once all 4 points are decided, sum up the plan briefly.
Never correct the candidate's German and never explain anything: this is an exam.
Reply ONLY with what the partner says."""
    text = (await generate_text(prompt)).strip()
    return text or "Gut. Und was machen wir mit dem nächsten Punkt?"


@with_model("conversation")
async def teil3_question(topic_title: str, transcript: str) -> str:
    """Partner's feedback and one question on the candidate's presentation (Teil 3)."""
    prompt = f"""You are the other candidate in the Goethe-Zertifikat B1 oral exam, Teil 3. The candidate has just
presented the topic "{topic_title}". Their presentation:
\"\"\"{transcript[:3000]}\"\"\"

In German, B1, 2 sentences: a short friendly feedback on the presentation, then ONE question about
something they said or about their opinion. Reply ONLY with what you say."""
    try:
        text = (await generate_text(prompt)).strip()
    except Exception as e:
        logger.error(f"Teil 3 question failed, using fixed one: {e}")
        text = ""
    return text or f"Danke für deine Präsentation zum Thema „{topic_title}“. Was würdest du einem Freund in dieser Situation raten?"


def _word_count(text: str | None) -> int:
    return len((text or "").split())


def part_texts(exam: dict) -> dict[str, str]:
    """What the candidate said in each part (only their own words are scored)."""
    t1 = " ".join(m["content"] for m in exam["teil1_history"] if m["role"] == "user")
    t3 = exam.get("teil3") or {}
    return {"teil1": t1, "teil2": exam.get("teil2_transcript") or "",
            "teil3": " ".join(filter(None, [t3.get("answer"), t3.get("feedback")]))}


def _scoring_prompt(exam: dict) -> str:
    tasks = exam["tasks"]
    topic = tasks["teil2"]["topics"][exam["teil2_topic"]]["title"]
    t3 = exam.get("teil3") or {}
    partner = tasks["teil3"]["partner_presentation"]
    slides = "\n".join(f"  {i}. {s}" for i, s in enumerate(SLIDES, 1))
    return f"""You are a certified Goethe-Institut examiner scoring a Goethe-Zertifikat B1 "Sprechen" exam.
The exam was spoken; you see a speech-recognition transcript, so ignore spelling, punctuation and
capitalisation, and do not judge pronunciation. Score only the CANDIDATE's words, strictly by the
official B1 criteria, levels A (fully meets B1) / B / C / D / E (not assessable or missing).

TEIL 1, Gemeinsam etwas planen. Situation: {tasks['teil1']['situation']}
Guiding points: {'; '.join(tasks['teil1']['points'])}
Dialogue:
{_dialogue(exam['teil1_history'])}
Criteria: erfuellung (task done: proposals, reactions, agreement on the points; amount appropriate),
interaktion (share of the conversation, language functions such as proposing, agreeing, rejecting
with reasons; reacting; starting, keeping going and ending the talk), wortschatz (range and
appropriateness of vocabulary and register), strukturen (morphology and syntax).

TEIL 2, Präsentation, topic: {topic}. Required slides:
{slides}
Transcript:
\"\"\"{exam.get('teil2_transcript') or ''}\"\"\"
Criteria: erfuellung (A all 5 slides covered adequately in content and length, B 3-4 slides,
C 2 slides or all too brief, D 1 slide, E not assessable), kohaerenz (clear line of thought,
linking of sentences and parts of sentences), wortschatz, strukturen.

TEIL 3, Über ein Thema sprechen.
The partner presented "{partner['title']}": {partner['text']}
Candidate's feedback and question on the partner's presentation: \"\"\"{t3.get('feedback') or ''}\"\"\"
Partner's question to the candidate: {t3.get('question') or ''}
Candidate's answer: \"\"\"{t3.get('answer') or ''}\"\"\"
Criterion: erfuellung (gives feedback, asks a relevant question, answers the question adequately).

For every criterion give the level, one reason in Polish, and up to 3 short quotes of the
candidate's errors with the correct form (empty list if none). Return JSON:
{{"teil1": {{"erfuellung": {{"level": "B", "reason": "...", "errors": ["falsch → richtig"]}},
            "interaktion": {{...}}, "wortschatz": {{...}}, "strukturen": {{...}}}},
 "teil2": {{"erfuellung": {{...}}, "kohaerenz": {{...}}, "wortschatz": {{...}}, "strukturen": {{...}}}},
 "teil3": {{"erfuellung": {{...}}}}}}"""


def _levels_from(raw: dict) -> dict | None:
    """Validated {part: {criterion: {level, reason, errors}}}, or None if anything is missing."""
    out: dict = {}
    try:
        for part, crits in RUBRIC.items():
            out[part] = {}
            for name, _ in crits:
                item = raw[part][name]
                level = str(item["level"]).strip().upper()[:1]
                if level not in LEVEL_FRACTION:
                    return None
                errors = item.get("errors") or []
                out[part][name] = {"level": level, "reason": str(item.get("reason") or ""),
                                   "errors": [str(e) for e in errors][:3] if isinstance(errors, list) else []}
    except (KeyError, TypeError, AttributeError):
        return None
    return out


def points_of(levels: dict) -> dict[str, dict[str, float]]:
    """Points per criterion for one scoring; Erfüllung E makes the part 0 (Goethe rule)."""
    pts: dict[str, dict[str, float]] = {}
    for part, crits in RUBRIC.items():
        zero = levels[part]["erfuellung"]["level"] == "E"
        pts[part] = {name: 0.0 if zero else LEVEL_FRACTION[levels[part][name]["level"]] * m for name, m in crits}
    return pts


def _empty_part_levels(part: str) -> dict:
    return {name: {"level": "E", "reason": "Brak wypowiedzi w tej części.", "errors": []} for name, _ in RUBRIC[part]}


@with_model("test")
async def _one_scoring(prompt: str) -> dict | None:
    try:
        return _levels_from(await generate_json(prompt))
    except Exception as e:
        logger.error(f"Mock exam scoring run failed: {e}")
        return None


async def score(exam: dict) -> dict | None:
    """Two independent scorings averaged (like Goethe's two examiners).

    A part where the candidate said nothing is E without asking the model.
    Returns None when neither scoring produced a valid result.
    """
    prompt = _scoring_prompt(exam)
    runs = [r for r in await asyncio.gather(_one_scoring(prompt), _one_scoring(prompt)) if r is not None]
    if not runs:
        return None
    texts = part_texts(exam)
    for run in runs:
        for part in RUBRIC:
            if _word_count(texts[part]) == 0:
                run[part] = _empty_part_levels(part)
    run_points = [points_of(r) for r in runs]
    parts: dict = {}
    total = 0.0
    for part, crits in RUBRIC.items():
        parts[part] = {}
        for name, maximum in crits:
            p = sum(rp[part][name] for rp in run_points) / len(run_points)
            total += p
            parts[part][name] = {
                "points": round(p, 2), "max": maximum,
                "levels": [r[part][name]["level"] for r in runs],
                "reason": runs[0][part][name]["reason"],
                "errors": runs[0][part][name]["errors"],
            }
    percent = round(100 * total / MAX_POINTS, 1)
    return {"parts": parts, "points": round(total, 2), "max_points": MAX_POINTS, "percent": percent,
            "passed": percent >= PASS_PERCENT, "scorings": len(runs),
            "not_assessed": NOT_ASSESSED, "words": {k: _word_count(v) for k, v in texts.items()}}


def goal_status(percents_newest_first: list[float]) -> dict:
    """Goal "Mówienie B1": the last two scored attempts both at or above the pass mark."""
    last_two = percents_newest_first[:2]
    return {"reached": len(last_two) == 2 and all(p >= PASS_PERCENT for p in last_two),
            "pass_percent": PASS_PERCENT, "last_two": last_two}
