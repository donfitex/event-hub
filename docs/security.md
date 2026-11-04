# Security

CSRF applies to website/session mutations. API token clients use Authorization headers. Argon2 hashes passwords; validators require at least 10 characters. Login locks an email/address pair for 15 minutes after five failures. Login API also has a scoped rate limit; global anonymous and user limits use cache counters. Production uses shared Redis when configured and a database-backed cache otherwise. NUM_PROXIES must match the trusted ingress topology; default zero ignores forwarded addresses.

CORS defaults to no cross-origin access. Explicit origins apply only to API URLs. Website CSP allows self-hosted assets and the configured image storage origin; admin and API docs are excluded because their bundled interfaces require other asset policies. Secure cookies, HSTS and HTTPS redirects are mandatory in production. Authenticated and API responses disable caching.

Uploads allow only verified JPG/PNG/WebP under 5 MB and 25 megapixels, stored with random names. The hosting proxy must enforce request limits and safe media serving. Organizer/staff roles are never writable through public signup/profile serializers.

Operational limits: Django REST Framework cache throttles are best effort under concurrent bursts, not a network abuse defense. Configure proxy/WAF limits for hostile traffic. Website login/signup/reset POST requests have hourly cache limits; reinforce these with proxy rate limits for public launch. SMTP delivery is at least once. Never expose development settings in production.
