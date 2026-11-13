/* Event hire (contract 03EV): where a booking carries its package {id, name, hours}.
   Before the Passenger accepts the price: proposal.quote.calculation.package. After acceptance: price.current.calculation.package.
   Admin oversight (GET /admin/workflow/bookings): event_package (null for other bookings). */
export const eventPackageOf=booking=>booking?.event_package||booking?.price?.current?.calculation?.package||booking?.proposal?.quote?.calculation?.package||null
