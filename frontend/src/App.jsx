import { Suspense, lazy } from 'react'
import { Routes, Route } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import UnlockGate from './components/UnlockGate'
import { PageLoader } from './components/LoadingSpinner'

// Pages are code-split: each becomes its own chunk, loaded on first visit.
// This keeps the initial bundle small — important for first load on a phone.
// The navbar (Layout) stays eager; a Suspense boundary inside Layout shows the
// loader only in the content area during navigation.
const Home = lazy(() => import('./pages/Home'))
const PlacementTest = lazy(() => import('./pages/PlacementTest'))
const DailyLesson = lazy(() => import('./pages/DailyLesson'))
const DailyTest = lazy(() => import('./pages/DailyTest'))
const Flashcards = lazy(() => import('./pages/Flashcards'))
const Conversation = lazy(() => import('./pages/Conversation'))
const Stats = lazy(() => import('./pages/Stats'))
const QuickMode = lazy(() => import('./pages/QuickMode'))
const News = lazy(() => import('./pages/News'))
const PronunciationTrainer = lazy(() => import('./pages/PronunciationTrainer'))
const LessonHistory = lazy(() => import('./pages/LessonHistory'))
const Videos = lazy(() => import('./pages/Videos'))
const ErrorReview = lazy(() => import('./pages/ErrorReview'))
const TopicsPage = lazy(() => import('./pages/TopicsPage'))
const Dictation = lazy(() => import('./pages/Dictation'))
const ReadAloud = lazy(() => import('./pages/ReadAloud'))
const Practice = lazy(() => import('./pages/Practice'))
const Profile = lazy(() => import('./pages/Profile'))
const Settings = lazy(() => import('./pages/Settings'))
const LoginAs = lazy(() => import('./pages/LoginAs'))

function App() {
  return (
    <ErrorBoundary>
      <UnlockGate>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<ErrorBoundary><Home /></ErrorBoundary>} />
          <Route path="lesson" element={<ErrorBoundary><DailyLesson /></ErrorBoundary>} />
          <Route path="lesson/history" element={<ErrorBoundary><LessonHistory /></ErrorBoundary>} />
          <Route path="lesson/:lessonId" element={<ErrorBoundary><DailyLesson /></ErrorBoundary>} />
          <Route path="test" element={<ErrorBoundary><DailyTest /></ErrorBoundary>} />
          <Route path="flashcards" element={<ErrorBoundary><Flashcards /></ErrorBoundary>} />
          <Route path="conversation" element={<ErrorBoundary><Conversation /></ErrorBoundary>} />
          <Route path="stats" element={<ErrorBoundary><Stats /></ErrorBoundary>} />
          <Route path="quickmode" element={<ErrorBoundary><QuickMode /></ErrorBoundary>} />
          <Route path="news" element={<ErrorBoundary><News /></ErrorBoundary>} />
          <Route path="pronunciation" element={<ErrorBoundary><PronunciationTrainer /></ErrorBoundary>} />
          <Route path="videos" element={<ErrorBoundary><Videos /></ErrorBoundary>} />
          <Route path="errors" element={<ErrorBoundary><ErrorReview /></ErrorBoundary>} />
          <Route path="topics" element={<ErrorBoundary><TopicsPage /></ErrorBoundary>} />
          <Route path="dictation" element={<ErrorBoundary><Dictation /></ErrorBoundary>} />
          <Route path="read-aloud" element={<ErrorBoundary><ReadAloud /></ErrorBoundary>} />
          <Route path="practice" element={<ErrorBoundary><Practice /></ErrorBoundary>} />
          <Route path="profile" element={<ErrorBoundary><Profile /></ErrorBoundary>} />
          <Route path="settings" element={<ErrorBoundary><Settings /></ErrorBoundary>} />
        </Route>
        {/* Routes outside the Layout need their own Suspense boundary. */}
        <Route path="/placement" element={
          <ErrorBoundary><Suspense fallback={<PageLoader />}><PlacementTest /></Suspense></ErrorBoundary>
        } />
        <Route path="/login-as" element={
          <ErrorBoundary><Suspense fallback={<PageLoader />}><LoginAs /></Suspense></ErrorBoundary>
        } />
      </Routes>
      </UnlockGate>
    </ErrorBoundary>
  )
}

export default App
