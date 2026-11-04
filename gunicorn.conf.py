import os

bind = "0.0.0.0:" + os.getenv("PORT", "8000")
workers = int(os.getenv("WEB_CONCURRENCY", "3"))
timeout = 60
accesslog = "-"
errorlog = "-"
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1")
