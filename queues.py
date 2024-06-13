# queues.py

from rq import Queue
from redis import Redis

redis_conn = Redis()
crawl_queue = Queue('crawl_queue', connection=redis_conn)
scrape_queue = Queue('scrape_queue', connection=redis_conn)

