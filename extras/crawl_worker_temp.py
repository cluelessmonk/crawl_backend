import os
from redis import Redis
from rq import Worker, Queue, Connection
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models import JobInstance  # Adjust the import according to your project structure

# Define the Redis connection
listen = ['crawl_queue']
redis_conn = Redis(os.environ.get('REDIS_HOST', 'localhost'), os.environ.get('REDIS_PORT', 6379))

# Define the database connection
DATABASE_URL = "sqlite:///crawlx.db"  # Adjust this path
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def update_job_status_success(job, connection, result, *args, **kwargs):
    """Callback function to update job instance status to COMPLETED."""
    session = Session()
    try:
        job_instance = session.query(JobInstance).filter_by(instance_id=job.meta.get('instance_id')).first()
        if job_instance:
            job_instance.status = "COMPLETED"
            job_instance.end_time = func.now()
            session.commit()
    except Exception as e:
        print(f"Error updating job instance status: {e}")
    finally:
        session.close()

def handle_job_failure(job, connection, type, value, traceback):
    """Callback function to update job instance status to FAILED on job failure."""
    session = Session()
    try:
        job_instance = session.query(JobInstance).filter_by(instance_id=job.meta.get('instance_id')).first()
        if job_instance:
            job_instance.status = "FAILED"
            job_instance.end_time = func.now()
            session.commit()
    except Exception as e:
        print(f"Error updating job instance status: {e}")
    finally:
        session.close()

if __name__ == '__main__':
    with Connection(connection=redis_conn):
        worker = Worker(map(Queue, listen))

        # Register event handlers
        worker.push_exc_handler(handle_job_failure)

        def success_handler(job, connection, result, *args, **kwargs):
            update_job_status_success(job, connection, result, *args, **kwargs)

        # Attach the success handler to the worker
        worker.on_success = success_handler

        worker.work()
