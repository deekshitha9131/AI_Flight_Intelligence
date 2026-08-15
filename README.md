# AI Flight Intelligence

AI Flight Intelligence is a full-stack travel assistant platform that combines flight search, personalization, and AI-powered recommendations in a single experience. The application helps users explore flight options, save favorites, receive trip suggestions, and interact with an assistant for travel-related questions.

## What the platform does

- Search and browse flight offers through a modern frontend experience
- Persist and manage user favorites
- Deliver AI-driven predictions and recommendations
- Support authenticated user flows for profile and preferences
- Provide a conversational assistant experience for travel help

## Project structure

- backend: FastAPI application, authentication, API routes, and service layer
- frontend: React + TypeScript + Vite interface for the end-user experience
- ml: training, preprocessing, evaluation, and prediction-related modules
- docs: product requirements, API references, and architecture notes

## Tech stack

- Backend: FastAPI, SQLAlchemy, Pydantic, JWT auth
- Frontend: React, TypeScript, Vite, TanStack Query, Zustand
- Data/AI: Python-based ML pipeline and prediction helpers
- Infrastructure: Docker Compose with PostgreSQL and Redis

## Run the application

### Option 1: Docker Compose (recommended)

1. Make sure Docker Desktop is running.
2. From the project root, start the full stack:

```bash
docker compose up --build
```

3. Open the following URLs after the containers are healthy:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

4. To stop the services later, run:

```bash
docker compose down
```

### Option 2: Run locally

#### 1. Start the database and Redis services

If you are not using Docker, make sure PostgreSQL and Redis are available and reachable from your backend configuration.

#### 2. Start the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Verify the backend is up by opening:
- http://localhost:8000/docs
- http://localhost:8000/health (if available in your environment)

#### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 to view the app.

## Things to verify

After the app starts, confirm the following:

- The frontend loads without a blank screen or console errors.
- The backend health endpoint or Swagger docs load correctly.
- User registration and login work end to end.
- The search page returns results or an expected empty state.
- Favorites can be added and removed.
- Recommendations and assistant features respond without runtime errors.
- Profile updates save and persist correctly.
- API requests from the frontend reach the backend successfully.

## Environment notes

The backend expects database and auth-related environment settings to be available. If you are running services locally, make sure your configuration points to a reachable PostgreSQL instance and the expected secret values.

## Testing

Frontend tests:

```bash
cd frontend
npm test -- --run
```

Backend tests:

```bash
cd backend
pytest
```

## Notes

This repository is organized as a multi-layer application with separate frontend, backend, and machine learning components. It is designed to be extended with additional travel features, deeper personalization, and richer AI workflows over time.
