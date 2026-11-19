export function bookingPriceState(booking) {
  const proposal = booking?.proposal || {}
  const offered = proposal.kind === 'QUOTE' ? proposal.quote : null
  const agreed = booking?.price?.current || null
  const locationPending = proposal.kind === 'LOCATION_CONFIRMATION_REQUIRED'
  const revisionNeedsQuote = proposal.kind === 'CHANGE_REQUEST_UNPRICED'
  const hasApplicablePrice = Boolean(offered || agreed)

  return {
    agreed,
    offered,
    hasApplicablePrice,
    locationPending,
    revisionNeedsQuote,
    passengerAcceptancePending: Boolean(offered && !booking?.accepted_quote_digest),
    needsInitialQuote: !locationPending && !hasApplicablePrice && !booking?.accepted_quote_digest,
  }
}
