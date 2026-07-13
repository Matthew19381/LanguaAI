import logging
import os

from fpdf import FPDF

logger = logging.getLogger(__name__)

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")


def generate_lesson_pdf(lesson: dict, output_path: str) -> str:
    """Generate a PDF file for a lesson and save to output_path. Returns the path."""
    content = lesson.get("content", lesson)  # support both wrapped and raw content

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 18)
    title = lesson.get("title", content.get("title", "Daily Lesson"))
    pdf.cell(0, 12, _safe(title), new_x="LMARGIN", new_y="NEXT", align="C")

    topic = lesson.get("topic", content.get("topic", ""))
    if topic:
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, _safe(f"Topic: {topic}"), new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_text_color(0, 0, 0)

    pdf.ln(4)

    # Grammar Explanation
    explanation = content.get("explanation", "")
    if explanation:
        _section_header(pdf, "Grammar Explanation")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, _safe(explanation))
        pdf.ln(4)

    # Comprehensible Input (i+1)
    ci = content.get("comprehensible_input", {})
    if ci:
        _section_header(pdf, "Reading Practice (Comprehensible Input)")
        pdf.set_font("Helvetica", "", 11)
        ci_text = ci.get("text", "")
        if ci_text:
            pdf.multi_cell(0, 6, _safe(ci_text))
        new_words = ci.get("new_words", [])
        if new_words:
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "New words:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 10)
            for w in new_words:
                pdf.cell(0, 5, _safe(f"  - {w}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Vocabulary
    vocabulary = content.get("vocabulary", [])
    if vocabulary:
        _section_header(pdf, f"Vocabulary ({len(vocabulary)} words)")
        pdf.set_font("Helvetica", "B", 10)
        # Table header
        col_w = [50, 50, 90]
        pdf.cell(col_w[0], 7, "Word", border=1)
        pdf.cell(col_w[1], 7, "Translation", border=1)
        pdf.cell(col_w[2], 7, "Example", border=1)
        pdf.ln()
        pdf.set_font("Helvetica", "", 10)
        for item in vocabulary:
            word = _safe(item.get("word", ""))
            translation = _safe(item.get("translation", ""))
            example = _safe(item.get("example", ""))
            pdf.cell(col_w[0], 6, word, border=1)
            pdf.cell(col_w[1], 6, translation, border=1)
            pdf.cell(col_w[2], 6, example, border=1)
            pdf.ln()
        pdf.ln(4)

    # Dialogue
    dialogue = content.get("dialogue", {})
    if dialogue:
        _section_header(pdf, "Dialogue")
        context = dialogue.get("context", "")
        if context:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 5, _safe(context))
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
        pdf.set_font("Helvetica", "", 11)
        for line in dialogue.get("lines", []):
            speaker = line.get("speaker", "")
            text = _safe(line.get("text", ""))
            translation = _safe(line.get("translation", ""))
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(8, 6, f"{speaker}:", new_x="END")
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, f" {text}")
            if translation:
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(8, 5, "")
                pdf.multi_cell(0, 5, f" {translation}")
                pdf.set_text_color(0, 0, 0)
        pdf.ln(4)

    # Exercises
    exercises = content.get("exercises", [])
    if exercises:
        _section_header(pdf, f"Exercises ({len(exercises)})")
        pdf.set_font("Helvetica", "", 11)
        for i, ex in enumerate(exercises, 1):
            ex_type = ex.get("type", "").replace("_", " ").title()
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 6, f"{i}. [{ex_type}] {_safe(ex.get('instruction', ''))}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 11)
            pdf.multi_cell(0, 6, _safe(ex.get("content", "")))
            options = ex.get("options", [])
            if options:
                for opt in options:
                    pdf.cell(0, 5, _safe(f"   {opt}"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(0, 128, 0)
            pdf.cell(0, 5, f"Answer: {_safe(ex.get('answer', ''))}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
        pdf.ln(2)

    # Production Task
    production = content.get("production_task", {})
    if production:
        _section_header(pdf, "Production Task")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, _safe(production.get("instruction", "")))
        example = production.get("example", "")
        if example:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(100, 100, 100)
            pdf.multi_cell(0, 5, f"Example: {_safe(example)}")
            pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        pdf.set_draw_color(150, 150, 150)
        for _ in range(4):
            pdf.cell(0, 10, "", border="B", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # Footer
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, "Generated by Language Tutor AI", align="C")

    os.makedirs(EXPORTS_DIR, exist_ok=True)
    pdf.output(output_path)
    return output_path


def _section_header(pdf: FPDF, title: str):
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_fill_color(230, 230, 250)
    pdf.cell(0, 8, title, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.ln(2)


def _safe(text: str) -> str:
    """Remove characters that FPDF Latin-1 can't encode."""
    if not isinstance(text, str):
        text = str(text)
    return text.encode("latin-1", errors="replace").decode("latin-1")
