# Infrastructure (Local / Docker Desktop)

## What is included
- PostgreSQL (with pgvector enabled)
- PGHero
- MinIO (S3 + console)

## Files
- `docker-compose.yml`
- `.env.example`
- scripts:
  - `install_infra.bat`
  - `start_infra.bat`
  - `stop_infra.bat`
  - `reset_infra.bat`

## Usage
1. Copy `.env.example` -> `.env`
2. Run `install_infra.bat`
3. Run `start_infra.bat`
