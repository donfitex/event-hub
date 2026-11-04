# Testing

Run `pytest --cov=apps --cov-report=term-missing` for the local SQLite suite. The 20-client last-seat concurrency test is intentionally skipped on SQLite because SQLite does not implement PostgreSQL row locks.

To run against PostgreSQL set TEST_POSTGRES=1, DB_HOST, DB_PORT, DB_NAME, DB_USER and DB_PASSWORD. The database user must have permission to create the isolated test database. CI provisions PostgreSQL 16 and runs this same suite including concurrency.

Coverage includes registration business rules, FIFO promotions, database uniqueness, deadlines and cancellation states, API role checks, private registration access, tokens, lockouts, account escalation attempts, CSRF and website journeys. Integration checks of actual SMTP, proxy TLS, media serving, backup restore and hosting persistence must run in the deployment environment.
