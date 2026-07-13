import logging
import os

import genanki

logger = logging.getLogger(__name__)

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")


def ensure_exports_dir():
    """Ensure the exports directory exists."""
    os.makedirs(EXPORTS_DIR, exist_ok=True)


def generate_anki_deck(flashcards: list, language: str, user_name: str = "Student") -> str:
    """
    Generate an Anki deck (.apkg file) from a list of flashcard objects.

    flashcards: list of Flashcard model instances or dicts with
                word, translation, example_sentence fields
    language: target language name
    user_name: student's name for the deck title

    Returns: path to the generated .apkg file
    """
    ensure_exports_dir()

    # Generate stable model and deck IDs based on language
    model_id = abs(hash(f"LinguaAI_{language}")) % (10 ** 10)
    deck_id = abs(hash(f"LinguaAI_{language}_{user_name}")) % (10 ** 10)

    # Define the Anki note model
    model = genanki.Model(
        model_id,
        f"{language} - LinguaAI",
        fields=[
            {"name": "Word"},
            {"name": "Translation"},
            {"name": "Example"},
            {"name": "Language"},
        ],
        templates=[
            {
                "name": "Word to Translation",
                "qfmt": """
                    <div class="card">
                        <div class="language-tag">{{Language}}</div>
                        <div class="word">{{Word}}</div>
                    </div>
                """,
                "afmt": """
                    <div class="card">
                        <div class="language-tag">{{Language}}</div>
                        <div class="word">{{Word}}</div>
                        <hr>
                        <div class="translation">{{Translation}}</div>
                        {{#Example}}
                        <div class="example">
                            <em>{{Example}}</em>
                        </div>
                        {{/Example}}
                    </div>
                """,
            },
            {
                "name": "Translation to Word",
                "qfmt": """
                    <div class="card reverse">
                        <div class="language-tag">{{Language}}</div>
                        <div class="word">{{Translation}}</div>
                    </div>
                """,
                "afmt": """
                    <div class="card reverse">
                        <div class="language-tag">{{Language}}</div>
                        <div class="word">{{Translation}}</div>
                        <hr>
                        <div class="translation">{{Word}}</div>
                        {{#Example}}
                        <div class="example">
                            <em>{{Example}}</em>
                        </div>
                        {{/Example}}
                    </div>
                """,
            },
        ],
        css="""
            .card {
                font-family: 'Arial', sans-serif;
                font-size: 20px;
                text-align: center;
                color: #2c3e50;
                background-color: #ecf0f1;
                padding: 40px 20px;
                border-radius: 10px;
                max-width: 500px;
                margin: 0 auto;
            }
            .card.reverse {
                background-color: #dfe6e9;
            }
            .language-tag {
                font-size: 12px;
                color: #7f8c8d;
                text-transform: uppercase;
                letter-spacing: 2px;
                margin-bottom: 20px;
            }
            .word {
                font-size: 32px;
                font-weight: bold;
                color: #2980b9;
                margin: 10px 0;
            }
            .translation {
                font-size: 24px;
                color: #27ae60;
                margin: 10px 0;
            }
            .example {
                font-size: 16px;
                color: #7f8c8d;
                margin-top: 15px;
                padding: 10px;
                background: rgba(0,0,0,0.05);
                border-radius: 5px;
            }
            hr {
                border: none;
                border-top: 2px solid #bdc3c7;
                margin: 20px 0;
            }
        """
    )

    # Create the deck
    deck = genanki.Deck(
        deck_id,
        f"LinguaAI: {language} ({user_name})"
    )

    # Add notes (cards) to the deck
    for flashcard in flashcards:
        # Support both ORM model instances and dicts
        if hasattr(flashcard, "word"):
            word = flashcard.word
            translation = flashcard.translation
            example = flashcard.example_sentence or ""
        else:
            word = flashcard.get("word", "")
            translation = flashcard.get("translation", "")
            example = flashcard.get("example_sentence", "") or ""

        if not word or not translation:
            continue

        note = genanki.Note(
            model=model,
            fields=[word, translation, example, language]
        )
        deck.add_note(note)

    # Generate output filename
    safe_language = language.replace(" ", "_").lower()
    safe_name = user_name.replace(" ", "_").lower()
    filename = f"LinguaAI_{safe_language}_{safe_name}.apkg"
    output_path = os.path.join(EXPORTS_DIR, filename)

    # Create the package and write to file
    package = genanki.Package(deck)
    package.write_to_file(output_path)

    logger.info(f"Anki deck generated: {output_path} ({len(flashcards)} cards)")
    return output_path


def get_deck_stats(flashcards: list) -> dict:
    """Get statistics about a deck before generation."""
    total = len(flashcards)
    with_examples = sum(
        1 for f in flashcards
        if (f.example_sentence if hasattr(f, "example_sentence") else f.get("example_sentence"))
    )

    return {
        "total_cards": total,
        "cards_with_examples": with_examples,
        "cards_without_examples": total - with_examples
    }
