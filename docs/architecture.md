# Architecture

`apps.users` links verified Neon identities to local users and owns role grants, session exchange and expiring local API tokens. `apps.events` owns categories, event validation, public visibility and organizer APIs. `apps.registrations` owns registrations, waitlist transitions, reminders and the durable email outbox. `apps.common` provides the website, security headers and API error handling.

Every seat-changing operation locks the same event row within a database transaction. PostgreSQL serializes competing registrations, cancellations, promotions and capacity edits. A partial unique constraint independently prevents duplicate active registrations. Cancelled registration rows remain as history. Waitlisted registrations are promoted in registration timestamp and primary-key order.

Notification records commit with the business transaction. Delivery is at least once: an SMTP success followed by a worker crash before database commit can cause a duplicate. Failed sends remain pending for retry. Schedule one or more delivery command workers; PostgreSQL row locks prevent workers from simultaneously sending the same pending row.

Event and registration admin pages are read-only to prevent bypassing business rules. Admins manage events using the API; organizers use their studio. Categories and user privileges are managed in Django admin.

The deployed preview uses Render for Django and Gunicorn, Neon PostgreSQL for application data and the cache table, and a private Neon Object Storage bucket for uploaded event images. Django issues short-lived signed media URLs. WhiteNoise serves bundled static assets. See [deployment](deployment.md) for configuration and [API](api.md) for the endpoint contract.
