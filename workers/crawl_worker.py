# worker.py

import os
from redis import Redis
from rq import Worker, Queue, Connection

listen = ['crawl_queue']

if __name__ == '__main__':
    redis_conn = Redis(os.environ.get('REDIS_HOST', 'localhost'), os.environ.get('REDIS_PORT', 6379))

    with Connection(connection=redis_conn):
        worker = Worker(map(Queue, listen))
        worker.work()

