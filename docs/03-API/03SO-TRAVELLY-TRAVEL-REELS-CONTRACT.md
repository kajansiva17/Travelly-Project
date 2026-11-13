# Travelly — Travel Reels and social (PRD matrix 79–85, 95)

Status: built on `claude-work` (13 Nov 2026).
- Migration **`0012_social`** creates the PRD `social_posts` and `social_interactions` tables, so all **20 of 20** PRD
  tables now exist. Run `alembic upgrade head`.
- Base `/api/v1`. Errors: `{ "code", "message", "field_errors", "trace_id" }`.
- POSTs without fields still send a JSON body `{}`, because the API accepts JSON only.

## Rules (PRD + owner decisions 13 Nov 2026)

- **Who posts:** anyone signed in (Passenger, Owner, Driver).
- **Post types:**
  - `REEL`: a video, **up to 60 seconds and 50 MB** (MP4, MOV or WebM), with an optional thumbnail.
  - `PHOTO`: one photo.
  - `REVIEW`: words, 1–5 stars and an optional photo.
- **Public at once (owner decision):** a new post is shown straight away, with no approval queue. The **Admin can hide**
  a sensitive post (`HIDDEN`), and show it again, with a reason; each decision is audited. The PRD's PENDING queue
  is not used.
- **Who sees it:**

  | `visibility` | Seen by |
  |---|---|
  | `PUBLIC` | Everyone, signed in or not |
  | `FOLLOWERS` | People who follow the author |
  | `PRIVATE` | Only the author |

- **Views (owner decision):** `view_count` is the one column added to the PRD table. It counts once per person (or
  per address when signed out) per post per day.
- **Reviews:** only for a vehicle the person travelled in on a **completed trip**, private hire or ticket. One review
  per vehicle; it can be edited.
- **Likes and saves:** once per person. **Follow:** once per person. **Comments:** with one level of replies.
- **Reports:** go to the Admin's list. Hiding or restoring the post closes its open reports.
- **Media:**
  - Media is stored outside the database and served only through the API.
  - Photos and thumbnails are re-encoded to JPEG, with no metadata.
  - Videos are stored as sent, and support seeking (HTTP Range).
- `.env` settings: `SOCIAL_REEL_MAX_SECONDS=60`, `SOCIAL_REEL_MAX_MB=50`, and `SOCIAL_MEDIA_ROOT` (default
  `<PRIVATE_DOCUMENT_ROOT>/../social-media`).

## 1. Create — `POST /social/posts` (multipart/form-data, signed in)

| Field | Notes |
|---|---|
| `post_type` | `REEL` / `PHOTO` / `REVIEW` |
| `visibility` | `PUBLIC` / `FOLLOWERS` / `PRIVATE`, **required** |
| `file` | REEL: video (required). PHOTO: photo (required). REVIEW: photo (optional). |
| `thumbnail` | REEL only: a JPEG frame from the video (recommended; capture it in the browser with a canvas) |
| `duration_seconds` | REEL: the video length (1–60), read in the browser from `video.duration` |
| `caption` | Up to 2200 characters. `#tags` in it become `hashtags`. REVIEW: required. |
| `hashtags` | Optional extra tags, comma separated or a JSON list (30 at most) |
| `location_name`, `latitude`, `longitude` | Optional; both coordinates or neither |
| `linked_vehicle_id` | REVIEW: required |
| `linked_route_id`, `linked_scheduled_trip_id` | Optional |
| `rating` | REVIEW: 1–5 |

**201** = a post item (section 2).

Errors:
- 401: not signed in.
- 413 `MEDIA_TOO_LARGE`.
- 422 `REEL_TOO_LONG`, `INVALID_MEDIA`, `VALIDATION_ERROR`.
- 403 `REVIEW_NOT_ALLOWED`: no completed trip in that vehicle.
- 409 `ALREADY_REVIEWED`.
- 429: 20 posts an hour.

## 2. Feed — `GET /social/feed[?type=REEL|PHOTO|REVIEW&hashtag=&author=<reference>&before=&limit=]`

This is a public read; a signed-in viewer also sees followers-only posts.

```json
{ "items": [ {
  "id": "…", "version": 1, "post_type": "REEL",
  "author": { "reference": "TRV-…", "name": "Maya Fernando", "profile_image_url": null },
  "media_url": "/api/v1/social/posts/…/media", "thumbnail_url": "/api/v1/social/posts/…/thumbnail",
  "caption": "Ella train ride #ella", "hashtags": ["ella"], "location_name": "Ella", "latitude": "6.866700", "longitude": "81.046600",
  "linked_vehicle_id": null, "linked_route_id": null, "linked_scheduled_trip_id": null,
  "visibility": "PUBLIC", "moderation_status": "APPROVED", "published_at": "…", "duration_seconds": 42, "rating": null,
  "like_count": 12, "comment_count": 3, "share_count": 1, "view_count": 1200,
  "liked_by_me": false, "saved_by_me": false, "following_author": false, "is_mine": false } ],
  "next_before": "…" }
```

