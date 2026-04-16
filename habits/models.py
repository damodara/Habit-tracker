from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .validators import (
    validate_execution_time,
    validate_habit_completion_gap,
    validate_periodicity,
    validate_pleasant_habit_properties,
    validate_related_habit_belongs_to_user,
    validate_related_habit_is_pleasant,
    validate_reward_and_related_habit,
)


class Habit(models.Model):  # noqa: E302
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="habits")
    place = models.CharField(max_length=255)
    time = models.TimeField()
    action = models.CharField(max_length=255)
    is_pleasant = models.BooleanField(default=False)
    related_habit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_habits",
    )
    periodicity = models.PositiveIntegerField(
        default=1, validators=[validate_periodicity]
    )  # days
    reward = models.CharField(max_length=255, blank=True)
    execution_time = models.PositiveIntegerField(
        validators=[validate_execution_time]
    )  # seconds
    is_public = models.BooleanField(default=False)
    last_completed_at = models.DateTimeField(null=True, blank=True)
    last_reminded_at = models.DateTimeField(null=True, blank=True)
    next_reminder_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.action} at {self.time} in {self.place}"

    def calculate_first_next_reminder_at(self):
        """
        Первый напоминатель: ближайшее наступление `time` (с учетом текущей даты).
        """
        now = timezone.localtime(timezone.now())
        today_at = datetime.combine(now.date(), self.time)
        today_at = timezone.make_aware(today_at, timezone.get_current_timezone())

        if today_at <= now:
            today_at += timedelta(days=1)
        return today_at

    def save(self, *args, **kwargs):
        # Pleasant habit не требует напоминаний.
        if self.next_reminder_at is None and not self.is_pleasant:
            self.next_reminder_at = self.calculate_first_next_reminder_at()
        super().save(*args, **kwargs)

    def clean(self):
        validate_reward_and_related_habit(self)
        validate_pleasant_habit_properties(self)
        validate_related_habit_is_pleasant(self)
        validate_related_habit_belongs_to_user(self)

    def validate_completion(self, now=None):
        if now is None:
            now = timezone.now()
        validate_habit_completion_gap(self, self.last_completed_at, now)

    class Meta:
        verbose_name = "Habit"
        verbose_name_plural = "Habits"
