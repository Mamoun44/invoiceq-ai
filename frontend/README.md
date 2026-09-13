# InvoiceQ AI frontend

Angular chat widget adapted from the `frontend` directory of
https://github.com/aozahran05/RAG-full-stack.

## Request flow

```text
Angular :4200 -> Spring Boot :8080 -> Python/FastAPI :8001 -> Gemini File Search
```

The Angular development proxy forwards `/api/*` to Spring Boot and removes the
`/api` prefix. The chat sends the selected invoice, its captured InvoiceQ error,
and the user's question to Spring's `/test-ai/explain/stream` endpoint. It reads
the `status`, `token`, `done`, and `error` SSE events progressively.

## Run locally

Start the Python service on port 8001 and Spring Boot on port 8080. Then:

```bash
npm install
npm start
```

Open http://localhost:4200.

In the real InvoiceQ dashboard, replace the demo value in `app.ts` with the
selected invoice payload and the error response captured from InvoiceQ.
