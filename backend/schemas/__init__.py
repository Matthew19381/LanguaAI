"""Pydantic schemas for request/response validation."""
from backend.schemas.conversation import (
    AnalyzePastedRequest,
    AnalyzeRequest,
    MessageRequest,
    QuestionRequest,
    StartConversationRequest,
    TranslateRequest,
)
from backend.schemas.flashcard import (
    AddFlashcardAIRequest,
    AddFlashcardRequest,
    ReviewFlashcardRequest,
)
from backend.schemas.lesson import (
    CompleteLessonRequest,
    ConceptFlashcardRequest,
    EvaluateProductionRequest,
    NextLessonRequest,
)
from backend.schemas.placement import (
    CreateUserRequest,
    StartPlacementRequest,
    SubmitPlacementRequest,
    UpdateLanguageRequest,
)
from backend.schemas.pronunciation import (
    AnalyzePronunciationRequest,
)
from backend.schemas.test import (
    SubmitTestRequest,
)
from backend.schemas.voice_chat import (
    VoiceChatMessageRequest,
    VoiceChatPromptResponse,
    VoiceChatTextResponse,
    VoiceChatVoiceResponse,
)

__all__ = [
    "StartConversationRequest",
    "MessageRequest",
    "AnalyzeRequest",
    "QuestionRequest",
    "AnalyzePastedRequest",
    "TranslateRequest",
    "CompleteLessonRequest",
    "EvaluateProductionRequest",
    "NextLessonRequest",
    "ConceptFlashcardRequest",
    "SubmitTestRequest",
    "AddFlashcardRequest",
    "ReviewFlashcardRequest",
    "AddFlashcardAIRequest",
    "AnalyzePronunciationRequest",
    "StartPlacementRequest",
    "SubmitPlacementRequest",
    "CreateUserRequest",
    "UpdateLanguageRequest",
    "VoiceChatMessageRequest",
    "VoiceChatPromptResponse",
    "VoiceChatTextResponse",
    "VoiceChatVoiceResponse",
]
