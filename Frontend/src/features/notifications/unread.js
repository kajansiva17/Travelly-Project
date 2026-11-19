export const NOTIFICATION_POLL_MS = 15_000

export function unreadBadge(count) {
  const value = Number(count)
  if (!Number.isFinite(value) || value <= 0) return ''
  return value > 99 ? '99+' : String(Math.floor(value))
}
