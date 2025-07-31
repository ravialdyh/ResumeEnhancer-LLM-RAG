from celery import Celery

celery_app = Celery('workers', broker='redis://redis:6379/0', backend='redis://redis:6379/0', include=['api.main'])