import os
from celery import Celery
from dotenv import load_dotenv
# import multiprocessing

# multiprocessing.set_start_method("spawn")

load_dotenv(".env")

print("REDIS_HOST : ", os.environ.get("REDIS_HOST"))

celery_app = Celery(
    "celery_app",
    broker=os.environ.get("RABBITMQ_BROKER", "pyamqp://guest:guest@35.202.12.228:5672/"),
    # broker=os.environ.get("REDIS_HOST", "redis://34.30.218.47:6379/0"),
    backend=os.environ.get("REDIS_HOST", "redis://34.30.218.47:6379/0"),
    include=["marker_api.celery_tasks"],
    worker_cancel_long_running_tasks_on_connection_loss=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],  # Restrict to JSON for safety
    result_expires=3600,
)

# Check if Celery is active
try:
    celery_app.conf.update(
        broker_connection_retry_on_startup=True
    )
    celery_app.control.ping()
    print("Celery is active and responding")
except Exception as e:
    print(f"Celery is not active: {str(e)}")
