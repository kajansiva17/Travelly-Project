// Presentation rules only; every action is authorized and validated again by the backend.
export const roleActions = status => status === 'PENDING' ? ['APPROVED', 'REJECTED'] : status === 'APPROVED' ? ['SUSPENDED'] : []
export const documentActions = status => status === 'SUBMITTED' ? ['UNDER_REVIEW'] : status === 'UNDER_REVIEW' ? ['APPROVED', 'REJECTED', 'NEEDS_CORRECTION'] : []
export const needsReason = decision => ['REJECTED', 'SUSPENDED', 'NEEDS_CORRECTION'].includes(decision)
export const mayReview = user => ['ACTIVE', 'PENDING_VERIFICATION'].includes(user?.account_status) && user?.approved_roles?.includes('ADMIN')
export const actionLabel = decision => ({ APPROVED: 'Approve', REJECTED: 'Reject', SUSPENDED: 'Suspend', UNDER_REVIEW: 'Start review', NEEDS_CORRECTION: 'Request correction' }[decision])
export function decisionPayload(decision, version, reason = '') {
  const text = reason.trim()
  if (!Number.isInteger(version) || version < 1 || (needsReason(decision) && (!text || text.length > 2000))) throw new Error('Enter an applicant-visible reason between 1 and 2000 characters.')
  return { decision, version, reason: needsReason(decision) ? text : null }
}
