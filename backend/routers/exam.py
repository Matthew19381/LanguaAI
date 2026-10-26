"""Mock Goethe-Zertifikat B1 "Sprechen" (A5): three parts, then a score.

Flow: start → Teil 1 dialogue with the exam partner → Teil 2 presentation
(transcript) → Teil 3 answer + feedback → score. Rules and points live in
services/mock_exam.py.
"""
import json
import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.mock_exam import MockExam
from backend.schemas.exam import ExamUser, Teil1Message, Teil2Submit, Teil3Submit
from backend.services import mock_exam as svc
from backend.utils import get_user_or_404

logger = logging.getLogger(__name__)
router = APIRouter()


def _exam_or_404(db: Session, exam_id: int, user_id: int) -> MockExam:
    exam = db.query(MockExam).filter(MockExam.id == exam_id, MockExam.user_id == user_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


def _require(exam: MockExam, status: str) -> None:
    if exam.status != status:
        raise HTTPException(status_code=409, detail=f"Exam is in {exam.status}, not {status}")


def _as_dict(exam: MockExam) -> dict:
    return {
        "teil1_history": json.loads(exam.teil1_history or "[]"),
        "teil2_topic": exam.teil2_topic,
        "teil2_transcript": exam.teil2_transcript,
        "teil3": json.loads(exam.teil3) if exam.teil3 else None,
        "tasks": json.loads(exam.tasks),
    }


def _view(exam: MockExam) -> dict:
    """The exam as the page needs it (tasks, what was said, score once scored)."""
    data = _as_dict(exam)
    return {
        "exam_id": exam.id,
        "status": exam.status,
        "created_at": exam.created_at.isoformat() if exam.created_at else None,
        "prep_minutes": svc.PREP_MINUTES,
        "teil1_max_turns": svc.TEIL1_MAX_TURNS,
        "slides": svc.SLIDES,
        **data,
        "score": json.loads(exam.scores) if exam.scores else None,
    }


@router.post("/api/exam/start/{user_id}")
async def start_exam(user_id: int, db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    if (user.target_language or "").lower() not in ("german", "deutsch", "niemiecki"):
        raise HTTPException(status_code=400, detail="The mock exam follows Goethe-Zertifikat B1, German only")
    recent = db.query(MockExam).filter(MockExam.user_id == user_id).order_by(MockExam.id.desc()).limit(5).all()
    titles = []
    for e in recent:
        t = json.loads(e.tasks)
        titles += [x["title"] for x in t["teil2"]["topics"]] + [t["teil3"]["partner_presentation"]["title"]]
    tasks = await svc.generate_tasks(titles)
    exam = MockExam(
        user_id=user_id, status="teil1", tasks=json.dumps(tasks, ensure_ascii=False),
        teil1_history=json.dumps([{"role": "assistant", "content": tasks["teil1"]["partner_opening"]}],
                                 ensure_ascii=False),
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return _view(exam)


@router.get("/api/exam/history/{user_id}")
def exam_history(user_id: int, db: Session = Depends(get_db)):
    get_user_or_404(db, user_id)
    scored = (db.query(MockExam).filter(MockExam.user_id == user_id, MockExam.status == "scored")
              .order_by(MockExam.scored_at.desc(), MockExam.id.desc()).all())
    unfinished = (db.query(MockExam).filter(MockExam.user_id == user_id, MockExam.status != "scored")
                  .order_by(MockExam.id.desc()).first())
    return {
        "exams": [{"exam_id": e.id, "scored_at": e.scored_at.isoformat() if e.scored_at else None,
                   "points": e.points, "max_points": e.max_points, "percent": e.percent, "passed": e.passed}
                  for e in scored],
        "goal": svc.goal_status([e.percent for e in scored]),
        "unfinished_exam_id": unfinished.id if unfinished else None,
    }


@router.get("/api/exam/{exam_id}")
def get_exam(exam_id: int, user_id: int, db: Session = Depends(get_db)):
    return _view(_exam_or_404(db, exam_id, user_id))


@router.post("/api/exam/{exam_id}/teil1")
async def teil1_message(exam_id: int, body: Teil1Message, db: Session = Depends(get_db)):
    exam = _exam_or_404(db, exam_id, body.user_id)
    _require(exam, "teil1")
    history = json.loads(exam.teil1_history)
    if sum(1 for m in history if m["role"] == "user") >= svc.TEIL1_MAX_TURNS:
        raise HTTPException(status_code=409, detail="Teil 1 turn limit reached, go on to Teil 2")
    history.append({"role": "user", "content": body.message.strip()})
    tasks = json.loads(exam.tasks)
    try:
        reply = await svc.partner_reply(tasks["teil1"], history)
    except httpx.RequestError as e:
        logger.error(f"AI service error in mock exam Teil 1: {e}")
        raise HTTPException(status_code=503, detail="AI service unavailable")
    history.append({"role": "assistant", "content": reply})
    exam.teil1_history = json.dumps(history, ensure_ascii=False)
    db.commit()
    return {"reply": reply, "turns_left": svc.TEIL1_MAX_TURNS - sum(1 for m in history if m["role"] == "user")}


@router.post("/api/exam/{exam_id}/teil1/finish")
def teil1_finish(exam_id: int, body: ExamUser, db: Session = Depends(get_db)):
    exam = _exam_or_404(db, exam_id, body.user_id)
    _require(exam, "teil1")
    exam.status = "teil2"
    db.commit()
    return _view(exam)


@router.post("/api/exam/{exam_id}/teil2")
async def teil2_submit(exam_id: int, body: Teil2Submit, db: Session = Depends(get_db)):
    exam = _exam_or_404(db, exam_id, body.user_id)
    _require(exam, "teil2")
    tasks = json.loads(exam.tasks)
    transcript = body.transcript.strip()
    title = tasks["teil2"]["topics"][body.topic_index]["title"]
    question = await svc.teil3_question(title, transcript) if transcript else \
        f"Was ist für dich beim Thema „{title}“ am wichtigsten?"
    exam.teil2_topic = body.topic_index
    exam.teil2_transcript = transcript
    exam.teil3 = json.dumps({"question": question, "answer": None, "feedback": None}, ensure_ascii=False)
    exam.status = "teil3"
    db.commit()
    return _view(exam)


@router.post("/api/exam/{exam_id}/teil3")
def teil3_submit(exam_id: int, body: Teil3Submit, db: Session = Depends(get_db)):
    exam = _exam_or_404(db, exam_id, body.user_id)
    _require(exam, "teil3")
    t3 = json.loads(exam.teil3)
    t3.update(answer=body.answer.strip(), feedback=body.feedback.strip())
    exam.teil3 = json.dumps(t3, ensure_ascii=False)
    exam.status = "scoring"
    db.commit()
    return _view(exam)


@router.post("/api/exam/{exam_id}/score")
async def score_exam(exam_id: int, body: ExamUser, db: Session = Depends(get_db)):
    exam = _exam_or_404(db, exam_id, body.user_id)
    if exam.status == "scored":
        return _view(exam)
    _require(exam, "scoring")
    result = await svc.score(_as_dict(exam))
    if result is None:
        # Answers stay saved; scoring can be retried.
        raise HTTPException(status_code=503, detail="Scoring failed, try again")
    exam.scores = json.dumps(result, ensure_ascii=False)
    exam.points = result["points"]
    exam.max_points = result["max_points"]
    exam.percent = result["percent"]
    exam.passed = result["passed"]
    exam.scored_at = datetime.now(timezone.utc)
    exam.status = "scored"
    db.commit()
    return _view(exam)
