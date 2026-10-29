# LLM Powered Smart Greenhouse Assistant — Frontend

A single-page dashboard for greenhouse sensor monitoring, plant-specific AI assessments and saved recommendations, and an AI chat assistant.

Built with React, JavaScript, CSS, Recharts, and Vite.

## Requirements

- Node.js 20.19+ within the 20.x release line, or Node.js 22.12+.
- npm.

## Setup and development

Run from the `frontend/` directory:

```sh
npm ci
cp .env.example .env
npm run dev
```

Create `.env` from the example if it does not already exist. Set `VITE_API_BASE_URL` to the backend root URL **without `/api`**:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

The API client appends `/api`. Restart the development server after changing environment variables. Backend startup instructions are in the [backend README](../backend/SmartGreenHouse/README.md).

## Build and test

```sh
npm run build                       # Output: dist/
npm run preview                     # Preview the production build
node --test tests/*.test.js          # Chat and JWT client tests
```

## Sign in and data access

Use an existing backend account. The UI includes login and logout, not registration or device selection. The dashboard assumes one device and retains backend per-user ownership restrictions. A newly registered user without an owned device sees no readings.

JWT access and refresh tokens are kept in tab session storage. The client refreshes expired access tokens once, and returns to login when authorization fails. Passwords are not stored. Plant choices are retained per user on reload and cleared on logout.

Initial load and Refresh data obtain a new current snapshot; changing plants refreshes AI assessments; changing week/month refreshes historical charts and saved analysis only. No polling is used. API/model failures display explicitly labeled demo content where applicable; authentication failures do not. Successful empty data remains empty, and real readings never receive fabricated status labels.

Configure MongoDB and Ollama, then run backend migrations and `seed_plants` before using the dashboard. See the backend README. English-only API contracts and snapshot behavior are described in the API reference.

## Source layout

- `src/components/`: plant selector, sensor cards, history charts, alerts, recommendations, and chat.
- `src/pages/Login.jsx`: sign-in form.
- `src/pages/Dashboard.jsx`: dashboard layout, plant selection and snapshot request coordination.
- `src/services/api.js`: backend requests and response validation.
- `src/data/mockData.js`: sensor, plant, alert, and recommendation fixtures.
- `src/index.css`: shared styling and responsive layout.

## Features and data sources

| Feature | Current behavior |
| --- | --- |
| Plant selection | Searches the backend English catalogue; caches successful results for five minutes. |
| Current status | Latest backend reading; transient plant-specific LLM labels are requested separately. |
| Historical charts | 28 six-hour buckets for 1 Week; 30 24-hour buckets for 1 Month, with average/min/max details. |
| Alerts and recommendations | One backend request analyzes the selected plant and period, validates JSON, and saves its input/output snapshot. |
| Chat | Uses `POST /api/llm/chat/`; supports loading, retry, and timeout states. |

Chat is independent of plant selection. Questions are limited to 2,000 characters. The latest 30 exchanges are kept in page memory and cleared on reload. The backend receives each question separately, without previous messages. All interactions and plant records are English-only.

