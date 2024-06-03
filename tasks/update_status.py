from celery import shared_task
from task_status import task_status

@shared_task(bind=True)
def update_status(self, status, task_id=None):
    self.request.id = task_id
    task_status[task_id] = status
