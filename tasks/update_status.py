from celery import shared_task
from task_status import task_status

@shared_task
def update_status(*args, task_id, status):
    task_status[task_id] = status
    print(f"Updating status to {status} for task ID {task_id}")
