from celery import Celery

app = Celery('music-clone', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

app.conf.update(
    result_expires=3600,
    worker_pool='solo',  # Add this line
)

app.autodiscover_tasks(['tasks'])
