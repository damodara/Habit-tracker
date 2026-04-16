from datetime import datetime, timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.pagination import HabitPagination

from .models import Habit
from .serializers import HabitSerializer


class HabitListCreateView(generics.ListCreateAPIView):
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Каждый пользователь видит только свои привычки
        return Habit.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class HabitDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = HabitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user)


class PublicHabitListView(generics.ListAPIView):
    serializer_class = HabitSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = HabitPagination

    def get_queryset(self):
        return Habit.objects.filter(is_public=True).order_by("-id")


class HabitCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        habit = get_object_or_404(Habit, pk=pk, user=request.user)
        now = timezone.now()

        try:
            habit.validate_completion(now=now)
        except DjangoValidationError as exc:
            return Response(
                {"detail": exc.messages},
                status=status.HTTP_400_BAD_REQUEST,
            )

        local_now = timezone.localtime(now)
        next_date = local_now.date() + timedelta(days=habit.periodicity)
        next_dt = datetime.combine(next_date, habit.time)
        next_dt = timezone.make_aware(next_dt, timezone.get_current_timezone())

        habit.last_completed_at = now
        habit.next_reminder_at = next_dt
        habit.save(
            update_fields=["last_completed_at", "next_reminder_at", "updated_at"]
        )

        return Response(
            {
                "detail": "Habit completed.",
                "last_completed_at": habit.last_completed_at,
                "next_reminder_at": habit.next_reminder_at,
            },
            status=status.HTTP_200_OK,
        )
