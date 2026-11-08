# Travelly landing assets

36 separate PNG assets recreated from the approved flattened page mockups using the built-in image generation tool. These are visual recreations, not exact extracted source layers. 3 full-page reference PNGs are included separately.

## Implementation guidance

- Passenger, Owner and Driver are separate public landing pages. Navbar links For Owners and For Drivers navigate to their own pages.
- Keep glass and light effects within the hero. Use matte navy/slate sections below; avoid a white page background.
- Hero images contain no headings or controls. Build text, navigation, forms, cards and buttons in HTML/CSS.
- Use service symbols rather than photographs in service cards. Preserve image aspect ratios with object-fit: contain for icons and vehicles.
- Transparent PNGs include vehicles, symbols and logo. Photos and hero backgrounds are opaque.
- Generated destination artwork is illustrative, not documentary photography; Kandy artwork is stylized/composite.
- The workspace preview is an illustration, not an implemented dashboard. Rebuild its UI as accessible components when interactive.
- Reference mockup copy is not a source of truth for business rules or implemented features. Inspect the actual repository and handoff before implementation.
- PNGs are full-resolution source/reference assets. Create optimized responsive derivatives for production, keeping these originals.

## Asset map

| File | Primary page/use |
|---|---|
| heroes/passenger-hero.png | passenger — passenger hero |
| heroes/owner-hero.png | owner — owner hero |
| heroes/driver-hero.png | driver — driver hero |
| icons/service-hire.png | passenger — service hire |
| icons/service-tickets.png | passenger — service tickets |
| icons/service-rentals.png | passenger — service rentals |
| vehicles/vehicle-van.png | passenger — vehicle van |
| vehicles/vehicle-car.png | passenger — vehicle car |
| vehicles/vehicle-bus.png | passenger — vehicle bus |
| destinations/destination-kandy.png | passenger — destination kandy |
| destinations/destination-ella.png | passenger — destination ella |
| vehicles/vehicle-tuk-tuk.png | passenger — vehicle tuk tuk |
| destinations/destination-galle.png | passenger — destination galle |
| vehicles/fleet.png | owner — fleet |
| icons/bookings-calendar.png | owner — bookings calendar |
| icons/approved-driver.png | owner — approved driver |
| icons/assignment-review.png | driver — assignment review |
| icons/shared-check.png | passenger — shared check |
| icons/trip-route.png | driver — trip route |
| icons/documents.png | driver — documents |
| icons/shared-search.png | passenger — shared search |
| icons/assignment-accept-decline.png | driver — assignment accept decline |
| icons/availability.png | driver — availability |
| icons/assignments.png | driver — assignments |
| icons/shared-profile.png | owner — shared profile |
| icons/owner-self-drive.png | owner — owner self drive |
| icons/shared-folder.png | owner — shared folder |
| icons/shared-shield.png | owner — shared shield |
| icons/shared-location.png | passenger — shared location |
| icons/shared-document.png | passenger — shared document |
| icons/shared-payment.png | passenger — shared payment |
| icons/shared-notification.png | passenger — shared notification |
| icons/shared-edit.png | driver — shared edit |
| branding/shared-logo.png | passenger — shared logo |
| illustrations/driver-workspace-preview.png | driver — driver workspace preview |
| heroes/cta-landscape.png | passenger — cta landscape |

Shared icons, services and vehicle images may be reused across pages. prompts.json records generation prompts.

