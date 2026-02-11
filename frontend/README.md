# Corporate RAG Frontend

Production frontend for corporate-rag-service with React + Vite + TypeScript + TanStack Query + Zod + Tailwind.

## Environment

- `VITE_API_BASE_URL` (required): backend base URL.
- `VITE_UI_MODE` (optional): `prod` or `debug`.

## Features

- Query workspace with structured refusal handling.
- Citation and source panels.
- Role-gated scoring trace and performance panels.
- Ingestion admin workflow with job polling.
- Diagnostics page with health + reserved cards for unsupported endpoints.
- Windows scripts and Docker Desktop deployment path.

## Development

```bash
npm install
npm run dev
npm run test
npm run build
```
