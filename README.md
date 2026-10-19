# LLM Powered Smart Greenhouse Assistant — Frontend

A single-page dashboard for greenhouse sensor monitoring, plant-specific demo alerts and recommendations, and an AI chat assistant.

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
node --test tests/api-chat.test.js   # Chat API client tests
```

## Source layout

- `src/components/`: plant selector, sensor cards, history charts, alerts, recommendations, and chat.
- `src/pages/Dashboard.jsx`: dashboard layout and selected plant state.
- `src/services/api.js`: backend requests and response validation.
- `src/data/mockData.js`: sensor, plant, alert, and recommendation fixtures.
- `src/index.css`: shared styling and responsive layout.

## Features and data sources

| Feature | Current behavior |
| --- | --- |
| Plant selection | Searches local example plants; selection filters alerts and recommendations. |
| Current status | Four sensor cards using mock readings and status labels. |
| Historical charts | Requests 7-day or 30-day sensor history; uses labeled demo data if unavailable. |
| Alerts and recommendations | Plant-specific mock data; plant analysis endpoints are pending. |
| Chat | Uses `POST /api/llm/chat/`; supports loading, retry, and timeout states. |

Chat is independent of plant selection. Questions are limited to 2,000 characters. The latest 30 exchanges are kept in page memory and cleared on reload. The backend receives each question separately, without previous messages. Requests currently use English because the backend's Chinese language mapping is incorrect.

