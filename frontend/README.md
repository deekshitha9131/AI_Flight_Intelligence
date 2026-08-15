# AI Flight frontend

React 18 + TypeScript single-page application for the FastAPI API.

## Start

`npm.cmd install` then `npm.cmd run dev` from `frontend/`. Set `VITE_API_URL`
to the backend origin (default `http://127.0.0.1:8000`).

The API client attaches JWT access tokens, refreshes them once after a 401, and
clears the persisted session if refresh fails. Routes for searches, predictions,
recommendations, assistant, and dashboard are protected.
