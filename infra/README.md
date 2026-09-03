# Infraestructura — EGRESA

## 1. Desarrollo local con Docker Compose

```bash
cd infra/docker
cp .env.example .env
```

Editá `infra/docker/.env` y agregá `DATABASE_URL=` con el mismo valor que tenés en `backend/.env`, así el backend usa la Supabase compartida del equipo (con todos los datos ya cargados) en vez de crear un Postgres local vacío. Si dejás esa línea sin poner, usa el Postgres local por defecto.

```bash
docker compose up -d --build
```

- Backend (FastAPI): http://localhost:8000/api/health
- Frontend (Angular): http://localhost
- PostgreSQL local (solo si no configuraste `DATABASE_URL`): localhost:5433

Los contenedores quedan nombrados `egresa-backend-1`, `egresa-db-1`, `egresa-frontend-1` (nombre de proyecto fijado en `docker-compose.yml`).

Para pararlo: `docker compose down`. Para ver logs: `docker compose logs -f`. Las próximas veces, sin reconstruir imágenes: `docker compose up -d`.

## 2. Producción

Ver `docker-compose.prod.yml` y `nginx/reverse-proxy.conf`. Despliegue en Google Cloud Platform: `gcp/deploy.sh` (pendiente).

## 3. Scripts

- `scripts/backup-db.sh` / `scripts/restore-db.sh`: respaldo y restauración de la base de datos.
- `scripts/logs.sh`: acceso rápido a los logs de los contenedores.
