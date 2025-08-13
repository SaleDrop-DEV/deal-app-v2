import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deal_app_project.settings')

app = Celery('deal_app_project') # Replace 'deal_app_project' with your actual project name

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix in your settings.py.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Discover tasks in all installed apps.
# Celery will look for a `tasks.py` file in each app listed in INSTALLED_APPS.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
