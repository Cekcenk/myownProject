from celery import current_app
import logging

logger = logging.getLogger(__name__)

def route_task(name, args, kwargs, options, task=None, **kw):
    chain_id = kwargs.get('chain_id') or options.get('chain_id')
    logger.debug(f"Routing task: {name}")
    logger.debug(f"Chain ID: {chain_id}")
    if chain_id:
        queue = f'chain_{chain_id}'
        logger.debug(f'Routing task {name} to queue: {queue}')
        return {'queue': queue}
    logger.debug(f'Routing task {name} to default queue: celery')
    return {'queue': 'celery'}

current_app.conf.task_routes = (route_task,)