from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Habit


class HabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = [
            "id",
            "user",
            "place",
            "time",
            "action",
            "is_pleasant",
            "related_habit",
            "periodicity",
            "reward",
            "execution_time",
            "is_public",
            "last_completed_at",
            "last_reminded_at",
            "next_reminder_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user",
            "last_completed_at",
            "last_reminded_at",
            "next_reminder_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        # Нельзя одновременно указывать связанную привычку и вознаграждение.
        if data.get("related_habit") and data.get("reward"):
            raise serializers.ValidationError(
                "Нельзя одновременно указывать связанную привычку и вознаграждение."
            )

        # Время выполнения должно быть не больше 120 секунд.
        execution_time = data.get("execution_time", 0)
        if execution_time > 120:
            raise serializers.ValidationError(
                "Время выполнения привычки не должно превышать 120 секунд."
            )

        # Связанная привычка должна быть приятной.
        related_habit = data.get("related_habit")
        if related_habit and not related_habit.is_pleasant:
            raise serializers.ValidationError(
                "Связанной привычкой может быть только приятная привычка."
            )

        # У приятной привычки не может быть вознаграждения или связанной привычки.
        is_pleasant = data.get("is_pleasant", False)
        if is_pleasant:
            if data.get("reward"):
                raise serializers.ValidationError(
                    "Приятная привычка не может иметь вознаграждение."
                )
            if data.get("related_habit"):
                raise serializers.ValidationError(
                    "Приятная привычка не может иметь связанную привычку."
                )

        # Периодичность не должна быть больше 7 дней.
        periodicity = data.get("periodicity", 1)
        if periodicity > 7:
            raise serializers.ValidationError(
                "Привычку нельзя выполнять реже, чем раз в 7 дней."
            )

        return data

    def create(self, validated_data):
        habit = Habit(**validated_data)
        try:
            habit.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict or exc.messages)
        habit.save()
        return habit

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict or exc.messages)

        instance.save()
        return instance
