# Testing

Run `pytest --cov=apps --cov-report=term-missing` for the local SQLite suite. The 20-client last-seat concurrency test is intentionally skipped on SQLite because SQLite does not implement PostgreSQL row locks.

To run against PostgreSQL set TEST_POSTGRES=1, DB_HOST, DB_PORT, DB_NAME, DB_USER and DB_PASSWORD. The database user must have permission to create the isolated test database. CI provisions PostgreSQL 16 and runs this same suite including concurrency.

Coverage includes registration business rules, FIFO promotions, database uniqueness, deadlines and cancellation states, API role checks, private registration access, tokens, lockouts, account escalation attempts, CSRF and website journeys. Integration checks of actual SMTP, proxy TLS, media serving, backup restore and hosting persistence must run in the deployment environment.

Validate the generated API contract with
`python manage.py spectacular --settings=config.testing --file openapi.yaml --validate --fail-on-warn`.
The API suite exercises all 33 documented versioned REST operations across 21 resource paths,
plus the API index, schema and Swagger routes. It covers role boundaries, validation and state
conflicts, attendee search and CSV export, and the health check's database failure response.
Django admin and internal identity proxy routes have focused tests, separate from the REST contract.
