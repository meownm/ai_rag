# RAG Knowledge Platform (Local / Closed Test Contour)

## Purpose
Local knowledge platform with:
- document ingestion from folders and user uploads (PDF/DOCX/DOC/TXT)
- hybrid search (full-text + semantic)
- RAG answer generation with strict structured output
- interfaces: Telegram Bot, Telegram Mini App, Web
- access model: global admin, organizations, roles (org admin/editor/reader)
- infrastructure: Docker Desktop (Windows/WSL2), PostgreSQL + pgvector, MinIO

## Repo layout
- `infra/` — local infrastructure (Docker Compose, scripts, env templates)
- `docs/` — project documentation (requirements, decisions, architecture, pipeline trace, etc.)
- `services/` — application services (placeholders for next epics)
- `tgbot/` — Telegram bot (placeholder for later epics)
- `web/` — Web UI (placeholder for later epics)

## How to start (infrastructure only)
1. Copy `infra/.env.example` to `infra/.env` and adjust if needed.
2. Run `infra\install_infra.bat`
3. Run `infra\start_infra.bat`
4. Open:
   - PostgreSQL: `localhost:5432`
   - PGHero: `http://localhost:8081`
   - MinIO Console: `http://localhost:9001`

## Current status
This repository contains the baseline scaffolding:
- documentation set
- infrastructure compose + scripts
- env templates
- backlog and epic boundaries

Application services are intentionally placeholders until EPIC sequencing begins.
