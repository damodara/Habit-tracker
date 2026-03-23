from datetime import time as dt_time, timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework import status

from .models import Habit
from .tasks import send_habit_reminder


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="u1", password="pass12345")


def auth_client(client, token: str):
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.mark.django_db
def test_register(api_client):
    resp = api_client.post(
        "/api/auth/register/",
        {"username": "newuser", "password": "strongpass123", "email": ""},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert "token" in resp.data


@pytest.mark.django_db
def test_login(api_client):
    User.objects.create_user(username="u2", password="pass12345")

    resp = api_client.post(
        "/api/auth/login/",
        {"username": "u2", "password": "pass12345"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert "token" in resp.data


@pytest.mark.django_db
def test_habit_crud_and_permissions(api_client, user):
    token = Token.objects.create(user=user).key
    auth_client(api_client, token)

    other = User.objects.create_user(username="other", password="pass12345")
    other_token = Token.objects.create(user=other).key

    habit_resp = api_client.post(
        "/api/habits/",
        {
            "place": "Home",
            "time": "08:00:00",
            "action": "Exercise",
            "execution_time": 60,
            "periodicity": 1,
            "is_pleasant": False,
            "is_public": False,
        },
        format="json",
    )
    assert habit_resp.status_code == status.HTTP_201_CREATED
    habit_id = habit_resp.data["id"]

    resp_list = api_client.get("/api/habits/")
    assert resp_list.status_code == status.HTTP_200_OK
    assert len(resp_list.data["results"]) == 1

    # Second user can't access the first user's habit.
    api_client2 = APIClient()
    auth_client(api_client2, other_token)
    resp = api_client2.get(f"/api/habits/{habit_id}/")
    assert resp.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)

    # Update.
    resp_patch = api_client.patch(
        f"/api/habits/{habit_id}/",
        {"place": "Park"},
        format="json",
    )
    assert resp_patch.status_code in (status.HTTP_200_OK, status.HTTP_202_ACCEPTED, status.HTTP_204_NO_CONTENT)

    # Delete.
    resp_del = api_client.delete(f"/api/habits/{habit_id}/")
    assert resp_del.status_code == status.HTTP_204_NO_CONTENT
    assert Habit.objects.count() == 0


@pytest.mark.django_db
def test_public_habits(api_client, user):
    # Public + private.
    Habit.objects.create(
        user=user,
        place="Park",
        time=dt_time(18, 0, 0),
        action="Walk",
        execution_time=120,
        is_public=True,
    )
    Habit.objects.create(
        user=user,
        place="Home",
        time=dt_time(8, 0, 0),
        action="Exercise",
        execution_time=60,
        is_public=False,
    )

    resp = api_client.get("/api/habits/public/")
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data["results"]) == 1
    assert resp.data["results"][0]["action"] == "Walk"


@pytest.mark.django_db
def test_pagination(api_client, user):
    token = Token.objects.create(user=user).key
    auth_client(api_client, token)

    for i in range(6):
        Habit.objects.create(
            user=user,
            place=f"P{i}",
            time=dt_time(8, 0, 0),
            action=f"A{i}",
            execution_time=60,
            periodicity=1,
        )

    resp = api_client.get("/api/habits/")
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.data["results"]) == 5


@pytest.mark.django_db
def test_validators_in_serializer(api_client, user):
    token = Token.objects.create(user=user).key
    auth_client(api_client, token)

    # execution_time > 120
    resp = api_client.post(
        "/api/habits/",
        {
            "place": "Home",
            "time": "08:00:00",
            "action": "Exercise",
            "execution_time": 150,
            "periodicity": 1,
            "is_pleasant": False,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # periodicity > 7
    resp = api_client.post(
        "/api/habits/",
        {
            "place": "Home",
            "time": "08:00:00",
            "action": "Exercise",
            "execution_time": 60,
            "periodicity": 8,
            "is_pleasant": False,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # pleasant habit cannot have reward
    resp = api_client.post(
        "/api/habits/",
        {
            "place": "Home",
            "time": "08:00:00",
            "action": "Pleasant",
            "execution_time": 60,
            "periodicity": 1,
            "is_pleasant": True,
            "reward": "Chocolate",
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_habit_completion_rule(api_client, user):
    token = Token.objects.create(user=user).key
    auth_client(api_client, token)

    habit = Habit.objects.create(
        user=user,
        place="Home",
        time=dt_time(8, 0, 0),
        action="Exercise",
        execution_time=60,
        periodicity=1,
    )
    habit.last_completed_at = timezone.now() - timedelta(days=8)
    habit.save(update_fields=["last_completed_at"])

    resp = api_client.post(f"/api/habits/{habit.id}/complete/", {})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_celery_reminder_task_sends_due_habits(monkeypatch, user, db):
    # Telegram sending is mocked.
    calls = []

    def fake_send(message):
        calls.append(message)
        return True

    monkeypatch.setattr("habits.tasks.send_telegram_message", fake_send)

    now = timezone.now()
    habit = Habit.objects.create(
        user=user,
        place="Home",
        time=dt_time(8, 0, 0),
        action="Exercise",
        execution_time=60,
        periodicity=2,
        is_pleasant=False,
    )
    habit.next_reminder_at = now + timedelta(seconds=30)
    habit.save(update_fields=["next_reminder_at"])

    # Pleasant habit is skipped by filter.
    pleasant = Habit.objects.create(
        user=user,
        place="Home",
        time=dt_time(8, 0, 0),
        action="Meditate",
        execution_time=60,
        periodicity=1,
        is_pleasant=True,
    )
    pleasant.next_reminder_at = now + timedelta(seconds=30)
    pleasant.save(update_fields=["next_reminder_at"])

    result = send_habit_reminder(now=now)
    assert result["sent"] == 1
    assert len(calls) == 1
    habit.refresh_from_db()
    assert habit.next_reminder_at > now
