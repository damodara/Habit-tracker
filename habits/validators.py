from datetime import timedelta

from django.core.exceptions import ValidationError


MAX_INACTIVITY_DAYS = 7
MAX_EXECUTION_TIME_SECONDS = 120


def validate_reward_and_related_habit(habit):
    """
    Нельзя одновременно указывать вознаграждение и связанную привычку.
    """
    if habit.reward and habit.related_habit:
        raise ValidationError("Нельзя одновременно указывать связанную привычку и вознаграждение.")


def validate_execution_time(habit):
    """
    Время выполнения должно быть не больше 120 секунд.

    Django field validators получают именно значение поля.
    """
    if habit > MAX_EXECUTION_TIME_SECONDS:
        raise ValidationError("Время выполнения привычки не должно превышать 120 секунд.")


def validate_pleasant_habit_properties(habit):
    """
    У приятной привычки не может быть вознаграждения или связанной привычки.
    """
    if habit.is_pleasant and (habit.reward or habit.related_habit):
        raise ValidationError("Приятная привычка не может иметь вознаграждение или связанную привычку.")


def validate_related_habit_is_pleasant(habit):
    """
    В связанные привычки могут попадать только привычки с признаком приятной.
    """
    if habit.related_habit and not habit.related_habit.is_pleasant:
        raise ValidationError("Связанной привычкой может быть только приятная привычка.")


def validate_related_habit_belongs_to_user(habit):
    """
    Связанная привычка должна принадлежать тому же пользователю.
    """
    if habit.related_habit and habit.user_id and habit.related_habit.user_id != habit.user_id:
        raise ValidationError("Связанная привычка должна принадлежать текущему пользователю.")


def validate_periodicity(habit):
    """
    Нельзя выполнять привычку реже, чем 1 раз в 7 дней.

    Django field validators получают именно значение поля.
    """
    if habit > MAX_INACTIVITY_DAYS:
        raise ValidationError("Привычку нельзя выполнять реже, чем раз в 7 дней.")


def validate_habit_completion_gap(habit, last_completed_at, now):
    """
    Нельзя не выполнять привычку более 7 дней.
    """
    if last_completed_at is None:
        return

    if now - last_completed_at > timedelta(days=MAX_INACTIVITY_DAYS):
        raise ValidationError("Нельзя не выполнять привычку более 7 дней.")