- **Next page:** `?before=<next_before>`. `limit` defaults to 20, 50 at most.
- **Media links:**
  - Use `media_url` / `thumbnail_url` as given, in `<video src>` / `<img src>`. No Bearer token is needed.
  - Followers-only and private posts come with `?t=…`, a signed link valid for 1 hour. When it expires, reload the
    feed.
- `GET /social/posts/{id}` returns one item.

## 3. Actions

| Call | Body | Reply |
|---|---|---|
| `POST /social/posts/{id}/views` | `{}` | `{ counted, view_count }`. Call it when a reel starts playing; public. |
| `POST /social/posts/{id}/like` | `{ "active": true }` / `false` | `{ active, like_count }` |
| `POST /social/posts/{id}/save` | `{ "active": … }` | `{ active }` |
| `POST /social/posts/{id}/share` | `{}` | `{ share_count, share_path: "/reels/<id>" }`. Then use `navigator.share` / copy the link. |
| `GET /social/posts/{id}/comments` | — | `{ items: [ { id, author, text, created_at, can_remove, replies: [...] } ], comment_count }` |
| `POST /social/posts/{id}/comments` | `{ "text", "parent_id"? }` | The comment. A reply to a reply joins the same thread. |
| `POST /social/comments/{id}/remove` | `{}` | The commenter, the post author or the Admin |
| `POST /social/posts/{id}/report` | `{ "reason" }` (3–500) | 409 `OWN_POST` / `ALREADY_REPORTED` |
| `POST /social/users/{reference}/follow` | `{ "active": … }` | 409 `OWN_ACCOUNT` |

**Author only:**
- `PATCH /social/posts/{id}` with `{ expected_version, caption?, hashtags?, location_name?, visibility?, rating? }`.
  409 `VERSION_CONFLICT`: likes and comments also raise `version`, so reload and retry.
- `POST /social/posts/{id}/remove` with `{}` takes the post down.

## 4. People and reviews

- `GET /social/users/{reference}` → `{ reference, name, profile_image_url, followers, following, post_count,
  followed_by_me, is_me, posts: [...] }`.
- `GET /social/me/saved` returns my saved posts.
- `GET /social/me/reviewable-vehicles` → `{ items: [ { vehicle_id, name, already_reviewed } ] }`. Use it for the
  "Write a review" picker.
- `GET /social/vehicles/{vehicle_id}/reviews` → `{ average_rating: "4.5", rating_count, items }`. Show it on the
  vehicle page and in search results.

## 5. Admin

- `GET /admin/social/posts[?status=APPROVED|HIDDEN&reported=true]`: the latest 200 posts, each with `open_reports`
  (reasons and times) and signed media links.
- `POST /admin/social/posts/{id}/moderation` with `{ "expected_version", "action": "HIDE" | "RESTORE", "reason" }`.
  - The reason is required (422 `REASON_REQUIRED`). The decision is audited.
  - 409 `VERSION_CONFLICT` / `NO_CHANGE`.

## Screens (UI Claude)

- **Dashboard "Travel Reels" card:**
  - `GET /social/feed?type=REEL&limit=8`: thumbnails with the place and **`view_count` views**. See all → `/reels`.
- **`/reels` page:**
  - Vertical, full-height player. Swipe or scroll for the next reel; autoplay muted, tap for sound.
  - Count a view when playback starts (`/views`).
  - Side buttons: like, comment, save, share, the author (follow), and ⋯ (report, or edit/remove on my own post).
  - Tabs: Reels / Photos / Reviews / Following.
  - Hashtag and place chips open filtered feeds.
  - `/reels/<id>` opens one post (`share_path`).
- **"+ Post":**
  1. Pick Reel / Photo / Review.
  2. **Reel:** choose or record a video. Read `duration` in the browser; over 60 s, show "Trim to 60 seconds" and do
     not upload. Over 50 MB, show the limit. Grab a frame on a canvas for `thumbnail`.
  3. Caption with #tags, place (optional), and visibility (Everyone / Followers / Only me).
  4. Show upload progress.
  - **Review:** pick the vehicle from `/social/me/reviewable-vehicles`, then stars, words and an optional photo.
- **Profile (`/social/users/<reference>`):** posts grid, followers/following counts, Follow button. On a person's own
  profile, show the Saved tab.
- **Vehicle page / search card:** ★ `average_rating` (`rating_count`) and the latest reviews.
- **Admin → "Social reviews"** (the existing `/admin/social-reviews` route): the reported list first, with Hide /
  Restore and a reason.
- Strings go in `messages.trips.js`.
