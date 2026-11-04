import os
import subprocess
import sys

for command in [["migrate", "--noinput"], ["createcachetable"], ["collectstatic", "--noinput"]]:
    subprocess.run([sys.executable, "manage.py", *command], check=True)
if os.getenv("SEED_DEMO") == "1":
    subprocess.run([sys.executable, "manage.py", "seed_demo"], check=True)
os.execvp("gunicorn", ["gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"])
