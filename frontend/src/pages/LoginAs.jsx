import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'
import { magicLogin, setUserId } from '../api/client'

/**
 * /login-as?key=<magic-token> — opened on a new device (e.g. phone) from the
 * link shown in the Profile page. Resolves the key against the backend,
 * stores the account in localStorage, and lands on the home page.
 */
export default function LoginAs() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const [state, setState] = useState('working') // working | ok | fail

  useEffect(() => {
    const key = params.get('key') || ''
    if (key.length < 16) { setState('fail'); return }

    magicLogin(key)
      .then((user) => {
        setUserId(user.user_id)
        localStorage.setItem('userName', user.name)
        localStorage.setItem('userLanguage', user.target_language)
        setState('ok')
        setTimeout(() => navigate('/', { replace: true }), 1200)
      })
      .catch(() => setState('fail'))
  }, [params, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center p-4 dark:bg-gray-950 bg-gray-50">
      <div className="text-center space-y-4">
        {state === 'working' && (
          <>
            <Loader2 className="w-10 h-10 animate-spin mx-auto text-blue-500" />
            <p className="text-gray-600 dark:text-gray-300">Logowanie na tym urządzeniu…</p>
          </>
        )}
        {state === 'ok' && (
          <>
            <CheckCircle className="w-10 h-10 mx-auto text-green-500" />
            <p className="text-gray-800 dark:text-gray-100 font-medium">Zalogowano! Przechodzę do aplikacji…</p>
          </>
        )}
        {state === 'fail' && (
          <>
            <XCircle className="w-10 h-10 mx-auto text-red-500" />
            <p className="text-gray-800 dark:text-gray-100 font-medium">Link logowania jest nieprawidłowy lub wygasł.</p>
            <button
              onClick={() => navigate('/', { replace: true })}
              className="text-blue-500 underline"
            >
              Wróć do strony głównej
            </button>
          </>
        )}
      </div>
    </div>
  )
}
