# Arc Control Room Web

Next.js control-room surface for the NOC engineer demo path.

Current scope:
- Calls the backend contract endpoints: `GET /health`, `POST /api/demo/inject-fault`, `GET /api/stream`, `POST /api/validation`, and `POST /api/demo/reset`.
- Decodes `push_sent` SSE events into the same incident payload shape used by iOS.
- Submits demo validation payloads with the backend `validation_event` contract shape.

Run:

```sh
cd frontend
npm install
npm run dev
```

Default backend URL:

```sh
http://127.0.0.1:8000
```

Override at build/dev time:

```sh
NEXT_PUBLIC_ARC_BACKEND_URL=http://192.168.10.223:8000 npm run dev
```
