# Weather-aware Routing — Runtime Source

React + TypeScript + Tailwind frontend with a Django REST API for weather-aware route comparisons, arrival checkpoint forecasts, and a 0–48-hour corridor heatmap.

## Requirements

Python 3.12+ (verified with 3.14), Node.js 22.12+, and npm. Live mode needs Mapbox and Geoapify credentials. The current Open-Meteo evaluation integration needs no key.

## Start the backend

Run from the extracted project directory:

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
```

On Windows, activate with `.venv\Scripts\activate`. The included `backend/.env` retains your local configuration. If you need to recreate it, copy `.env.example` to `.env` and set `MAPBOX_ACCESS_TOKEN` and `GEOAPIFY_API_KEY`. Then run:

```sh
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Local API docs: http://127.0.0.1:8000/api/v1/docs/.

## Start the frontend

In another terminal, from the extracted project directory:

```sh
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173. Vite forwards `/api` requests to Django on port 8000. The default local setup does not need a frontend `.env`; provider secrets belong only on the backend. Demo mode works without Django or provider keys, with a schematic fallback if basemap tiles are unavailable.

To compile the frontend, run `npm run build` inside `frontend/`. A production host must provide an API proxy or configure `VITE_API_BASE_URL`, along with backend CORS and a production application server.

## Using the app

Select both locations from search suggestions, enter departure in the origin's time zone, choose load and checkpoint spacing, and compare. Select a route or checkpoint to inspect arrival weather. The forecast slider updates the corridor heatmap independently of arrival-based route risk. Switching Live/Demo preserves each mode's state until page reload. Expired forecasts need refreshing.

## Archive contents

This package contains application source, dependency manifests and lock files, configuration templates, and this setup guide. Screenshots and the current private environment files are included. Tests, developer documentation, dependencies, build output, caches, package metadata, local databases, and Git history are intentionally excluded. Test commands in package metadata apply to the full development repository.

Edit `frontend/src/styles/theme.css` to customize colors and fonts. See `backend/.env.example` for configurable resource limits. The local cache is process-local; shared caching and hosting configuration are needed for a multi-worker production release. Mapbox's driving profile is not a complete commercial-truck restriction profile.
