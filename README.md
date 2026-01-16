# MIPH Shop Backend

Scaffolded per `fastapi_shop_spec_final.md`.

## Structure
- `apps/public_api/` - public FastAPI app (`/api/v1`)
- `apps/admin_api/` - admin FastAPI app (`/admin/v1`)
- `core/` - shared config, db, auth, models, schemas, services
- `alembic/` - migrations
- `docker/` - Dockerfiles and nginx config

This repo currently contains the base file layout only.

## Setup
- Create `.env` from `.env.example` (see spec for required variables).
- Install deps: `pip install -r requirements.txt`
- Run Alembic migrations: `alembic upgrade head`
- Start services: `docker compose up --build`
