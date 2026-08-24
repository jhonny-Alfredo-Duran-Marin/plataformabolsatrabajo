# EGRESA

Plataforma de Reclutamiento y Bolsa de Trabajo para la Vinculación entre Empresas y Egresados Universitarios — Universidad Autónoma Gabriel René Moreno (UAGRM).

- **Backend:** FastAPI · Python 3.13 · PostgreSQL · SQLAlchemy · Alembic · JWT (monolito)
- **Frontend Web:** Angular (standalone components)
- **Móvil:** Flutter (Android · iOS)
- **Infra:** Docker · GCP · ver [infra/](infra/)

Este repositorio contiene únicamente el **esqueleto de la solución** (carpetas y archivos base) definido en el perfil de proyecto. Cada integrante del equipo implementa sus historias de usuario en su propia rama `feature/<nombre>` a partir de esta estructura.

## Estructura del monorepo

```
backend/    API monolítica FastAPI, organizada por módulo de negocio en
            app/features/<modulo>/ (router, service, repository, schema).
            Ver backend/ARCHITECTURE.md para el detalle.
frontend/   Aplicación web Angular (core, shared, features/<módulo>)
mobile/     Aplicación móvil Flutter (core, features/<módulo>)
infra/      Docker Compose, Nginx, scripts de despliegue y respaldo
```

## Requisitos

| Herramienta | Versión |
|---|---|
| Python | 3.13+ |
| Node.js | 20+ |
| PostgreSQL | 16 |
| Flutter | 3.11+ (opcional, solo móvil) |
| Docker Desktop | 24+ (opcional, alternativa al setup nativo) |

## Setup local

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements-dev.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Documentación interactiva: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm start
```

Abre 👉 http://localhost:4200

### Móvil

```bash
cd mobile
flutter pub get
flutter run
```

### Todo junto con Docker Compose

Ver [infra/README.md](infra/README.md).

## Documentación del proyecto

Ver [ROADMAP.md](ROADMAP.md) para los módulos del alcance y la planificación de sprints, y [backend/ARCHITECTURE.md](backend/ARCHITECTURE.md) para cómo está organizado el código del backend y cómo se conectan sus capas.

## Equipo

| Rol | Integrante |
|---|---|
| Product Owner | Bravo Vieira Antonio |
| Scrum Master | Duran Marin Jhonny Alfredo |
| Development Team | Nils Jonathan Jimenez Duarte |
| Development Team | Quispe Tito Jorge Gabriel |
| Development Team | Valencia Amezaga Andre |
| Development Team | Moya Bustamante Manuel |

## Base de datos y usuarios de acceso

El backend se conecta a PostgreSQL en la nube (Supabase) mediante `DATABASE_URL`
en `backend/.env`. Se usa el Session Pooler por compatibilidad con IPv4:

```
DATABASE_URL=postgresql+psycopg://postgres.etsonjspfydvvqdsappq:BaseDeDatosFicct@aws-0-sa-east-1.pooler.supabase.com:5432/postgres
```

El esquema y los datos demo se gestionan con los scripts de `basededatos/`
(`schema.sql`, `seed.sql`, `consultas_utiles.sql`) y ya están cargados en el
proyecto de Supabase.

Para crear o restablecer los usuarios de inicio de sesión:

```powershell
cd backend
.\.venv\Scripts\activate
python -m scripts.crear_usuarios_demo
```

### Credenciales demo

| Usuario | Contraseña | Rol |
|---|---|---|
| admin@uagrm.bo | Admin1234! | platform_admin |
| moderador@uagrm.bo | Moderador1234! | moderator |
| maria.fernandez@example.bo | Demo1234! | candidate |
| carlos.mamani@example.bo | Demo1234! | candidate |
| lucia.rojas@example.bo | Demo1234! | candidate |
| diego.suarez@example.bo | Demo1234! | candidate |
| rrhh@tecnova.bo | Demo1234! | empresa |
| talento@finandina.bo | Demo1234! | empresa |

Con el backend (`uvicorn app.main:app --reload`) y el frontend (`ng serve`)
corriendo, inicia sesión en http://localhost:4200. Los usuarios
platform_admin/moderator son redirigidos al panel de bitácora; los demás,
a su perfil.
