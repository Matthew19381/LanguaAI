import hashlib
import logging
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.audio_service import generate_audio, AUDIO_DIR

logger = logging.getLogger(__name__)
router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    language: str = "German"


@router.post("/api/audio/tts")
async def text_to_speech(request: TTSRequest):
    """Generate TTS audio on demand. Caches by text hash."""
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    text_hash = hashlib.md5(f"{request.language}:{request.text}".encode()).hexdigest()[:16]
    filename = f"tts_{text_hash}.mp3"
    output_path = os.path.join(AUDIO_DIR, filename)

    if not os.path.exists(output_path):
        try:
            await generate_audio(request.text.strip(), request.language, output_path)
        except httpx.RequestError as e:
            logger.error(f"TTS service error: {e}")
            raise HTTPException(status_code=503, detail="TTS service unavailable")
        except Exception:
            logger.exception("Unexpected error generating TTS")
            raise HTTPException(status_code=500, detail="Audio generation failed")

    return {"url": f"/audio/{filename}"}
