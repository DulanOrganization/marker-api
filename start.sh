celery -A marker_api.celery_worker.celery_app worker --pool=solo --loglevel=info &

celery -A marker_api.celery_worker.celery_app flower --port=5555 &

python distributed_server.py --host 0.0.0.0 --port 8010