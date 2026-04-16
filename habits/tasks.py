import json
import urllib.parse
import urllib.request
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import Habit


def send_telegram_message(message):
    """
    Отправляет сообщение в Telegram через HTTP (без внешних зависимостей).
    """
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message,
        }
    ).encode("utf-8")

    request = urllib.request.Request(url=url, data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return bool(payload.get("ok"))
    except Exception:
        return False


@shared_task
def send_habit_reminder(now=None):
    """
    Отправляет напоминания по расписанию и двигает `next_reminder_at`.
    """
    if now is None:
        now = timezone.now()

    window_end = now + timedelta(minutes=1)

    due_habits = Habit.objects.filter(
        next_reminder_at__isnull=False,
        next_reminder_at__gte=now,
        next_reminder_at__lt=window_end,
        is_pleasant=False,
    ).select_related("user", "related_habit")

    sent = 0

    for habit in due_habits:
        if habit.reward:
            reward_text = habit.reward
        elif habit.related_habit:
            reward_text = (
                f"Приятная привычка: {habit.related_habit.action} "
                f"({habit.related_habit.place})"
            )
        else:
            reward_text = "Отдых и чувство accomplishment!"

        message = (
            "Напоминание: пора выполнять привычку!\n\n"
            f"Пользователь: {habit.user.username}\n"
            f"Действие: {habit.action}\n"
            f"Место: {habit.place}\n"
            f"Время: {habit.time}\n"
            f"Вознаграждение: {reward_text}"
        )

        if send_telegram_message(message):
            habit.last_reminded_at = now
            habit.next_reminder_at = habit.next_reminder_at + timedelta(
                days=habit.periodicity
            )
            habit.save(
                update_fields=["last_reminded_at", "next_reminder_at", "updated_at"]
            )
            sent += 1

    return {"sent": sent, "total_due": due_habits.count()}
