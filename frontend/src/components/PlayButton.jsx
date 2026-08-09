import { useState, useRef, useEffect } from 'react'
import { Volume2, Loader2, Square } from 'lucide-react'

export default function PlayButton({ text, language, className = '' }) {
  const [loading, setLoading] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState(false)
  const audioRef = useRef(null)

  // Stop playback if the card gets swapped/unmounted mid-audio (e.g. "Next word").
  useEffect(() => () => audioRef.current?.pause(), [])

  const stop = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
    setIsPlaying(false)
  }

  const handleClick = async (e) => {
    e.stopPropagation()
    if (loading) return
    // Click while playing = stop, not restart.
    if (isPlaying) { stop(); return }
    if (!text) return
    setLoading(true)
    setError(false)
    try {
      const res = await fetch('/api/audio/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, language: language || 'German' }),
      })
      if (!res.ok) throw new Error('TTS failed')
      const data = await res.json()
      if (!data?.url) throw new Error('No audio URL in response')
      const audio = new Audio(data.url)
      audioRef.current = audio
      audio.onended = () => setIsPlaying(false)
      audio.onerror = () => setIsPlaying(false)
      setIsPlaying(true)
      audio.play()
    } catch (_err) {
      setError(true)
      setTimeout(() => setError(false), 2000)
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      title={isPlaying ? 'Zatrzymaj' : `Play: ${text}`}
      className={`inline-flex items-center justify-center w-6 h-6 rounded-full hover:bg-gray-700 text-gray-400 hover:text-indigo-300 transition-colors disabled:opacity-50 ${error ? 'text-red-400' : ''} ${isPlaying ? 'text-indigo-300' : ''} ${className}`}
    >
      {loading ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
      ) : isPlaying ? (
        <Square className="w-3 h-3 fill-current" />
      ) : (
        <Volume2 className="w-3.5 h-3.5" />
      )}
    </button>
  )
}
