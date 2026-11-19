// User-supplied PNG archive, 7 November. These are reconstructed standalone
// artwork files, not the exact original artwork embedded in the references.
export const landingArtwork = '/images/travelly/landing-scenes-2026-11-07/'
export const heroArtwork = {
  home: 'home/hero-coastal-vehicle-lineup',
  driver: 'driver/hero-tea-country-driver',
  owner: 'owner/hero-fleet-depot',
}
export const cardArtwork = {
  'home-hire': 'home/card-vehicle-hire-family',
  'home-tickets': 'home/card-bus-van-tickets',
  'home-rentals': 'home/card-rental-key-handover',
  'home-airport': 'home/card-airport-pickup',
  'home-local': 'home/card-local-ride',
  'home-long-distance': 'home/card-long-distance-route',
  'home-multi-day': 'home/card-multi-day-journey',
  'driver-assignments': 'driver/card-assigned-trips',
  'driver-routes': 'driver/card-trip-routes',
  'driver-expenses': 'driver/card-trip-expenses',
  'driver-payments': 'driver/card-payment-records',
  'driver-before': 'driver/card-before-pickup',
  'driver-during': 'driver/card-during-trip',
  'driver-after': 'driver/card-after-trip',
  'owner-vehicles': 'owner/card-list-vehicles',
  'owner-bookings': 'owner/card-manage-bookings',
  'owner-drivers': 'owner/card-assign-drivers',
  'owner-maintenance': 'owner/card-track-maintenance',
  'owner-hire': 'owner/card-vehicle-hire-bus',
  'owner-tickets': 'owner/card-scheduled-tickets-interior',
  'owner-rentals': 'owner/card-rental-van',
}
export function artworkSources(file) {
  const [role, name] = file.split('/')
  const hero = name.startsWith('hero-')
  // Vector artwork (1536 x 1024 viewBox, same 3:2 ratio as the PNG cards) has no responsive raster sizes.
  if (name.endsWith('.svg')) return { src: `${landingArtwork}${file}`, width: 1536, height: 1024 }
  return {
    src: `${landingArtwork}${file}.png`,
    srcSet: `${landingArtwork}${role}/responsive/${name}-768w.png 768w, ${landingArtwork}${file}.png ${hero ? 1672 : 1536}w`,
    width: hero ? 1672 : 1536,
    height: hero ? 941 : 1024,
  }
}
