"""Speech recognition measured on the learner's own voice (A6).

The page /asr-pomiar records 20 sentences; evaluation runs the Whisper sizes
on them next to what the browser heard. Rules: services/asr_benchmark.py.
"""
import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from backend.config import settings
from backend.services import asr_benchmark as bench

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_AUDIO_BYTES = 5 * 1024 * 1024  # a sentence is a few seconds


class EvaluateRequest(BaseModel):
    models: list[str] = bench.DEFAULT_MODELS


def _transcribe(audio: bytes, fmt: str, language: str, size: str) -> str:
    from backend.services.pronunciation_service import transcribe_audio
    return transcribe_audio(audio, audio_format=fmt, language=language, model_size=size)


def _release() -> None:
    from backend.services.pronunciation_service import release_models
    release_models()


@router.get("/api/asr-benchmark/sentences")
def sentences():
    return {"sentences": bench.SENTENCES, "current_whisper": settings.WHISPER_MODEL}


@router.post("/api/asr-benchmark/recording")
async def upload_recording(
    audio: UploadFile = File(...),
    session_id: str = Form(...),
    index: int = Form(...),
    browser_text: Optional[str] = Form(None),
):
    data = await audio.read()
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="Empty or too long recording")
    fmt = (audio.filename or "").rsplit(".", 1)[-1].lower() or "webm"
    try:
        bench.save_recording(session_id, index, data, fmt, browser_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"saved": index, "recordings": len(bench.recordings(session_id))}


@router.post("/api/asr-benchmark/{session_id}/evaluate")
async def evaluate(session_id: str, body: EvaluateRequest):
    try:
        return await run_in_threadpool(bench.evaluate, session_id, body.models, _transcribe, _release)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/asr-benchmark/latest")
def latest():
    return {"result": bench.latest(), "current_whisper": settings.WHISPER_MODEL}
