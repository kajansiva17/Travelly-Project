import { t } from './language.js'

/* Friendly labels for the codes the API sends (statuses, roles, kinds, vehicle facts). Screens show these instead of the raw
   code (CONFIRMED, AWAITING_DRIVER, …). Every label has Tamil and Sinhala in messages.js (tests/language.test.js checks it).
   A code that is not listed is shown in sentence case ("SOME_NEW_CODE" -> "Some new code"). */
export const CODE_LABELS = {
  // review and records
  DRAFT: 'Draft', PENDING: 'Pending', SUBMITTED: 'Submitted', UNDER_REVIEW: 'Under review', NEEDS_CORRECTION: 'Needs correction',
  PENDING_VERIFICATION: 'Waiting for verification', APPROVED: 'Approved', REJECTED: 'Rejected', SUSPENDED: 'Suspended',
  SUPERSEDED: 'Superseded', WITHDRAWN: 'Withdrawn', NOT_REQUIRED: 'Not required', EXPIRED: 'Expired',
  ACTIVE: 'Active', INACTIVE: 'Inactive', PUBLISHED: 'Published', HIDDEN: 'Hidden', REMOVED: 'Removed', VISIBLE: 'Visible',
  OPEN: 'Open', CLOSED: 'Closed', ENDED: 'Ended', BLOCKED: 'Blocked', AVAILABLE: 'Available', BOOKED: 'Booked',
  // bookings and trips
  REQUESTED: 'Requested', OWNER_ACTION_REQUIRED: 'Waiting for the Owner', AWAITING_DRIVER: 'Waiting for a Driver',
  AWAITING_OTHER_OWNER: 'Waiting for another Owner', CONFIRMED: 'Confirmed', ACCEPTED: 'Accepted', DECLINED: 'Declined',
  SCHEDULED: 'Scheduled', READY: 'Ready', IN_PROGRESS: 'In progress', ON_TRIP: 'On trip', BREAKDOWN: 'Vehicle broke down',
  ASSISTANCE_REQUIRED: 'Help needed', COMPLETED: 'Completed', CANCELLED: 'Cancelled', COMMITTED: 'Committed', DISRUPTED: 'Disrupted',
  UNCONFIRMED: 'Unconfirmed', STALE: 'Stale',
  // money
  PAID: 'Paid', REFUNDED: 'Refunded', PARTIALLY_REFUNDED: 'Partly refunded', FAILED: 'Failed', PROCESSING: 'Processing',
  QUEUED: 'Queued', SENT: 'Sent', DELIVERED: 'Delivered', READ: 'Read',
  // people and kinds
  PASSENGER: 'Passenger', OWNER: 'Owner', DRIVER: 'Driver', ADMIN: 'Admin', PERSONAL: 'Personal', BOOKING: 'Booking',
  AVAILABILITY_BLOCK: 'Availability block', MAINTENANCE: 'Maintenance', PRIVATE_HIRE: 'Private hire', TICKET: 'Ticket', RENTAL: 'Rental',
  // price methods
  DISTANCE: 'Distance', TIME: 'Time', FIXED: 'Fixed price', EVENT_PACKAGE: 'Event package',
  // documents
  VEHICLE_REGISTRATION: 'Vehicle registration', INSURANCE: 'Insurance', REVENUE_LICENCE: 'Revenue licence',
  OWNER_AUTHORISATION: 'Owner or company authorisation', EMISSION: 'Emission certificate', FITNESS: 'Fitness certificate',
  ROUTE_PERMIT: 'Route permit', DRIVING_LICENCE: 'Driving licence', NIC: 'National identity card', PASSPORT: 'Passport',
  BUSINESS_REGISTRATION: 'Business registration', BANK_PROOF: 'Bank proof',
  // vehicle facts
  CAR: 'Car', VAN: 'Van', BUS: 'Bus', THREE_WHEELER: 'Three-wheeler',
  ICE: 'Petrol or diesel engine', MHEV: 'Mild hybrid', HEV: 'Hybrid', PHEV: 'Plug-in hybrid', BEV: 'Electric',
  PETROL: 'Petrol', DIESEL: 'Diesel', SELF: 'Myself', OTHER_PERSON: 'Another person', COMPANY: 'A company',
}

// English text for a code, before translation.
export function codeEnglish(code) {
  if (code === null || code === undefined || code === '') return ''
  const key = String(code)
  if (CODE_LABELS[key]) return CODE_LABELS[key]
  // only codes (UPPER_CASE or snake_case) are reworded; ordinary text is kept
  if (!/^[A-Z0-9_ ]+$/.test(key) && !/^[a-z0-9]+(_[a-z0-9]+)+$/.test(key)) return key
  const words = key.replaceAll('_', ' ').toLowerCase().trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

// The label to show for a code, in the current language.
export const codeLabel = code => t(codeEnglish(code))
