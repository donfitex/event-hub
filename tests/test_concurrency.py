from concurrent.futures import ThreadPoolExecutor
import pytest
from django.db import connection, close_old_connections
from apps.users.models import User
from apps.registrations.services import register


@pytest.mark.django_db(transaction=True)
def test_twenty_clients_compete_for_last_seat(event):
    if connection.vendor != "postgresql":
        pytest.skip("Row-lock concurrency requires PostgreSQL; exercised by CI.")
    users = [User.objects.create_user(f"person{i}@example.com", "pass").pk for i in range(20)]

    def attempt(pk):
        close_old_connections()
        try:
            return register(User.objects.get(pk=pk), event.pk).status
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(attempt, users))
    assert results.count("REGISTERED") == 1
    assert results.count("WAITLISTED") == 19
