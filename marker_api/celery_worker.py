import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv(".env")

print("REDIS_HOST : ", os.environ.get("REDIS_HOST"))

# Celery app definition
celery_app = Celery(
    "celery_app",
    broker=os.environ.get("RABBITMQ_BROKER", "pyamqp://guest:guest@35.202.12.228:5672/"),
    backend=os.environ.get("REDIS_HOST", "redis://34.30.218.47:6379/0"),
    include=["marker_api.celery_tasks"],
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    result_expires=3600,
    broker_heartbeat=900,
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
)

# Celery configuration for task routing and worker behavior
celery_app.conf.update(
    worker_heartbeat_interval=900,
    worker_prefetch_multiplier=1,
    task_time_limit=3600,
    task_soft_time_limit=3500,
    task_routes={
        "marker_api.celery_tasks.convert_pdf_to_markdown": {"queue": "celery"},
        "marker_api.celery_tasks.send_to_process_continue_queue": {"queue": "process_continue_queue"},
    }
)

# Check Celery connection
try:
    celery_app.control.ping()
    print("✅ Celery is active and responding")
except Exception as e:
    print(f"❌ Celery is not active: {str(e)}")
