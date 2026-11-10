import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

createRoot(document.getElementById('root')).render(<App />)
// index.html paints the sunset photo on sign-in routes before this file loads; the page's own background takes over now.
requestAnimationFrame(() => requestAnimationFrame(() => document.documentElement.classList.remove('auth-boot')))
