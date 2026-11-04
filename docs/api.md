# API

All routes use `/api/v1/`. JSON successes wrap payloads in `data`; failures contain `error.code`, `error.message` and optional details. List payloads contain count, next, previous and results. Schema: `/api/schema/`.

Sign up with POST `users/register/` (`email`, `password`, optional first/last name). POST `users/login/` returns a token. Send `Authorization: Token <token>`. Tokens expire after 14 days. POST `users/logout/` revokes the token. GET/PATCH `users/profile/` edits names. Only staff may access `users/manage/` and `users/manage/{id}/` for role grants and account deactivation.

GET `events/` and `events/{id}/` are public; drafts are visible only to owners and staff. Filters: search, category (slug), location, status, date_from, date_to; sorting: ordering=start_datetime, -created_at, title. Pagination: page.

Organizers POST `events/`, PUT/PATCH `events/{id}/`, DELETE empty drafts, and POST `events/{id}/publish/`, `cancel/`, `complete/`. Status is read-only in generic edits. GET `events/mine/` and `events/dashboard/` report own events. GET `events/{id}/registrations/` accepts search=email; `registrations/export/` exports CSV. Staff can manage all events.

POST `events/{id}/register/` confirms a seat or adds a FIFO waitlist entry. Duplicate or closed registrations return 409. GET `registrations/`, GET `registrations/{id}/`, POST `registrations/{id}/cancel/` are scoped to the attendee (staff can moderate all). Cancellation closes when the event starts. Unknown or private objects return 404; missing authentication returns 401; insufficient role returns 403. Throttled traffic returns 429.

GET `categories/` is public; organizers may create categories, staff may edit/delete. Password reset is available through the website using emailed single-use Django tokens.
