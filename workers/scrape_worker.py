# import os
# from redis import Redis
# from rq import Worker, Queue, Connection

# listen = ['scrape_queue']

# def clear_queue(queue):
#     with Connection(connection=redis_conn):
#         jobs = queue.jobs
#         for job in jobs:
#             job.cancel()

# if __name__ == '__main__':
#     redis_conn = Redis(os.environ.get('REDIS_HOST', 'localhost'), os.environ.get('REDIS_PORT', 6379))
#     scrape_queue = Queue('scrape_queue', connection=redis_conn)

#     # Clear the scrape_queue before starting the worker
#     clear_queue(scrape_queue)

#     with Connection(connection=redis_conn):
#         worker = Worker(map(Queue, listen))
#         worker.work()
import os
from redis import Redis
from rq import Worker, Queue, Connection

listen = ['scrape_queue']

if __name__ == '__main__':
    redis_conn = Redis(os.environ.get('REDIS_HOST', 'localhost'), os.environ.get('REDIS_PORT', 6379))

    # Clear the scrape queue
    scrape_queue = Queue('scrape_queue', connection=redis_conn)
    scrape_queue.empty()

    with Connection(connection=redis_conn):
        worker = Worker(map(Queue, listen))
        worker.work()
        
# worker.py

# import os
# from redis import Redis
# from rq import Worker, Queue, Connection

# listen = ['scrape_queue']

# if __name__ == '__main__':
#     redis_conn = Redis(os.environ.get('REDIS_HOST', 'localhost'), os.environ.get('REDIS_PORT', 6379))

#     with Connection(connection=redis_conn):
#         worker = Worker(map(Queue, listen))
#         worker.work()
