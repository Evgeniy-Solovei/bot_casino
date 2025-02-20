import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bot_core.settings')

app = Celery('bot_core')
app.config_from_object('bot_core.conf:settings', namespace='CELERY')
app.conf.update(task_acks_late=True, task_reject_on_worker_lost=True)
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
