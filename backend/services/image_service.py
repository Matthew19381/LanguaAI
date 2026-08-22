"""Image generation service — currently just the on-demand visual mnemonic
for flashcards (Wariant B, 2026-08-19). Mirrors audio_service.py's pattern:
a dedicated directory under the project, served statically by main.py.
"""
import logging
import os

from backend.services.gemini_service import generate_image

logger = logging.getLogger(__name__)

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")


def ensure_images_dir():
    os.makedirs(IMAGES_DIR, exist_ok=True)


async def generate_mnemonic_image(word: str, mnemonic: str, language: str, flashcard_id: int) -> str:
    """Generate and save a visual mnemonic for a flashcard, return its served
    path (e.g. "/images/mnemonic_42.png"). Callers are responsible for caching
    the result (Flashcard.mnemonic_image_path) — this always generates fresh,
    it does not check for an existing file itself.
    """
    ensure_images_dir()
    prompt = (
        f"A simple, vivid, slightly absurd illustration for a language-learning "
        f"memory aid (keyword mnemonic method). The {language} word is \"{word}\". "
        f"The mnemonic image/story to depict: {mnemonic}. "
        f"Style: clean, colorful, a single clear scene, no text or letters in the "
        f"image, memorable and a little exaggerated so it's easy to recall."
    )
    image_bytes = await generate_image(prompt)
    filename = f"mnemonic_{flashcard_id}.png"
    output_path = os.path.join(IMAGES_DIR, filename)
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    logger.info(f"Mnemonic image generated: {output_path}")
    return f"/images/{filename}"
