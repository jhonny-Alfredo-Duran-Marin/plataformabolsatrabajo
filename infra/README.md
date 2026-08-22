# Infraestructura — EGRESA

## 1. Desarrollo local con Docker Compose

```bash
cd infra/docker
cp .env.example .env
docker compose up --build
```

- Backend (FastAPI): http://localhost:8000/api/health
- Frontend (Angular): http://localhost
- PostgreSQL: localhost:5432

## 2. Producción

Ver `docker-compose.prod.yml` y `nginx/reverse-proxy.conf`. Despliegue en Google Cloud Platform: `gcp/deploy.sh` (pendiente).

## 3. Scripts

- `scripts/backup-db.sh` / `scripts/restore-db.sh`: respaldo y restauración de la base de datos.
- `scripts/logs.sh`: acceso rápido a los logs de los contenedores.
