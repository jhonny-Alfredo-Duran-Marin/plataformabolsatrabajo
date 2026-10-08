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

## Producción (Railway)

| Qué | URL |
|---|---|
| Web | https://egresa.up.railway.app |
| API | https://backend-production-24e5.up.railway.app/api |
| App móvil | APK generado con `flutter build apk` (ver [Móvil](#móvil)) |

- Cada push a `preproduccion` que toca `backend/` o `frontend/` redespliega solo ese servicio.
- Producción usa la **misma Supabase** que el desarrollo local: lo que se cree probando en
  local también aparece en producción.
- Las variables secretas (`DATABASE_URL`, `JWT_SECRET`, claves de Stripe) están cargadas en
  Railway y no se versionan. En producción el backend no arranca sin un `JWT_SECRET` propio.

## Requisitos

| Herramienta | Versión |
|---|---|
| Python | 3.13+ |
| Node.js | 22+ |
| PostgreSQL | 16 |
| Flutter | 3.44+ con Dart 3.12 (opcional, solo móvil) |
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

La app es para **egresados**: buscar vacantes y postularse, seguir sus postulaciones,
responder las entrevistas que proponen las empresas (confirmar, rechazar con un motivo,
unirse a la videollamada o abrir la dirección en el mapa), chatear con la empresa (con
adjuntos de hasta 5 MB), ver sus notificaciones, completar el CV y ver las recomendaciones.
Sin cuenta se pueden explorar las ofertas públicas.

Las **empresas** tienen una versión acotada: postulantes nuevos (sin revisar), la agenda de
entrevistas del día y de la semana, y los mensajes con los candidatos. Publicar vacantes y
mover el proceso de selección se hace en la web, igual que todo lo de administración.

```bash
cd mobile
flutter pub get
flutter run        # desarrollo: usa el backend local
```

Para generar el APK que se instala en el celular:

```bash
flutter build apk  # queda en mobile/build/app/outputs/flutter-apk/app-release.apk
```

El APK de release se conecta al backend de producción en Railway, así que funciona
con cualquier conexión a internet (WiFi o datos), sin tener una PC prendida.

Para instalarlo, pasá el `app-release.apk` al celular (por WhatsApp o por cable), abrilo y
permití "instalar apps de origen desconocido" cuando Android lo pida. Si dice que la app no
se puede instalar, desinstalá primero la versión anterior: cada PC firma el APK con su propia
clave, y Android no deja actualizar encima de uno firmado en otra máquina.

Para probar un celular contra el backend de tu PC:

- **Por USB** (lo más simple): `adb reverse tcp:8000 tcp:8000` y compilá con
  `--dart-define=API_URL=http://127.0.0.1:8000/api`.
- **Por WiFi** (misma red): compilá con `--dart-define=CELULAR_FISICO=true`; la IP está en
  `mobile/lib/core/services/api_config.dart`.

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
python -m scripts.sembrar_multitenant     # superadmin, admins, empresas y egresados del SaaS
python -m scripts.crear_usuarios_demo     # cuentas del Sprint 0 (ver la nota de abajo)
```

`sembrar_multitenant` es idempotente y vuelve a poner en sus cuentas la contraseña de
`DEMO_PASSWORD`, que se define en `backend/.env` (no se versiona). `crear_usuarios_demo`
restablece las cuentas del Sprint 0 con las contraseñas del propio script; ojo, también
cambia la de `rrhh@tecnova.bo`.

En una base nueva, antes hay que correr las migraciones aditivas, en este orden:
`migrar_multitenant`, `migrar_cambio_password`, `migrar_planes`, `migrar_respaldos`,
`migrar_hu20_entrevistas`, `migrar_hu21_notificaciones` y `migrar_requisitos_generales`
(todas con `python -m scripts.<nombre>`). Son idempotentes: se pueden volver a correr sin
problema. La última también la aplica el backend solo al arrancar.

### Cuentas de prueba

> Son cuentas de demostración de la base compartida. Las claves reales (`DATABASE_URL`,
> Stripe) **no** van acá: se piden por el grupo del equipo.

Verificadas el 08/10/2026 contra producción (la Supabase compartida): todas inician sesión
con la contraseña de la tabla.

**Superadmin del SaaS.** Ve todas las universidades, aprueba altas, gestiona planes y
pagos, y es el único que entra a Copias de seguridad: `superadmin@egresa.bo` / `Egresa2026!`.

**Administradores de universidad.** Cada uno ve solo los datos de su universidad.

| Universidad | Plan | Correo | Contraseña |
|---|---|---|---|
| UAGRM | Institucional (al día) | `admin@uagrm.bo`, `admin2@uagrm.bo` | `Admin1234!` |
| UMSS | Profesional (al día) | `admin@umss.egresa.bo` | `Egresa2026!` |
| UMSA | Básico (gratis) | `admin@umsa.egresa.bo` | `Egresa2026!` |
| Unifranz | Profesional (pago pendiente) | `admin@unifranz.egresa.bo` | `Egresa2026!` |

Moderador de UMSS: `moderador@umss.egresa.bo` / `Egresa2026!`.

**Empresas.** Son globales: cada universidad decide si las habilita para reclutar.

| Empresa | Correo | Contraseña |
|---|---|---|
| TECNOVA | `rrhh@tecnova.bo` | `empresa1234` |
| Andes Digital | `rrhh@andesdigital.bo` | `Egresa2026!` |
| ValleFin | `seleccion@vallefin.bo` | `Egresa2026!` |
| Oriente Logística | `empleos@orientelogistica.bo` | `Egresa2026!` |
| Chiquitano Agro | `rrhh@chiquitanoagro.bo` | `Egresa2026!` |
| Altiplano Analytics | `talento@altiplanoanalytics.bo` | `Egresa2026!` |
| Empresa Prueba SRL | `empresa@prueba.com` | `Prueba123!` |
| Pampa Software (escenario de demostración) | `rrhh@pampasoftware.egresa.bo` | `Egresa2026!` |
| Cooperativa Horizonte (escenario de demostración) | `talento@coophorizonte.egresa.bo` | `Egresa2026!` |
| Mercado Express (escenario de demostración) | `empleos@mercadoexpress.egresa.bo` | `Egresa2026!` |

**Egresados.**

| Universidad | Correo | Contraseña |
|---|---|---|
| UAGRM | `antonio@prueba.com` (perfil completo, ideal para la HU-23) | `Prueba123!` |
| UAGRM | `egresado.prueba@uagrm.bo` | `Egresado1234!` |
| UAGRM | `sofia.vargas@uagrm.egresa.bo`, `marco.rivero@uagrm.egresa.bo` | `Egresa2026!` |
| UMSS | `valeria.quiroga@umss.egresa.bo`, `jorge.montano@umss.egresa.bo`, `paola.arce@umss.egresa.bo` | `Egresa2026!` |
| UMSA | `andrea.gutierrez@umsa.egresa.bo`, `luis.mamani@umsa.egresa.bo`, `rodrigo.condori@umsa.egresa.bo` | `Egresa2026!` |
| Unifranz | `camila.salvatierra@unifranz.egresa.bo`, `diego.antelo@unifranz.egresa.bo` | `Egresa2026!` |

**Egresados del escenario de demostración.** Todos con `Egresa2026!`. Los validados tienen
postulaciones en distintas etapas; los sin validar esperan en la cola de validación de su
universidad (pueden entrar, pero no postularse hasta que el admin los valide).

| Universidad | Validados | Sin validar |
|---|---|---|
| UAGRM | `maria.rojas` (Sistemas), `jose.fernandez` (Contaduría), `daniela.gutierrez` (Desarrollo de software), `carlos.mamani` (Economía), `gabriela.quispe` (Industrial), `miguel.choque` (Redes), `carla.flores` (Administración), `juan.vargas` (Sistemas) | `lucia.justiniano`, `diego.suarez` |
| UMSS | `natalia.rocha` (Industrial), `sergio.camacho` (Redes), `valentina.villarroel` (Administración), `fernando.arce` (Sistemas), `mariana.ribera` (Contaduría), `ricardo.antelo` (Desarrollo de software), `alejandra.saucedo` (Economía), `gonzalo.terrazas` (Industrial) | `ximena.cuellar`, `alvaro.montenegro` |
| UMSA | `rocio.aguilera` (Contaduría), `mauricio.zeballos` (Desarrollo de software), `claudia.salazar` (Economía), `javier.mendez` (Industrial), `jimena.pinto` (Redes), `oscar.vaca` (Administración), `veronica.anez` (Sistemas), `marcelo.moreno` (Contaduría) | `paola.cespedes`, `cristian.chavez` |
| Unifranz | `silvia.limachi` (Redes), `adrian.condori` (Administración), `melany.apaza` (Sistemas), `bruno.ticona` (Contaduría), `fabiola.peredo` (Desarrollo de software), `ivan.soliz` (Economía), `estefania.guzman` (Industrial), `wilson.medina` (Redes) | `andrea.zambrana`, `rodrigo.paz` |

El correo completo es el usuario más el dominio de su universidad: `@uagrm.egresa.bo`,
`@umss.egresa.bo`, `@umsa.egresa.bo` o `@unifranz.egresa.bo` (por ejemplo
`maria.rojas@uagrm.egresa.bo`).

**Para probar las funciones nuevas:**

- **Recomendaciones (HU-23):** entrá como egresado y abrí "Vacantes Recomendadas" en el
  dashboard (`/recomendaciones`). Con `IA_RECOMENDACIONES_ACTIVAS=false` en el `.env` se
  prueba el CP04 (servicio no disponible).
- **Pago con tarjeta (Stripe, modo prueba):** entrá como admin de Unifranz → Universidades →
  "Pagar con tarjeta". Tarjeta de prueba de Stripe `4242 4242 4242 4242`, cualquier fecha
  futura y cualquier CVC. Las claves (`STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`) van en
  `backend/.env` e `infra/docker/.env`.
- **Altas de universidades:** hay solicitudes pendientes (UPDS y UCB) para aprobar desde
  Universidades con el superadmin. La página pública es `/auth/registro-universidad`.
- **Copias de seguridad:** con el superadmin, menú "Copias de seguridad". Ojo: restaurar
  reemplaza los datos de la Supabase compartida para todo el equipo; para probar usá
  "Verificar sin cambiar nada".
- Las cuentas que se crean desde Gestión de roles (o al aprobar una universidad) tienen una
  contraseña temporal y deben cambiarla en el primer ingreso.
- **Ofertas sin cuenta (HU-34):** en el login, "Explorar vacantes de empleo" (web) o
  "Explorar ofertas sin cuenta" (app). Muestra las vacantes publicadas con el total de
  vacantes activas y de empresas verificadas; para postularse pide iniciar sesión.
- **Entrevistas (HU-20):** con `empresa@prueba.com`, en el dashboard "Gestionar Candidatos y
  Etapas" → "Agendar entrevista" en la tarjeta del candidato. El egresado la confirma o la
  rechaza desde Mis postulaciones (web) o desde la app, donde Inicio avisa la propuesta.
- **Comparar candidatos (HU-18):** en "Gestionar Candidatos y Etapas", marcá 2 o 3 candidatos
  de la misma vacante con el checkbox de su tarjeta y tocá "Comparar candidatos" en la barra
  de abajo. Ojo: "Descartar candidato" desde la comparación descarta de verdad.
- **Mensajes (HU-19):** la empresa escribe desde "Mensajes" en la tarjeta del candidato
  (web) y el egresado responde desde Mis postulaciones (web) o desde la app, en el detalle
  de la postulación o con el botón de mensajes del Inicio. Se pueden adjuntar archivos.
- **App de empresas:** entrá a la app con `empresa@prueba.com` / `Prueba123!`: pestañas
  Postulantes, Entrevistas y Mensajes.
- **Notificaciones (HU-21):** campana en la web y en el Inicio de la app; en "Preferencias de
  alertas" se apaga cada tipo de aviso (mensajes, entrevistas, etapas, vacantes afines).
  **Avisos push:** la app los pide al entrar (Android pregunta el permiso) y la web desde
  Notificaciones → Preferencias → "Activar en este navegador"; ahí mismo "Enviar un aviso de
  prueba" manda uno real a todos los dispositivos de la cuenta. El backend necesita la
  variable `FIREBASE_SERVICE_ACCOUNT_JSON` (la llave privada de Firebase, nunca en el repo);
  sin ella todo lo demás funciona igual. La configuración web (`environment*.ts`) y la de
  Android (`mobile/lib/core/firebase_options.dart`) son identificadores públicos, no secretos.
- **Sugerencias IA (HU-24):** con una empresa, botón "Sugerencias IA" en el dashboard o en
  "Gestionar Candidatos y Etapas": ranking de los postulantes de cada vacante por afinidad.
- **Denuncia de ofertas (HU-22):** con un egresado, en el detalle de una vacante "Denunciar
  oferta" (web) o el menú ⋮ del detalle (app). Con 3 denuncias que cuentan qué pasó (al menos
  20 caracteres), la oferta se oculta sola. El admin de la universidad las revisa en
  "Denuncias de ofertas" y decide mantenerla, suspenderla o eliminarla; la empresa y quienes
  denunciaron reciben el aviso. No necesita migración: usa la tabla `moderation_report`.

**Requisitos generales de la materia:**

- **Grupos de usuarios y permisos por componente (requisito 2):** "Grupos y permisos" en el
  menú del admin de la universidad (y del superadmin, eligiendo la universidad). Un grupo
  junta administradores y moderadores y dice qué menús, formularios, botones y etiquetas del
  panel ven (el catálogo está en `backend/app/security/permisos.py`). Sin grupo, cada uno ve
  lo de su rol; con grupos, la suma de sus grupos, sin pasar el techo del rol (los
  componentes "solo admin" no llegan a un moderador). El backend controla cada permiso en su
  endpoint, así que ocultar un botón no es la única barrera, y los cambios valen al instante.
  "Lo que ve cada persona" muestra el resultado de cada cuenta. Para probarlo: con
  `admin@umss.egresa.bo` creá un grupo con unos pocos permisos, sumá a
  `moderador@umss.egresa.bo` y entrá con esa cuenta.
  Las tablas (`user_group`, `user_group_member`, `user_group_permission`) las crea el backend
  solo al arrancar.
- **Bitácora confidencial (requisito 3):** registra usuario, IP, fecha y hora, módulo y
  acción, y cada entrada se guarda cifrada (X25519 + AES-256-GCM): en la base solo se ve
  `cifrado`. Para leerla, "Bitácora del sistema" pide la **clave de desarrollador**; la
  clave no se guarda en ningún lado del sistema. El servidor solo tiene la clave pública,
  en la variable `BITACORA_CLAVE_PUBLICA`. Para generar un par nuevo:
  `python -m scripts.clave_bitacora` (muestra la clave de desarrollador una sola vez; si se
  pierde, las entradas cifradas con ella no se recuperan). Las entradas viejas sin cifrar se
  cifran con `python -m scripts.cifrar_bitacora --confirmar` (antes, una copia de
  seguridad). Sin la variable, la bitácora funciona como antes, sin cifrar.
- **Reportes personalizados (requisito 5):** "Reportes personalizados" en el menú del admin
  y "Reportes" en el panel de la empresa. Se elige la fuente (egresados, empresas, vacantes
  o postulaciones), los filtros, las columnas y su orden y el orden de las filas; se ve la
  vista previa y se exporta a Excel, PDF o HTML o se manda por correo. El admin ve solo su
  universidad y la empresa solo lo suyo. El plan Básico no incluye reportes (probalo con
  un admin de la UMSA). El correo usa SMTP (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
  `SMTP_PASSWORD`, `SMTP_FROM`) o la API de Brevo (`BREVO_API_KEY`, con `SMTP_FROM`
  verificado en Brevo); Railway bloquea SMTP en sus planes básicos.
- **Ayuda en línea (requisito 4):** botón **?** (o la tecla F1) en todas las pantallas de
  la web, que abre la ayuda de esa pantalla, y el centro de ayuda en `/ayuda`. En la app, el
  ícono de ayuda de la barra superior de cada pantalla.
- **Tareas automáticas y backup automático (requisitos 1 y 6):** todos los días desde las
  03:00 (hora de Bolivia) el backend hace una copia de seguridad completa (conserva las
  últimas 7), cierra las vacantes vencidas avisando a la empresa, manda a cada egresado el
  boletín con las ofertas nuevas que coinciden con su perfil y envía los recordatorios de lo
  que vence en las próximas 24 horas: vacantes por cerrar (a la empresa y a los egresados
  afines que no se postularon) y entrevistas (al egresado y a la empresa). El superadmin ve el historial y
  las puede ejecutar a mano en "Tareas automáticas". Corren solas en Railway y no en las
  computadoras del equipo (`TAREAS_AUTOMATICAS_ACTIVAS=true` para forzarlas;
  `TAREAS_HORA_DIARIA` cambia la hora). Las copias se guardan en `STORAGE_LOCAL_PATH`: en
  Railway conviene montar un volumen en `/app/storage` para que no se pierdan al redesplegar.
- **Escenario de demostración con datos realistas:** `python -m scripts.sembrar_escenario_demo`
  (después de `sembrar_multitenant`, que corre solo al principio). Agrega 3 empresas, 25
  vacantes, 40 egresados de las cuatro universidades (8 sin validar), unas 100 postulaciones
  en todas las etapas, entrevistas y conversaciones, y deja eventos por vencer: vacantes
  publicadas hoy, que cierran en unas horas y ya vencidas, entrevistas de hoy y mañana. Para
  que salten los avisos (campana y push), el superadmin ejecuta en "Tareas automáticas" el
  cierre de vacantes, el boletín y los recordatorios; si no, el servidor los corre solo a
  las 03:00. Se puede volver a correr: no duplica datos ni avisos y refresca las fechas. Las
  cuentas nuevas usan `DEMO_PASSWORD` (están en las tablas de "Cuentas de prueba"). Si
  existen, `empresa@prueba.com` y `antonio@prueba.com` quedan con una entrevista para
  mañana: es el mejor par para mostrar los recordatorios.

Si alguna deja de funcionar (alguien del equipo pudo haberla cambiado probando), se resetea corriendo los scripts de arriba o pidiendo que se actualice manualmente — avisen en el grupo antes de cambiarlas para no romper la sesión de otro compañero.

Con el backend (`uvicorn app.main:app --reload`) y el frontend (`ng serve`)
corriendo, inicia sesión en http://localhost:4200 (o http://localhost si
usás Docker Compose). Los usuarios platform_admin/moderator son
redirigidos al panel `/admin`; empresa y egresado, a su dashboard.
