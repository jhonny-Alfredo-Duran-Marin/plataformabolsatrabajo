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

Levanta backend, frontend y base de datos con un solo comando, sin tener que correr `uvicorn`/`ng serve` cada vez.

```bash
cd infra/docker
cp .env.example .env
```

Editá `infra/docker/.env` y agregá una línea con el mismo `DATABASE_URL` que tenés en `backend/.env`, para que el backend en Docker use la Supabase compartida (con los datos de prueba ya cargados) en vez de un Postgres local vacío:

```
DATABASE_URL=postgresql+psycopg://...   # copiá el valor real de backend/.env
```

```bash
docker compose up -d --build
```

Abrí 👉 http://localhost — el backend queda en http://localhost:8000.

| Comando | Qué hace |
|---|---|
| `docker compose up -d --build` | Construye y levanta todo (primera vez o tras cambiar código) |
| `docker compose up -d` | Levanta sin reconstruir (siguientes veces) |
| `docker compose down` | Para y elimina los contenedores |
| `docker compose logs -f` | Ver logs en vivo |
| `docker compose ps` | Ver estado de los contenedores |

Más detalle en [infra/README.md](infra/README.md).

## Flujo de trabajo en Git

Rama principal: **`preproduccion`**. Nadie trabaja directo sobre ella — cada integrante tiene su propia rama.

### 1. Clonar el proyecto y crear tu rama (una sola vez)

```bash
git clone https://github.com/jhonny-Alfredo-Duran-Marin/plataformabolsatrabajo.git
cd plataformabolsatrabajo
git checkout preproduccion
git pull origin preproduccion
git checkout -b <tu-nombre>          # ej: git checkout -b Manuel
git push -u origin <tu-nombre>
```

### 2. Antes de programar, cada día: traer lo nuevo de preproduccion

```bash
git checkout <tu-nombre>
git fetch origin
git merge origin/preproduccion
```

Si el merge trajo cambios en `requirements.txt`, `package.json` o `pubspec.yaml`, reinstalá dependencias:

```bash
cd backend && pip install -r requirements-dev.txt
cd ../frontend && npm install
cd ../mobile && flutter pub get
```

### 3. Mientras trabajás: commits chicos y frecuentes

```bash
git add archivo1 archivo2
git commit -m "feat(vacantes): agrega filtro por ciudad"
git push origin <tu-nombre>
```

### 4. Terminaste tu HU: devolverla a preproduccion

```bash
# traé preproduccion una vez más por si alguien subió algo mientras trabajabas
git checkout <tu-nombre>
git fetch origin
git merge origin/preproduccion

# mergeá tu rama a la principal
git checkout preproduccion
git pull origin preproduccion
git merge <tu-nombre>
git push origin preproduccion
```

**Si aparece un conflicto:** Git marca con `<<<<<<<` los archivos donde dos personas tocaron las mismas líneas. Abrí el archivo, decidí qué versión queda (o combinalas a mano), borrá esas marcas, y cerrá con `git add <archivo>` seguido de `git commit`. Es normal trabajando en equipo, no un error.

**Dos cosas que Git nunca toca:**
- `backend/.env` está en `.gitignore` a propósito (tiene la contraseña de la Supabase compartida, JWT secret, credenciales de correo). Se comparte aparte, por un canal privado — nunca por GitHub.
- Mergear, pushear o pullear código no ejecuta nada contra la base de datos. La Supabase solo se ve afectada cuando alguien efectivamente levanta el backend y lo usa (o corre una migración a propósito).

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
en `backend/.env` (no versionado — pide la cadena de conexión real a quien
administre el proyecto de Supabase). Se usa el Session Pooler por
compatibilidad con IPv4.

El esquema y los datos demo se gestionan con los scripts de `basededatos/`
(`schema.sql`, `seed.sql`, `consultas_utiles.sql`) y ya están cargados en el
proyecto de Supabase.

Para crear o restablecer los usuarios de inicio de sesión:

```powershell
cd backend
.\.venv\Scripts\activate
python -m scripts.crear_usuarios_demo
```

Las credenciales demo que crea ese script se comparten por un canal privado
del equipo (no en este README) — pide la lista a quien lo ejecutó.

Con el backend (`uvicorn app.main:app --reload`) y el frontend (`ng serve`)
corriendo, inicia sesión en http://localhost:4200. Los usuarios
platform_admin/moderator son redirigidos al panel de bitácora; los demás,
a su perfil.
