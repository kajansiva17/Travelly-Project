// Any page can open the booking chat of a booking: openChat(bookingId). ChatHost (in the workspace shell) listens and shows the chat on top of the page.
export const OPEN_CHAT = 'travelly:open-chat'
export const BELL_OPENED = 'travelly:bell-opened'
export const openChat = bookingId => { if (bookingId) window.dispatchEvent(new CustomEvent(OPEN_CHAT, { detail: { bookingId } })) }
// Returns true when a chat opened because of the bell (an unread message was waiting); then the notification list stays closed.
export const bellOpened = () => { const detail = { handled: false }; window.dispatchEvent(new CustomEvent(BELL_OPENED, { detail })); return detail.handled }
