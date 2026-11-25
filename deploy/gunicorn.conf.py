import os

bind = "127.0.0.1:8000"
workers = int(os.getenv("WEB_CONCURRENCY", "2"))
worker_class = "gthread"
threads = 8
timeout = 30
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
capture_output = True
max_requests = 2000
max_requests_jitter = 200
