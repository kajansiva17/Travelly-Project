// Any page can open the booking chat of a booking: openChat(bookingId). ChatHost (in the workspace shell) listens and shows the chat on top of the page.
export const OPEN_CHAT = 'travelly:open-chat'
export const BELL_OPENED = 'travelly:bell-opened'
export const openChat = bookingId => { if (bookingId) window.dispatchEvent(new CustomEvent(OPEN_CHAT, { detail: { bookingId } })) }
export const bellOpened = () => window.dispatchEvent(new Event(BELL_OPENED))
