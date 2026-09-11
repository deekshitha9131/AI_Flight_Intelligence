import subprocess
import socket
import sys
import time
from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent
backend_dir = project_dir / "backend"

subprocess.run(
    ["docker", "compose", "up", "-d", "postgres"],
    cwd=project_dir,
    check=True,
)

deadline = time.time() + 60
while time.time() < deadline:
    try:
        with socket.create_connection(("127.0.0.1", 5433), timeout=2):
            break
    except OSError:
        time.sleep(2)
else:
    raise RuntimeError("PostgreSQL did not become available on port 5433 within 60 seconds")

subprocess.run(
    [sys.executable, "-m", "alembic", "upgrade", "head"],
    cwd=backend_dir,
    check=True,
)

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
    cwd=backend_dir,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
print(f"Server PID: {proc.pid}")
print("Server should be running now")
