import os

from celery import Celery

# Ensure Django settings are loaded for Celery worker.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

# Load Celery configuration from Django settings using CELERY_* namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Automatically discover tasks.py from installed apps.
app.autodiscover_tasks()
