# Luxe Commerce — Backend (FastAPI)

FastAPI + PostgreSQL 16 + Redis 7. Clean Architecture, feature-based.

## Quick start
```bash
cp .env.example .env
docker compose up --build
```
- Health: http://localhost:8000/health
- Swagger UI: http://localhost:8000/docs
- OpenAPI: http://localhost:8000/openapi.json

## Migrations
```bash
alembic upgrade head           # apply
alembic revision -m "msg"      # new migration (autogenerate once models land)
alembic downgrade -1           # roll back one
```
The baseline `0001_initial` applies the canonical `../db/schema.sql`.

## Structure
See [`../docs/FOLDER_STRUCTURE_BACKEND.md`](../docs/FOLDER_STRUCTURE_BACKEND.md).

## Status
**Phase 1 (backend) COMPLETE.** 15 feature modules, ~86 endpoints, RBAC, JWT (rotation +
reuse detection), pricing engine, idempotent checkout, payments with signed webhooks,
CMS, notifications, delivery, analytics/audit. All compile-clean; pricing/lifecycle/
signature logic unit-tested; schema + critical SQL validated on live PostgreSQL 16.

Run `docker compose up --build` then open `/docs` for the full interactive API.
Next: Phase 2 (admin panel UI), Phase 3 (Flutter app), then testing + deployment.
