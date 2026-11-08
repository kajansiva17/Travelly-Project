import { getCountries, getCountryCallingCode, parsePhoneNumberFromString } from 'libphonenumber-js/max'

const names = new Intl.DisplayNames(['en'], { type: 'region' })
export const phoneCountries = getCountries().map(code => ({
  code, name: names.of(code), callingCode: getCountryCallingCode(code),
})).sort((a, b) => a.name.localeCompare(b.name))
const countryCodes = new Set(phoneCountries.map(country => country.code))
const entryHint = 'Select your country code and enter the national number without the country code.'

export function registrationPhone(country, nationalNumber) {
  if (/[\u0000-\u001f\u007f-\u009f]/.test(nationalNumber)) throw new Error(entryHint)
  if (!nationalNumber.trim()) return null
  if (!countryCodes.has(country)) throw new Error('Select a valid country code.')
  if (!/^[0-9 ()-]+$/.test(nationalNumber)) throw new Error(entryHint)
  const digits = nationalNumber.replace(/[^0-9]/g, '')
  if (digits.startsWith('00')) throw new Error(entryHint)
  const phone = parsePhoneNumberFromString(nationalNumber, { defaultCountry: country, extract: false })
  if (!phone || !phone.isValid() || phone.ext || phone.country !== country) {
    throw new Error('Enter a complete, valid mobile number for the selected country.')
  }
  // Prevent the parser silently stripping a repeated calling code. Accept only
  // national digits or the selected country's own national/trunk format.
  const nationalDigits = phone.formatNational().replace(/[^0-9]/g, '')
  if (digits !== phone.nationalNumber && digits !== nationalDigits) throw new Error(entryHint)
  if (phone.number.length > 16) throw new Error('Enter a valid mobile number of at most 15 international digits.')
  return phone.number
}
