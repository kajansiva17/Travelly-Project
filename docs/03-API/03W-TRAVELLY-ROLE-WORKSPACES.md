# Travelly — One workspace per person (sign-in destination and role workspaces)

Owner request, 12 Nov 2026. Replaces the 12 Nov morning rule "plain sign-in always opens the Passenger dashboard".
This is mostly screen work (UI Claude). The backend support listed below is built on `claude-work`.

## 1. Where sign-in goes

| Signed in from | Has the role | Goes to |
|---|---|---|
| Home page / plain login / registration | — | the **highest role's** dashboard: **Admin > Owner > Driver > Passenger** |
| Owner landing page (Owner button) | approved OWNER | Owner dashboard |
| Owner landing page | no OWNER role yet (or pending/rejected) | Owner application form / its status (`/owner/onboarding`) |
| Driver landing page (Driver button) | approved DRIVER | Driver dashboard |
| Driver landing page | no DRIVER role yet | Driver application form / its status (`/driver/onboarding`) |

Examples:
- Owner + Passenger → Owner dashboard from anywhere.
- Driver + Passenger → Driver dashboard.
- Owner + Driver + Passenger → Owner dashboard.
- Passenger only → Passenger dashboard.

Rules:
- Use `approved_roles` from `GET /users/me` (or `/users/me/roles`).
- A signed-in person who opens `/login` gets the same rule.
- After logout nothing is remembered (already built), so the next person never lands on the previous person's page.
- Code: `loginDestination()` in `Frontend/src/routes/workspaceRoutes.js`. Today it sends a plain sign-in to
  `/dashboard`; change it to the priority order above.

## 2. One dashboard holds everything

The person stays in the workspace of their highest role. **Its sidebar never changes.**

- **Owner workspace** keeps the Owner sidebar and adds:
  - **Travel & booking**: the Passenger features, rendered inside the Owner workspace, not by navigating to
    `/dashboard`. Search, book (private hire and tickets), pay, cancel, the replacement-change card, pickup code, my
    trips and their history.
  - **My driving**: shown **always, but only to a person approved as both Owner and Driver** (owner decision 12 Nov
    2026). Driving, self-drive included, needs the approved DRIVER role and a matching licence, so an Owner-only person
    never drives and does not see this menu.
    - Contents: assigned trips, passenger check (QR/PIN), start, live position, problem on the road, finish, and
      driving history.
    - With nothing to drive it shows an empty state: "Trips you drive yourself appear here."
  - **Owner sidebar order:** Overview, My vehicles, Prices, Routes, Ticket departures, Bookings for my vehicles,
    Replacement requests, Settlements, Travel & booking, My driving (Owner + Driver only), then Settings, Profile and
    Logout.
  - No separate Driver or Passenger dashboard is needed.
- **Driver workspace** keeps the Driver sidebar and adds **Travel & booking**, as above.
- **Passenger-only** people keep the Passenger dashboard.
- **Admin** is unchanged.
- **Workspace switcher:** the Passenger and Driver dashboards are no longer needed by someone with a higher role.
  Hide the switch, or keep it only as a shortcut that opens the same sections inside the current workspace.

Implementation hint: reuse the existing Passenger and Driver page components inside the current workspace shell
(routes such as `/owner/travel/...`, `/owner/driving/...`, `/driver/travel/...`), instead of copying pages.

## 3. Backend support (built)

- **Every account already has the PASSENGER role** (given at registration), so an Owner or Driver can book, pay and
  cancel with their own account. No backend change was needed for that.
- **`GET /api/v1/bookings`**: each item now carries **`viewer_roles`**, how the caller takes part:
  - `PASSENGER`: booked it.
  - `OWNER`: runs it.
  - `DRIVER`: drives it. For a ticket booking, this means the caller drives the departure's trip.
  - Optional filter **`?as=passenger|owner|driver`**; anything else gets 422.

```json
{ "items": [ { "id": "…", "booking_reference": "TKT-…", "status": "CONFIRMED", "…": "…", "viewer_roles": ["OWNER", "DRIVER"] } ] }
```

    - "My trips" (Travel & booking) = `?as=passenger`. "Bookings of my vehicles" = `?as=owner`.
    "My driving" = `?as=driver` plus `GET /scheduled-trips?driving=true`.
- **`GET /api/v1/scheduled-trips?driving=true`** (the departures I drive) stays Driver-only, which matches the
  rule above.
- **Trip operations** (start, pickup check, location, problem, finish) already allow whoever is the trip's assigned
  operator, so a self-driving Owner uses them directly.

## 4. Becoming an Owner or Driver from the profile (recommendation)

**Yes. Add a "My roles" section under Profile**, and keep the landing-page route as well.

- **What it shows:**
  - Passenger ✓.
  - For each of Owner and Driver: Approved ✓ / Waiting for approval / Needs correction (with the Admin's reason) /
    "Become an Owner" / "Become a Driver".
- **Data:** `GET /users/me/role-requests/{OWNER|DRIVER}/status` (existing).
- **The button opens the same application form** as the landing page (`/owner/onboarding`, `/driver/onboarding`).
  One form, two entry points; no second copy to keep in sync.
- **Why:**
  - People already signed in should not have to log out and find the landing page.
  - They can see their application status and fix a rejected one in the same place.
  - The landing pages stay the way for new visitors.
- No backend change: the role application and status endpoints already exist.
