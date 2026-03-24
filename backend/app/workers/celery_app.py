from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.task_routes = {
    "app.workers.tasks.mail_fetch_task": "mail_queue",
    "app.workers.tasks.receipt_parse_task": "parsing_queue",
    "app.workers.tasks.subscriptions_matcher_task": "parsing_queue",
    "app.workers.tasks.periodic_mail_sync": "mail_queue",
    "app.workers.tasks.firebase_notifier_task": "mail_queue"
}

# Define periodic tasks for Celery Beat Scheduler
celery_app.conf.beat_schedule = {
    "periodic-mail-sync-every-6-hours": {
        "task": "app.workers.tasks.periodic_mail_sync",
        "schedule": crontab(minute=0, hour='*/6'),
    },
    "firebase-daily-reminders": {
        "task": "app.workers.tasks.firebase_notifier_task",
        "schedule": crontab(minute=0, hour=9), # daily at 9am
    }
}
