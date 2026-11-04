# EventHub API

Open the [interactive API reference](https://eventhub-donfitex.onrender.com/api/docs/) or download the [OpenAPI schema](https://eventhub-donfitex.onrender.com/api/schema/). The application API starts at `/api/v1/`, which also exposes a discovery index. Keep the trailing slash on every route.

## Authentication

- **Deployed preview:** Sign in through the website with Neon Better Auth. API clients with a Neon JWT send `Authorization: Bearer <jwt>`. Django verifies the signature, issuer, audience and expiry and applies local role permissions. The browser sign-in proxy and session exchange under `/identity/` are internal to the website.
- **Local authentication mode:** With Neon Auth disabled, register with `POST /api/v1/users/register/` and log in with `POST /api/v1/users/login/`. Send the returned token as `Authorization: Token <token>`. Local tokens expire after 14 days. Both endpoints return `400 MANAGED_AUTH` in managed mode.
- **Django session:** Browser requests can use the Django session cookie. Unsafe methods require the CSRF token. Existing Django staff accounts can establish a session through `/admin/login/`.
- `POST /users/logout/` revokes local API tokens and ends the Django session. It does not revoke a Neon JWT. Sign out through the Neon session flow to end that session.

## Responses

JSON success responses wrap their payload in `data`. Lists return `count`, `next`, `previous` and `results` inside that envelope, with 12 results per page by default. Use `?page=2` or follow `next`. CSV is sent directly and `204` has no body. Errors from API handlers use `{"error":{"code":"NOT_FOUND","message":"...","details":{}}}`. Use the status and code for program logic. Common statuses include `400` invalid input, `401` missing or invalid authentication, `403` insufficient permissions, `404` missing or hidden resource, `409` state conflict and `429` rate limited.

## Endpoint reference

Paths in this table are relative to `/api/v1/`.

| Method | Path | Access | Successful response |
|---|---|---|---|
| GET | `/` | Public | API discovery links |
| GET | `/categories/` | Public | Paginated categories |
| POST | `/categories/` | Organizer or staff | 201 category |
| GET | `/categories/{id}/` | Public | Category |
| PUT, PATCH | `/categories/{id}/` | Staff | Updated category |
| DELETE | `/categories/{id}/` | Staff | 204. A category used by an event returns 409 |
| GET | `/events/` | Public | Paginated visible events |
| POST | `/events/` | Organizer or staff | 201 draft event owned by caller |
| GET | `/events/{id}/` | Public for visible events | Event details |
| PUT, PATCH | `/events/{id}/` | Event owner or staff | Updated event |
| DELETE | `/events/{id}/` | Event owner or staff | 204 for an empty draft |
| POST | `/events/{id}/publish/` | Event owner or staff | Published event |
| POST | `/events/{id}/cancel/` | Event owner or staff | Cancelled event and cancelled registrations |
| POST | `/events/{id}/complete/` | Event owner or staff | Completed event after its end time |
| POST | `/events/{id}/register/` | Signed in | 201 confirmed or waitlisted registration |
| GET | `/events/{id}/registrations/` | Event owner or staff | Paginated attendees. `search` filters by email substring |
| GET | `/events/{id}/registrations/export/` | Event owner or staff | CSV download of all event registrations |
| GET | `/events/mine/` | Organizer or staff | Paginated events owned by caller |
| GET | `/events/dashboard/` | Organizer or staff | Counts for caller's events, published events, completed events and confirmed registrations |
| GET | `/registrations/` | Signed in | Own registrations, or all registrations for staff |
| GET | `/registrations/{id}/` | Registration owner or staff | Registration detail |
| POST | `/registrations/{id}/cancel/` | Registration owner or staff | Cancelled registration. A released seat can promote the next waitlisted attendee |
| POST | `/users/register/` | Public, local mode | 201 user. Send email, password and optional names |
| POST | `/users/login/` | Public, local mode | Token and user. Send email and password |
| POST | `/users/logout/` | Signed in | 204 |
| GET | `/users/profile/` | Signed in | Current user |
| PUT, PATCH | `/users/profile/` | Signed in | Updated first and last names |
| GET | `/users/manage/` | Staff | Paginated users |
| GET | `/users/manage/{id}/` | Staff | User details including account status |
| PUT, PATCH | `/users/manage/{id}/` | Staff | Updated names, organizer role or active status |

Draft events are visible to their owner and staff. Public event queries accept `search`, `category` (slug), `location`, `status`, `date_from`, `date_to` and `ordering`. Dates are inclusive in `YYYY-MM-DD` format. Order by `start_datetime`, `created_at` or `title`, with `-` for descending. The `mine` endpoint uses the same filters.

Event creation and edits accept JSON. Use multipart form data for an image. Supply the title, description, category ID, location, venue, start and end timestamps, registration deadline and capacity. Use ISO 8601 timestamps with a time-zone offset. Event status changes, registration and cancellation actions take no body. Duplicate registration, closed registration and incompatible state changes return `409`.

## Operational routes

`GET /health/` runs a database query and returns `{"status":"ok","database":"ok"}` or HTTP 503 with `{"status":"unavailable"}`. These responses use no API envelope. Django admin, the organizer website and password reset pages are browser flows outside the versioned REST API. See [architecture](architecture.md), [testing](testing.md), and [deployment](deployment.md).
