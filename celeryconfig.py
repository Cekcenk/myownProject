from celery import Celery
from kombu import Exchange, Queue

# Redis configuration
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/1'

app = Celery('music-clone', broker=broker_url, backend=result_backend)

# Define exchange and queue
chain_exchange = Exchange('chain_exchange', type='direct')
chain_queue = Queue('chain_queue', chain_exchange, routing_key='chain')

app.conf.task_queues = (chain_queue,)

# Update task routes
app.conf.task_routes = {
    '*': {'queue': 'chain_queue', 'routing_key': 'chain'},
}

# Celery configuration
app.conf.update(
    task_default_queue='chain_queue',
    task_default_exchange='chain_exchange',
    task_default_routing_key='chain',
    result_expires=3600,
    worker_pool='solo',
    worker_concurrency=1,
    task_queue_max_priority=10,
    task_default_priority=5,
    worker_max_tasks_per_child=1,  # Process one task per child for better isolation
    broker_connection_timeout=30,
    broker_heartbeat=10,
    broker_pool_limit=1,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_time_limit=3600,
    task_soft_time_limit=3540,
    task_track_started=True,
    task_always_eager=False,
    broker_connection_retry_on_startup=True,
    task_create_missing_queues=True,
    broker_connection_max_retries=None,
    worker_cancel_long_running_tasks_on_connection_loss=True,
    result_persistent=True,
    broker_transport_options={'visibility_timeout': 3600},
    result_backend_transport_options={'visibility_timeout': 3600},
)

app.autodiscover_tasks(['tasks'])

class MyTask(app.Task):
    def __call__(self, *args, **kwargs):
        return self.run(*args, **kwargs)

app.Task = MyTask