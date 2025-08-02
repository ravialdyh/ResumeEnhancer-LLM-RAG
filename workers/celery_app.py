import os
from celery import Celery

broker_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
backend_url = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')

celery_app = Celery('workers',
                    broker=broker_url,
                    backend=backend_url,
                    include=['api.tasks'])