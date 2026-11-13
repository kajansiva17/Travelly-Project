import { createRoot } from 'react-dom/client'
import App from './App'
import { restoreSession } from './services/api'

// A reload keeps the person signed in: renew from the HttpOnly session cookie before the first screen is chosen.
restoreSession().finally(() => {
  createRoot(document.getElementById('root')).render(<App />)
  // index.html paints the sunset photo on sign-in routes before this file loads; the page's own background takes over now.
  requestAnimationFrame(() => requestAnimationFrame(() => document.documentElement.classList.remove('auth-boot')))
})
