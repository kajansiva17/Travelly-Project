export function emailError(value) {
  const email = value.trim()
  const parts = email.split('@')
  const local = parts[0], domain = parts[1] || ''
  if (email.length > 254 || parts.length !== 2 || !local || /\s/u.test(email) || local.startsWith('.') || local.endsWith('.') || local.includes('..') || !/^[^<>(),;:"\\[\]]+$/u.test(local) || !domain.includes('.') || domain.split('.').some(label => !label || label.startsWith('-') || label.endsWith('-')) || /[\s/\\:#?]/u.test(domain) || /^[0-9.]+$/.test(domain) || /\.(local|localhost|test|invalid)$/i.test(domain)) {
    return 'Enter a valid public email address, such as name@example.com, without spaces inside it.'
  }
  return ''
}

export function passwordErrors(value) {
  const errors = []
  if ([...value].length < 12) errors.push('Use at least 12 characters.')
  if ([...value].length > 128) errors.push('Use at most 128 characters.')
  if (!/\p{Lu}/u.test(value)) errors.push('Add an uppercase letter.')
  if (!/\p{Ll}/u.test(value)) errors.push('Add a lowercase letter.')
  if (!/\p{Nd}/u.test(value)) errors.push('Add a number.')
  if (!/[\p{P}\p{S}]/u.test(value)) errors.push('Add a symbol.')
  if (/\s/u.test(value)) errors.push('Remove all whitespace.')
  if (/\p{C}/u.test(value)) errors.push('Remove control characters.')
  return errors
}
export const passwordHint = '12–128 characters, with an uppercase letter, a lowercase letter, a number and a symbol. No spaces or other whitespace.'
