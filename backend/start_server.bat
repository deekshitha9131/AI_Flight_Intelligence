@echo off
setlocal

set "BACKEND_DIR=%~dp0"
set "PROJECT_DIR=%BACKEND_DIR%.."

cd /d "%PROJECT_DIR%"
docker compose up -d postgres
if errorlevel 1 (
	echo Failed to start PostgreSQL. Make sure Docker Desktop is running.
	exit /b 1
)

cd /d "%BACKEND_DIR%"
python -c "import socket, time, sys; host, port = '127.0.0.1', 5433; deadline = time.time() + 60; ready = False; exec('while time.time() < deadline:\n    try:\n        with socket.create_connection((host, port), timeout=2):\n            ready = True\n            break\n    except OSError:\n        time.sleep(2)'); sys.exit(0 if ready else 1)"
if errorlevel 1 (
	echo PostgreSQL did not become available on port 5433 within 60 seconds.
	exit /b 1
)

python -m alembic upgrade head
if errorlevel 1 (
	echo Database migrations failed.
	exit /b 1
)

python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
