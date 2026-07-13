import json
import logging
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)
router = APIRouter()

_UI_EN = {
    "nav.home": "Home", "nav.lesson": "Lesson", "nav.test": "Test",
    "nav.flashcards": "Flashcards", "nav.speak": "Speak", "nav.quickmode": "15 min",
    "nav.news": "News", "nav.pronounce": "Pronounce", "nav.stats": "Stats",
    "nav.getStarted": "Get Started",
    "achievement.unlocked": "Achievement Unlocked!",
    "lesson.loading": "Generating today's lesson...", "lesson.errorTitle": "Could not load lesson",
    "lesson.takePlacement": "Take Placement Test", "lesson.day": "Day",
    "lesson.completed": "Completed", "lesson.grammar": "Grammar Explanation",
    "lesson.vocabulary": "Vocabulary", "lesson.words": "words", "lesson.word": "Word",
    "lesson.translation": "Translation", "lesson.example": "Example",
    "lesson.dialogue": "Dialogue Practice", "lesson.exercises": "Exercises",
    "lesson.productionTask": "Production Task", "lesson.errorReview": "Error Review",
    "lesson.readingPractice": "Reading Practice (i+1)", "lesson.mixedReview": "Mixed Review",
    "lesson.questions": "questions", "lesson.outputForcing": "Output Forcing (Recall Practice)",
    "lesson.markComplete": "Mark Lesson Complete (+25 XP)", "lesson.marking": "Marking complete...",
    "lesson.lessonCompleted": "Lesson Completed!", "lesson.earnedXP": "You earned 25 XP. Ready for the daily test?",
    "lesson.takeDailyTest": "Take Daily Test", "lesson.pdf": "PDF", "lesson.generating": "Generating...",
    "lesson.newWords": "New words (highlighted):", "lesson.comprehensionCheck": "Comprehension check:",
    "lesson.reviewPrevious": "Review from previous lessons:", "lesson.topic": "Topic:",
    "lesson.practiceLabel": "Practice:", "lesson.showAnswer": "Show answer",
    "lesson.hideAnswer": "Hide answer", "lesson.hideTest": "Hide & Test Yourself",
    "lesson.recallText": "Reproduce the text from memory:", "lesson.writeRemember": "Write what you remember...",
    "lesson.similarity": "Similarity:", "lesson.showOriginal": "Show original",
    "lesson.yourAnswer": "Your answer...", "lesson.showExerciseAnswer": "Show Answer",
    "lesson.hideExerciseAnswer": "Hide Answer", "lesson.answerLabel": "Answer:",
    "lesson.writeResponse": "Write your response here...", "lesson.exampleLabel": "Example:",
    "lesson.exportObsidian": "Export to Obsidian", "lesson.yesterday": "Yesterday",
    "lesson.today": "Today", "lesson.tomorrow": "Tomorrow", "lesson.dayAfterTomorrow": "Day after tomorrow",
    "lesson.downloadLocal": "Download locally", "lesson.sendToDrive": "Send to Google Drive",
    "stats.title": "Statistics", "stats.loading": "Loading statistics...", "stats.level": "Level",
    "stats.streak": "Streak", "stats.days": "days", "stats.totalXP": "Total XP",
    "stats.lessons": "Lessons", "stats.avgScore": "Avg Score", "stats.testHistory": "Test Score History",
    "stats.best": "Best:", "stats.average": "Average:", "stats.testsTaken": "Tests taken:",
    "stats.recentLessons": "Recent Lessons", "stats.completionRate": "Completion rate",
    "stats.errorAnalysis": "Error Analysis", "stats.errorAreas": "Areas that need more practice:",
    "stats.errors": "errors", "stats.flashcardsTitle": "Flashcards", "stats.totalCards": "Total Cards",
    "stats.dueToday": "Due Today", "stats.achievements": "Achievements", "stats.unlocked": "unlocked",
    "stats.memberSince": "Member since", "stats.downloadCSV": "Download CSV", "stats.settings": "Settings",
    "stats.uiLanguage": "UI Language", "stats.polishMode": "Polski", "stats.hardcoreMode": "Hardcore",
    "stats.tips": "Daily Tips", "stats.loadingTips": "Loading tips...", "stats.noTips": "No tips available",
    "flash.title": "Flashcards", "flash.loading": "Loading flashcards...", "flash.total": "total",
    "flash.dueToday": "due today", "flash.exportAnki": "Export Anki", "flash.exporting": "Exporting...",
    "flash.dueTab": "Due Today", "flash.allTab": "All Cards", "flash.addTab": "Add Card",
    "flash.addNew": "Add New Flashcard", "flash.wordPhrase": "Word / Phrase",
    "flash.translationLabel": "Translation", "flash.exampleOptional": "Example sentence (optional)",
    "flash.wordPlaceholder": "Word in target language", "flash.translationPlaceholder": "Translation in your language",
    "flash.examplePlaceholder": "Example sentence", "flash.addButton": "Add Card",
    "flash.allCaughtUp": "All caught up!", "flash.noDueCards": "No cards due for review today. Check back tomorrow!",
    "flash.noCards": "No flashcards yet", "flash.completeLesson": "Complete lessons to automatically add vocabulary cards.",
    "flash.reviewed": "reviewed", "flash.clickReveal": "Click to reveal translation",
    "flash.wordSide": "word", "flash.translationSide": "translation",
    "flash.again": "Again", "flash.hard": "Hard", "flash.good": "Good", "flash.easy": "Easy",
    "flash.previous": "Previous", "flash.next": "Next", "flash.reveal": "Reveal", "flash.showFront": "Show Front",
    "quick.title": "15-Minute Mode", "quick.loading": "Loading quick mode...",
    "quick.activities": "activities", "quick.estimated": "min estimated",
    "quick.start": "Start", "quick.pause": "Pause",
    "quick.timeUp": "Time's up! Great session!", "quick.allDone": "All done! Amazing session!",
    "quick.completed15min": "You've completed your 15-minute daily practice.", "quick.go": "Go â†’",
    "news.title": "News in Target Language", "news.subtitle": "Simplified articles at your CEFR level",
    "news.loading": "Loading news articles...", "news.noArticles": "No articles available. Please try again later.",
    "news.simplified": "Simplified Article", "news.vocabulary": "Key Vocabulary",
    "news.comprehension": "Comprehension Questions", "news.readOriginal": "Read original article",
    "news.showAnswer": "Show answer", "news.hideAnswer": "Hide answer",
    "news.addedToFlash": "Added to flashcards", "news.addToFlash": "Add to flashcards",
    "pronun.title": "Pronunciation Trainer", "pronun.subtitle": "Record yourself and get instant feedback",
    "pronun.loading": "Loading pronunciation trainer...", "pronun.fromLessons": "From Lessons",
    "pronun.customPhrase": "Custom Phrase", "pronun.enterPhrase": "Enter a phrase to practice...",
    "pronun.completeLessons": "Complete some lessons to get practice phrases, or use Custom Phrase.",
    "pronun.recording": "Recording... Click to stop", "pronun.clickMic": "Click the microphone to start recording",
    "pronun.analyzing": "Analyzing pronunciation...", "pronun.results": "Results",
    "pronun.youSaid": "You said:", "pronun.target": "Target:", "pronun.wordAnalysis": "Word analysis:",
    "pronun.charSimilarity": "Char similarity:", "pronun.wordAccuracy": "Word accuracy:",
    "pronun.noDetected": "(nothing detected)", "pronun.micError": "Could not access microphone. Please allow microphone access.",
    "pronun.enterPhraseError": "Please enter a phrase to practice.", "pronun.analysisFailed": "Analysis failed:",
    "place.title": "Placement Test", "place.subtitle": "Assess your language level",
    "place.yourName": "Your Name", "place.namePlaceholder": "Enter your name",
    "place.targetLanguage": "Target Language", "place.nativeLanguage": "Native Language",
    "place.startTest": "Start Test", "place.loading": "Creating account and generating test...",
    "place.question": "Question", "place.of": "of", "place.answered": "answered",
    "place.previous": "Previous", "place.next": "Next", "place.submit": "Submit Test",
    "place.analyzing": "Analyzing results...", "place.results": "Your Results",
    "place.yourLevel": "Your Level:", "place.strongAreas": "Strong Areas:",
    "place.weakAreas": "Needs Work:", "place.recommendations": "Recommendations:",
    "place.studyPlan": "Your 30-Day Study Plan", "place.startLearning": "Start Learning",
    "place.enterName": "Please enter your name",
    "place.tellUs": "Tell us about yourself",
    "nav.videos": "Videos",
    "quick.duration": "Duration:", "quick.subtitle": "Quick daily practice",
    "pronun.nextPhrase": "Next phrase", "pronun.summary": "Summary",
    "pronun.sessionSummary": "Session summary", "pronun.phrasesPracticed": "Phrases practiced",
    "pronun.avgScore": "Average score", "pronun.bestScore": "Best score",
    "pronun.problemWords": "Words needing work:", "pronun.resetSession": "Start new session",
    "home.loadingDashboard": "Loading dashboard...", "home.welcomeBack": "Welcome back,",
    "home.learner": "Learner", "home.learning": "Learning", "home.yourLanguage": "your language",
    "home.level": "Level", "home.dayStreak": "Day streak", "home.totalXP": "Total XP",
    "home.lessonsDone": "Lessons", "home.avgScore": "Avg score", "home.forNextLevel": "to next level",
    "home.todayActivities": "Today's activities", "home.todayLesson": "Today's lesson",
    "home.todayLessonDesc": "Learn new vocabulary and grammar",
    "home.dailyTest": "Daily test", "home.dailyTestDesc": "Check what you learned today",
    "home.practiceSpeaking": "Practice speaking", "home.practiceSpeakingDesc": "Conversation with AI tutor",
    "home.flashcardsDue": "Flashcards due", "home.flashcardsReady": "cards to review",
    "home.reviewNow": "Review now", "home.dailyTips": "Daily tips",
    "home.welcomeTitle": "Learn languages with", "home.welcomeTitleHighlight": "AI Power",
    "home.welcomeSubtitle": "Personalized lessons, adaptive tests, flashcards, and AI conversation practice.",
    "home.featureLessons": "Daily lessons", "home.featureTests": "Smart tests",
    "home.featureFlashcards": "Flashcards", "home.featureConversation": "AI conversation",
    "home.startTest": "Start placement test",
    "test.loading": "Loading daily test...", "test.couldNotLoad": "Could not load test",
    "test.goToLesson": "Go to today's lesson", "test.analyzing": "Analyzing answers...",
    "test.title": "Daily test", "test.question": "Question", "test.of": "of",
    "test.answered": "answered", "test.typeAnswer": "Type your answer...",
    "test.previous": "Previous", "test.next": "Next", "test.submit": "Submit",
    "test.alreadyTaken": "Already done!", "test.complete": "Test complete!",
    "test.xpEarned": "XP earned", "test.errorsTitle": "Errors to review",
    "test.yourAnswer": "Your answer:", "test.correct": "Correct:", "test.rule": "Rule:",
    "test.perfectScore": "Perfect score! No errors!", "test.excellentWork": "Excellent work today!",
    "test.alreadyTakenMsg": "You already completed this test today!", "test.pts": "pts",
    "conv.title": "Conversation practice", "conv.startTitle": "Start conversation",
    "conv.startDesc": "Practice speaking with AI tutor.", "conv.chooseTopic": "Choose topic",
    "conv.customTopic": "Or enter custom topic", "conv.customPlaceholder": "e.g. discussing culture",
    "conv.settingUp": "Setting up...", "conv.start": "Start conversation",
    "conv.voiceChatTitle": "Generate Voice Chat prompt", "conv.voiceChatDesc": "Generate a personalized Voice Chat prompt.",
    "conv.voiceChatGenerating": "Generating...", "conv.voiceChatCopied": "Copied!",
    "conv.voiceChatButton": "Generate and copy prompt", "conv.voiceChatSuccess": "Prompt copied to clipboard!",
    "conv.qaTitle": "Ask a question", "conv.qaDesc": "Have a grammar question? Ask the AI tutor!",
    "conv.qaPlaceholder": "e.g. What's the difference between du and Sie?",
    "conv.qaThinking": "Thinking...", "conv.qaAsk": "Ask",
    "conv.you": "You", "conv.ai": "AI", "conv.endAnalyze": "End and analyze",
    "conv.usefulPhrases": "Useful phrases", "conv.typeMessage": "Type a message...",
    "conv.messagesSent": "messages sent", "conv.errorResponse": "Response error. Try again.",
    "conv.analysisTitle": "Conversation analysis", "conv.whatWell": "What you did well",
    "conv.errorsReview": "Errors to review", "conv.recommendations": "Recommendations",
    "conv.newConversation": "Start new conversation",
    "conv.topic.everyday": "Everyday conversation", "conv.topic.restaurant": "At a restaurant",
    "conv.topic.shopping": "Shopping", "conv.topic.directions": "Asking for directions",
    "conv.topic.doctor": "At the doctor", "conv.topic.jobInterview": "Job interview",
    "conv.topic.hobbies": "Hobbies", "conv.topic.trip": "Planning a trip",
    "conv.topic.hotel": "At the hotel", "conv.topic.friends": "Meeting new people",
    "lesson.aiWillEvaluate": "AI will evaluate your answer and point out errors",
    "lesson.addedToFlash": "added to flashcards", "lesson.addFlashError": "Error adding flashcard",
    "lesson.evaluating": "Evaluating...", "lesson.checkAnswer": "Check answer",
    "lesson.pts": "pts", "lesson.corrections": "Corrections:",
    "lesson.betterVersion": "Better version:", "lesson.addToFlash": "Add to flashcards",
    "lesson.nextLesson": "Next lesson", "lesson.nextWord": "Next word",
    "flash.quickAdd": "Quick flashcard", "flash.quickPlaceholder": "Word or phrase...",
    "flash.quickAddBtn": "Add", "flash.quickSuccess": "Flashcard added!",
    "history.title": "Lesson history", "history.day": "Day", "history.score": "Score",
}


