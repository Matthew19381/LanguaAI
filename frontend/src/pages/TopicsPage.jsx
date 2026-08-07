import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  BookOpen, Brain, ChevronDown, ChevronRight, Clock,
  Filter, Layers, Loader2, RefreshCw, Search,
  Star, Target, TrendingUp, Zap, CheckCircle, AlertCircle
} from 'lucide-react';
import {
  getUserId, getTopics, getTopicTree, getDueTopics,
  getTopicStats, getTopicDetail, reviewTopic,
  generateFlashcardsFromTopic, generateFlashcardsFromErrors,
  batchAddFlashcards
} from '../api/client';
import { PageLoader } from '../components/LoadingSpinner';

// ── Category labels (Polish) ──────────────────────────────────────────────
const CATEGORY_LABELS = {
  grammar: 'Gramatyka',
  vocabulary: 'Słownictwo',
  pronunciation: 'Wymowa',
  listening: 'Słuchanie',
  reading: 'Czytanie',
  writing: 'Pisanie',
  speaking: 'Mówienie',
  culture: 'Kultura',
  idioms: 'Idiomy',
  other: 'Inne',
};

const CATEGORY_COLORS = {
  grammar: 'bg-blue-100 text-blue-800 border-blue-200',
  vocabulary: 'bg-green-100 text-green-800 border-green-200',
  pronunciation: 'bg-purple-100 text-purple-800 border-purple-200',
  listening: 'bg-orange-100 text-orange-800 border-orange-200',
  reading: 'bg-teal-100 text-teal-800 border-teal-200',
  writing: 'bg-pink-100 text-pink-800 border-pink-200',
  speaking: 'bg-red-100 text-red-800 border-red-200',
  culture: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  idioms: 'bg-indigo-100 text-indigo-800 border-indigo-200',
  other: 'bg-gray-100 text-gray-800 border-gray-200',
};

