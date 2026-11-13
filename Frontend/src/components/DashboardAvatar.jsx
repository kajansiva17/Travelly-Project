import { useState } from 'react'

// A missing or failed image keeps the same initial-based fallback.
export default function DashboardAvatar({ name, url }) {
  const [failedUrl, setFailedUrl] = useState(null)
  return <span className="dashboard-avatar">{url && url !== failedUrl
    ? <img src={url} alt="" referrerPolicy="no-referrer" onError={() => setFailedUrl(url)}/>
    : Array.from(name || 'T')[0]}</span>
}
