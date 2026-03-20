from django.urls import path
from . import views
from .auth_views import LoginView, RegisterView

app_name = 'habits'

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('habits/', views.HabitListCreateView.as_view(), name='habit-list-create'),
    path('habits/<int:pk>/', views.HabitDetailView.as_view(), name='habit-detail'),
    path('habits/public/', views.PublicHabitListView.as_view(), name='public-habit-list'),
    path('habits/<int:pk>/complete/', views.HabitCompleteView.as_view(), name='habit-complete'),
]