// ── German gender colors ──────────────────────────────────────────────────
const GENDER_COLORS = {
  der: { bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-300', label: 'm.' },
  die: { bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-300', label: 'f.' },
  das: { bg: 'bg-green-100', text: 'text-green-700', border: 'border-green-300', label: 'n.' },
};

function GenderBadge({ gender }) {
  if (!gender || !GENDER_COLORS[gender]) return null;
  const c = GENDER_COLORS[gender];
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${c.bg} ${c.text} border ${c.border} mr-1`}>
      {gender}
    </span>
  );
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function highlightWordInSentence(sentence, word, gender, isImportant = false) {
  if (!sentence) return sentence;
  const safeSentence = escapeHtml(sentence);
  if (!word) return safeSentence;
  const escaped = escapeHtml(word).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`\\b(${escaped})\\b`, 'gi');

  // Get gender color class
  let genderColorClass = '';
  if (gender && GENDER_COLORS[gender]) {
    genderColorClass = GENDER_COLORS[gender].text.replace('text-', 'bg-').replace('-700', '-200');
  }

  // Build the final class string
  let finalClass = '';
  if (genderColorClass) {
    // Start with gender background
    finalClass = genderColorClass + ' rounded px-0.5';
    // If important, add yellow border
    if (isImportant) {
      finalClass += ' border-2 border-yellow-200';
    }
  } else {
    // No gender - use importance background or default
    if (isImportant) {
      finalClass = 'bg-yellow-200 border-2 border-yellow-200 rounded px-0.5';
    } else {
      // Neither gender nor importance - default to yellow background
      finalClass = 'bg-yellow-200 rounded px-0.5';
    }
  }

  return safeSentence.replace(regex, `<mark class="${finalClass}">$1</mark>`);
}

// ── Memory strength bar ───────────────────────────────────────────────────
function MemoryBar({ strength, size = 'md' }) {
  const pct = Math.round(strength * 100);
  const color =
    pct >= 80 ? 'bg-green-500' :
    pct >= 50 ? 'bg-yellow-500' :
    pct >= 30 ? 'bg-orange-500' : 'bg-red-400';
  const h = size === 'sm' ? 'h-1.5' : size === 'lg' ? 'h-3' : 'h-2';

  return (
    <div className={`w-full ${h} bg-gray-200 rounded-full overflow-hidden`}>
      <div
        className={`${h} ${color} rounded-full transition-all duration-500`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ── Review buttons (FSRS rating 1-4) ────────────────────────────────────
function ReviewButtons({ onReview, reviewing }) {
  const labels = [
    { r: 1, label: 'Znowu', color: 'bg-red-600 hover:bg-red-700', desc: 'Zapomniałem' },
    { r: 2, label: 'Trudne', color: 'bg-orange-500 hover:bg-orange-600', desc: 'Z trudem przypomniałem' },
    { r: 3, label: 'Dobre', color: 'bg-blue-500 hover:bg-blue-600', desc: 'Przypomniałem z wysiłkiem' },
    { r: 4, label: 'Łatwe', color: 'bg-green-500 hover:bg-green-600', desc: 'Natychmiastowe przypomnienie' },
  ];

  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {labels.map(({ r, label, color, desc }) => (
        <button
          key={r}
          onClick={() => onReview(r)}
          disabled={reviewing}
          title={desc}
          className={`${color} text-white text-xs px-2.5 py-1.5 rounded-md transition-colors disabled:opacity-50 font-medium`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// ── Flashcard preview card ─────────────────────────────────────────────────
function FlashcardPreview({ fc, index, onToggle, selected }) {
  const hasGender = fc.gender && GENDER_COLORS[fc.gender];
  return (
    <div
      className={`border rounded-lg p-3 cursor-pointer transition-all ${
        selected ? 'border-indigo-400 bg-indigo-50/50' : 'border-gray-200 hover:border-gray-300'
      }`}
      onClick={() => onToggle(index)}
    >
      <div className="flex items-start gap-2">
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onToggle(index)}
          className="mt-1 accent-indigo-600"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <GenderBadge gender={fc.gender} />
            <span className="font-semibold text-sm">{fc.word}</span>
            <span className="text-gray-400">—</span>
            <span className="text-sm text-gray-600">{fc.translation}</span>
          </div>
          {fc.example && (
            <p
              className="text-xs text-gray-500 mt-1 italic"
              dangerouslySetInnerHTML={{ __html: highlightWordInSentence(fc.example, fc.word, fc.gender, fc.isImportant) }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Topic detail panel ─────────────────────────────────────────────────────
function TopicDetail({ topicId, onClose }) {
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reviewing, setReviewing] = useState(false);

  // "Rozpocznij naukę" — jump from a material straight into it.
  const startItem = (item) => {
    if (item.type === 'lesson') navigate(`/lesson/${item.item_id}`);
    else if (item.type === 'test') navigate('/test');
    else navigate('/practice');
  };

  // Flashcard generation state
  const [fcCount, setFcCount] = useState(10);
  const [fcPreview, setFcPreview] = useState(null);
  const [fcLoading, setFcLoading] = useState(false);
  const [fcError, setFcError] = useState('');
  const [fcSelected, setFcSelected] = useState({});
  const [fcSaving, setFcSaving] = useState(false);
  const [fcSource, setFcSource] = useState('topic'); // 'topic' | 'errors'
  const [showFcPanel, setShowFcPanel] = useState(false);

  const userId = getUserId();

  useEffect(() => {
    getTopicDetail(topicId)
      .then(setDetail)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [topicId]);

  const handleReview = async (quality) => {
    setReviewing(true);
    try {
      const updated = await reviewTopic(topicId, quality);
      setDetail(prev => ({
        ...prev,
        topic: { ...prev.topic, ...updated },
      }));
    } catch (e) {
      alert('Błąd podczas zapisu powtórki: ' + e.message);
    } finally {
      setReviewing(false);
    }
  };

  const handleGenerate = async (source) => {
    setFcSource(source);
    setFcLoading(true);
    setFcError('');
    setFcPreview(null);
    setFcSelected({});
    try {
      const res = source === 'topic'
        ? await generateFlashcardsFromTopic(userId, topicId, fcCount)
        : await generateFlashcardsFromErrors(userId, fcCount);
      setFcPreview(res.flashcards || []);
      // Select all by default
      const sel = {};
      (res.flashcards || []).forEach((_, i) => { sel[i] = true; });
      setFcSelected(sel);
    } catch (e) {
      setFcError(e.message || 'Nie udało się wygenerować fiszek');
    } finally {
      setFcLoading(false);
    }
  };

  const handleToggleFc = (index) => {
    setFcSelected(prev => ({ ...prev, [index]: !prev[index] }));
  };

  const handleSelectAll = () => {
    if (!fcPreview) return;
    const allSelected = fcPreview.every((_, i) => fcSelected[i]);
    const sel = {};
    fcPreview.forEach((_, i) => { sel[i] = !allSelected; });
    setFcSelected(sel);
  };

  const handleSaveSelected = async () => {
    if (!fcPreview) return;
    const selectedFcs = fcPreview.filter((_, i) => fcSelected[i]);
    if (selectedFcs.length === 0) return;
    setFcSaving(true);
    try {
      const res = await batchAddFlashcards(userId, selectedFcs);
      alert(`Dodano ${res.created} fiszek do kolekcji!`);
      setFcPreview(null);
      setShowFcPanel(false);
    } catch (e) {
      alert('Błąd podczas zapisu: ' + e.message);
    } finally {
      setFcSaving(false);
    }
  };

  if (loading) return <div className="p-4 text-center"><Loader2 className="animate-spin mx-auto" /></div>;
  if (!detail) return <div className="p-4 text-center text-gray-500">Nie znaleziono tematu</div>;

  const { topic, items } = detail;

  return (
    <div className="bg-white rounded-xl shadow-lg border p-4 mt-2">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold">{topic.name}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
      </div>

      {topic.description && (
        <p className="text-sm text-gray-600 mb-3">{topic.description}</p>
      )}

      {/* Memory strength */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-gray-500">Siła zapamiętania</span>
          <span className="font-semibold">{Math.round(topic.memory_strength * 100)}%</span>
        </div>
        <MemoryBar strength={topic.memory_strength} size="lg" />
      </div>

      {/* FSRS stats */}
      <div className="grid grid-cols-4 gap-2 mb-3 text-center">
        <div className="bg-gray-50 rounded-lg p-2">
          <div className="text-xs text-gray-500">Powtórki</div>
          <div className="font-bold">{topic.repetitions}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-2">
          <div className="text-xs text-gray-500">Interwał</div>
          <div className="font-bold">{topic.interval}d</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-2">
          <div className="text-xs text-gray-500">Trudność</div>
          <div className="font-bold">{topic.difficulty?.toFixed(1)}</div>
        </div>
        <div className="bg-gray-50 rounded-lg p-2">
          <div className="text-xs text-gray-500">Stabilność</div>
          <div className="font-bold">{topic.stability?.toFixed(0)}d</div>
        </div>
      </div>

      {/* Review buttons */}
      {topic.is_due && (
        <div className="mb-3">
          <div className="text-sm font-medium text-orange-600 mb-1 flex items-center gap-1">
            <AlertCircle size={14} /> Do powtórki!
          </div>
          <ReviewButtons onReview={handleReview} reviewing={reviewing} />
        </div>
      )}

      {!topic.is_due && topic.next_review && (
        <div className="text-sm text-gray-500 mb-3 flex items-center gap-1">
          <Clock size={14} /> Następna powtórka: {new Date(topic.next_review).toLocaleDateString('pl-PL')}
        </div>
      )}

      {/* ── Flashcard generation section ── */}
      <div className="border-t pt-3 mb-3">
        <button
          onClick={() => setShowFcPanel(!showFcPanel)}
          className="flex items-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
        >
          {showFcPanel ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          Wygeneruj fiszki
        </button>

        {showFcPanel && (
          <div className="mt-3 space-y-3">
            {/* Count selector */}
            <div className="flex items-center gap-3">
              <label className="text-sm text-gray-600">Liczba fiszek:</label>
              <select
                value={fcCount}
                onChange={e => setFcCount(Number(e.target.value))}
                className="border rounded-lg px-2 py-1 text-sm"
              >
                {[5, 10, 15, 20, 25, 30].map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
              <button
                onClick={() => handleGenerate('topic')}
                disabled={fcLoading}
                className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                {fcLoading && fcSource === 'topic' ? <Loader2 size={14} className="animate-spin inline" /> : 'Z tematu'}
              </button>
              <button
                onClick={() => handleGenerate('errors')}
                disabled={fcLoading}
                className="px-3 py-1.5 bg-orange-500 text-white text-sm rounded-lg hover:bg-orange-600 disabled:opacity-50 transition-colors"
              >
                {fcLoading && fcSource === 'errors' ? <Loader2 size={14} className="animate-spin inline" /> : 'Z błędów'}
              </button>
            </div>

            {/* Error */}
            {fcError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-2 text-sm text-red-600">
                {fcError}
              </div>
            )}

            {/* Preview */}
            {fcPreview && fcPreview.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">
                    Podgląd ({fcPreview.length} fiszek)
                  </span>
                  <button
                    onClick={handleSelectAll}
                    className="text-xs text-indigo-600 hover:underline"
                  >
                    Zaznacz/odznacz wszystkie
                  </button>
                </div>
                <div className="space-y-1.5 max-h-64 overflow-y-auto">
                  {fcPreview.map((fc, i) => (
                    <FlashcardPreview
                      key={i}
                      fc={fc}
                      index={i}
                      onToggle={handleToggleFc}
                      selected={!!fcSelected[i]}
                    />
                  ))}
                </div>
                <button
                  onClick={handleSaveSelected}
                  disabled={fcSaving || Object.values(fcSelected).every(v => !v)}
                  className="w-full py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors font-medium"
                >
                  {fcSaving ? 'Zapisywanie...' : `Dodaj zaznaczone (${Object.values(fcSelected).filter(Boolean).length})`}
                </button>
              </div>
            )}

            {fcPreview && fcPreview.length === 0 && !fcLoading && (
              <p className="text-sm text-gray-500">Brak fiszek do wygenerowania.</p>
            )}
          </div>
        )}
      </div>

      {/* Items list */}
      <div className="border-t pt-3">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">
          Materiały ({items.length})
        </h4>
        {items.length === 0 ? (
          <p className="text-sm text-gray-400">Brak materiałów</p>
        ) : (
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {items.map(item => (
              <div key={item.id} className="flex items-center justify-between text-sm py-1 px-2 rounded hover:bg-gray-50">
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    item.type === 'lesson' ? 'bg-blue-100 text-blue-700' :
                    item.type === 'test' ? 'bg-purple-100 text-purple-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {item.type === 'lesson' ? 'Lekcja' :
                     item.type === 'test' ? 'Test' :
                     item.type === 'exercise' ? 'Ćwiczenie' : item.type}
                  </span>
                  <span className="truncate max-w-[200px]">{item.title || `#${item.item_id}`}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {item.score != null && (
                    <span className={`text-xs font-medium ${
                      item.score >= 4 ? 'text-green-600' :
                      item.score >= 3 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {item.score}/5
                    </span>
                  )}
                  <button
                    onClick={() => startItem(item)}
                    className="text-xs font-medium text-indigo-600 hover:text-indigo-800 whitespace-nowrap"
                    title="Rozpocznij naukę z tego materiału"
                  >
                    Ucz się →
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main Topics Page ───────────────────────────────────────────────────────
export default function TopicsPage() {
  const navigate = useNavigate();
  const userId = getUserId();

  const [view, setView] = useState('list'); // 'list' | 'tree' | 'due'
  const [topics, setTopics] = useState([]);
  const [tree, setTree] = useState({});
  const [dueTopics, setDueTopics] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [expandedCategories, setExpandedCategories] = useState({});
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [sortBy, setSortBy] = useState('name');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (categoryFilter) params.category = categoryFilter;
      if (sortBy) params.sort = sortBy;

      const [topicsRes, treeRes, dueRes, statsRes] = await Promise.all([
        getTopics(userId, params).catch(() => ({ topics: [] })),
        getTopicTree(userId).catch(() => ({ tree: {} })),
        getDueTopics(userId).catch(() => ({ topics: [] })),
        getTopicStats(userId).catch(() => ({})),
      ]);

      setTopics(topicsRes.topics || []);
      setTree(treeRes.tree || {});
      setDueTopics(dueRes.topics || []);
      setStats(statsRes);
    } catch (e) {
      console.error('Failed to fetch topics:', e);
    } finally {
      setLoading(false);
    }
  }, [userId, categoryFilter, sortBy]);

  useEffect(() => {
    if (!userId) { navigate('/placement'); return; }
    fetchData();
  }, [userId, fetchData]);

  // Filter topics by search
  const filteredTopics = topics.filter(t =>
    !search || t.name.toLowerCase().includes(search.toLowerCase()) ||
    (t.description && t.description.toLowerCase().includes(search.toLowerCase()))
  );

  const toggleCategory = (cat) => {
    setExpandedCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
  };

  if (loading) return <PageLoader />;

  return (
    <div className="max-w-4xl mx-auto p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Layers className="text-indigo-600" size={28} />
          <div>
            <h1 className="text-2xl font-bold">Bank wiedzy</h1>
            <p className="text-xs text-gray-500">Tematy → materiały, z opanowaniem i powtórkami</p>
          </div>
        </div>
        <button
          onClick={fetchData}
          className="p-2 text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
          title="Odśwież"
        >
          <RefreshCw size={18} />
        </button>
      </div>

      {/* Stats bar */}
      {stats && stats.total_topics > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-white rounded-xl shadow-sm border p-3 text-center">
            <div className="text-2xl font-bold text-indigo-600">{stats.total_topics}</div>
            <div className="text-xs text-gray-500">Tematów</div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border p-3 text-center">
            <div className="text-2xl font-bold text-orange-500">{stats.due_now}</div>
            <div className="text-xs text-gray-500">Do powtórki</div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border p-3 text-center">
            <div className="text-2xl font-bold text-green-500">{stats.mastered}</div>
            <div className="text-xs text-gray-500">Opanowane</div>
          </div>
          <div className="bg-white rounded-xl shadow-sm border p-3 text-center">
            <div className="text-2xl font-bold text-yellow-500">
              {Math.round((stats.avg_memory_strength || 0) * 100)}%
            </div>
            <div className="text-xs text-gray-500">Śr. zapamiętanie</div>
          </div>
        </div>
      )}

      {/* View tabs */}
      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1">
        {[
          { key: 'list', label: 'Lista', icon: BookOpen },
          { key: 'tree', label: 'Kategorie', icon: Layers },
          { key: 'due', label: 'Do powtórki', icon: Clock },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setView(key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-md text-sm font-medium transition-colors ${
              view === key
                ? 'bg-white text-indigo-600 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Icon size={16} />
            {label}
            {key === 'due' && dueTopics.length > 0 && (
              <span className="bg-orange-500 text-white text-xs rounded-full px-1.5 py-0.5 min-w-[20px] text-center">
                {dueTopics.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Search & filters */}
      {view === 'list' && (
        <div className="flex gap-2 mb-4">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Szukaj tematu..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
            />
          </div>
          <select
            value={categoryFilter}
            onChange={e => setCategoryFilter(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          >
            <option value="">Wszystkie kategorie</option>
            {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
          >
            <option value="name">Nazwa</option>
            <option value="strength">Siła zapamiętania</option>
            <option value="due">Do powtórki</option>
            <option value="items">Liczba materiałów</option>
          </select>
        </div>
      )}

      {/* ── LIST VIEW ── */}
      {view === 'list' && (
        <div className="space-y-2">
          {filteredTopics.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Layers size={48} className="mx-auto mb-3 opacity-50" />
              <p>Brak tematów. Wygeneruj lekcję, aby rozpocząć.</p>
            </div>
          ) : (
            filteredTopics.map(topic => (
              <div key={topic.id}>
                <div
                  className={`bg-white rounded-xl shadow-sm border p-4 cursor-pointer hover:shadow-md transition-shadow ${
                    topic.is_due ? 'border-l-4 border-l-orange-400' : ''
                  }`}
                  onClick={() => setSelectedTopic(selectedTopic === topic.id ? null : topic.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold truncate">{topic.name}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${CATEGORY_COLORS[topic.category] || CATEGORY_COLORS.other}`}>
                          {CATEGORY_LABELS[topic.category] || topic.category}
                        </span>
                        {topic.is_due && (
                          <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full flex items-center gap-1">
                            <Clock size={10} /> Do powtórki
                          </span>
                        )}
                      </div>
                      {topic.description && (
                        <p className="text-sm text-gray-500 truncate">{topic.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-3 ml-4">
                      <div className="text-right">
                        <div className="text-xs text-gray-400">{topic.items_count} materiałów</div>
                        <div className="text-sm font-medium">{Math.round(topic.memory_strength * 100)}%</div>
                      </div>
                      <MemoryBar strength={topic.memory_strength} size="sm" />
                    </div>
                  </div>
                </div>
                {selectedTopic === topic.id && (
                  <TopicDetail topicId={topic.id} onClose={() => setSelectedTopic(null)} />
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* ── TREE VIEW ── */}
      {view === 'tree' && (
        <div className="space-y-2">
          {Object.keys(tree).length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Layers size={48} className="mx-auto mb-3 opacity-50" />
              <p>Brak tematów. Wygeneruj lekcję, aby rozpocząć.</p>
            </div>
          ) : (
            Object.entries(tree).map(([category, catTopics]) => (
              <div key={category} className="bg-white rounded-xl shadow-sm border overflow-hidden">
                <button
                  onClick={() => toggleCategory(category)}
                  className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {expandedCategories[category] ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                    <span className={`text-sm px-2 py-0.5 rounded-full border ${CATEGORY_COLORS[category] || CATEGORY_COLORS.other}`}>
                      {CATEGORY_LABELS[category] || category}
                    </span>
                    <span className="text-sm text-gray-400">({catTopics.length})</span>
                  </div>
                </button>
                {expandedCategories[category] && (
                  <div className="border-t divide-y">
                    {catTopics.map(topic => (
                      <div key={topic.id}>
                        <div
                          className={`p-3 pl-10 cursor-pointer hover:bg-gray-50 transition-colors ${
                            topic.is_due ? 'border-l-4 border-l-orange-400' : ''
                          }`}
                          onClick={() => setSelectedTopic(selectedTopic === topic.id ? null : topic.id)}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <span className="font-medium text-sm">{topic.name}</span>
                              {topic.is_due && (
                                <span className="ml-2 text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">
                                  Do powtórki
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-400">{topic.items_count}</span>
                              <div className="w-16">
                                <MemoryBar strength={topic.memory_strength} size="sm" />
                              </div>
                            </div>
                          </div>
                        </div>
                        {selectedTopic === topic.id && (
                          <div className="pl-10 pr-3 pb-3">
                            <TopicDetail topicId={topic.id} onClose={() => setSelectedTopic(null)} />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* ── DUE VIEW ── */}
      {view === 'due' && (
        <div className="space-y-2">
          {dueTopics.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <CheckCircle size={48} className="mx-auto mb-3 opacity-50" />
              <p>Brak tematów do powtórki. Świetna robota!</p>
            </div>
          ) : (
            dueTopics.map(topic => (
              <div key={topic.id}>
                <div
                  className="bg-white rounded-xl shadow-sm border border-l-4 border-l-orange-400 p-4 cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => setSelectedTopic(selectedTopic === topic.id ? null : topic.id)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{topic.name}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${CATEGORY_COLORS[topic.category] || CATEGORY_COLORS.other}`}>
                          {CATEGORY_LABELS[topic.category] || topic.category}
                        </span>
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        {topic.days_until_review < 0
                          ? `Przeterminowany o ${Math.abs(topic.days_until_review)} dni`
                          : 'Do powtórki dziś'}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <div className="text-xs text-gray-400">{topic.items_count} materiałów</div>
                        <div className="text-sm font-medium">{Math.round(topic.memory_strength * 100)}%</div>
                      </div>
                      <MemoryBar strength={topic.memory_strength} size="sm" />
                    </div>
                  </div>
                </div>
                {selectedTopic === topic.id && (
                  <TopicDetail topicId={topic.id} onClose={() => setSelectedTopic(null)} />
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
