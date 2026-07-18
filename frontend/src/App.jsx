import { Routes, Route } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import Home from './pages/Home'
import PlacementTest from './pages/PlacementTest'
import DailyLesson from './pages/DailyLesson'
import DailyTest from './pages/DailyTest'
import Flashcards from './pages/Flashcards'
import Conversation from './pages/Conversation'
import Stats from './pages/Stats'
import QuickMode from './pages/QuickMode'
import News from './pages/News'
import PronunciationTrainer from './pages/PronunciationTrainer'
import LessonHistory from './pages/LessonHistory'
import Videos from './pages/Videos'
import ErrorReview from './pages/ErrorReview'
import TopicsPage from './pages/TopicsPage'
import Dictation from './pages/Dictation'
import Practice from './pages/Practice'

function App() {
  return (
    <ErrorBoundary>
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
          <Route path="practice" element={<ErrorBoundary><Practice /></ErrorBoundary>} />
        </Route>
        <Route path="/placement" element={<ErrorBoundary><PlacementTest /></ErrorBoundary>} />
      </Routes>
    </ErrorBoundary>
  )
}

export default App
