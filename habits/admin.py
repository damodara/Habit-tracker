
from django.contrib import admin
from .models import Habit

@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'periodicity', 'is_public', 'created_at')