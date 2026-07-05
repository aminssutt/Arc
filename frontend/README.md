# Arc Control Room Web

Next.js control-room surface for the NOC engineer demo path.

## Capabilities

- Streams the live incident lifecycle from `GET /api/stream`.
- Triggers deterministic confirm and pivot scenarios.
- Shows the site/factory fault location in Simple mode.
- Shows multi-agent orchestration, responder matching, and mobile validation in Technical mode.
- Submits field validation and produces a cited intervention report.

## Run

Start the backend from the repository root:

```sh
python -m uvicorn backend.app.main:app --port 8000
```

Then start the frontend:

```sh
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

The frontend runs at `http://localhost:3000` and uses `http://127.0.0.1:8000`
by default. Override the API URL with `NEXT_PUBLIC_ARC_BACKEND_URL`.

## Structure

```text
src/app/          application routes
src/components/   control-room and landing components
src/lib/          backend contracts, event reducer, reports, session
src/motion/       shared motion primitives and tokens
```
