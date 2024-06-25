from celery import Celery

app = Celery('music-clone', broker='redis://localhost:6379/0', backend='rpc://')

app.conf.update(
    result_expires=3600,
    worker_pool='solo',
    # worker_concurrency=2,  # Limit to 2 concurrent tasks
)

app.autodiscover_tasks(['tasks'])