@router.get("/api/settings/ui-translations")
async def get_ui_translations(language: str):
    from backend.services.gemini_service import generate_json
    prompt = f"""Translate these UI strings from English to {language}.
Return a JSON object with identical keys and translated values. No extra text.
{json.dumps(_UI_EN, ensure_ascii=False)}"""
    try:
        result = await generate_json(prompt)
        return result
    except Exception as e:
        logger.error(f"Error generating UI translations to {language}: {e}")
        return _UI_EN


@router.get("/api/settings/gdrive/auth")
async def gdrive_auth():
    """Return Google Drive OAuth2 authorization URL."""
    try:
        from backend.services.google_drive_service import get_auth_url, is_authorized
        if is_authorized():
            return {"authorized": True, "message": "Google Drive already authorized"}
        url = get_auth_url()
        return {"authorized": False, "auth_url": url}
    except FileNotFoundError:
        return {
            "authorized": False,
            "auth_url": None,
            "error": "gdrive_credentials.json not found. Download OAuth2 credentials from Google Cloud Console and save as backend/gdrive_credentials.json"
        }
    except Exception:
        logger.exception("Unexpected error in GDrive auth")
        return {"authorized": False, "auth_url": None, "error": "Failed to get authorization URL"}


@router.get("/api/settings/gdrive/callback")
async def gdrive_callback(code: str):
    """Handle Google Drive OAuth2 callback, save token, and redirect to frontend."""
    try:
        from backend.services.google_drive_service import save_token_from_code
        success = save_token_from_code(code)
        if success:
            return RedirectResponse(url="/?gdrive=success", status_code=302)
        return RedirectResponse(url="/?gdrive=error", status_code=302)
    except Exception:
        logger.exception("GDrive callback error")
        return RedirectResponse(url="/?gdrive=error", status_code=302)


@router.get("/api/settings/gdrive/status")
async def gdrive_status():
    """Check if Google Drive is authorized."""
    try:
        from backend.services.google_drive_service import is_authorized
        return {"authorized": is_authorized()}
    except (ImportError, OSError):
        return {"authorized": False}

