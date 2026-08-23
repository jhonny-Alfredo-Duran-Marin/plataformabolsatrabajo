# Roadmap — EGRESA

Basado en el perfil de proyecto (alcance, sección 5) y la planificación de sprints (sección 3.11).

## Módulos del sistema

Backend organizado por módulo de negocio en `backend/app/features/<modulo>/`
(no por capa). Cada carpeta agrupa `router.py` (endpoints), `service.py`
(reglas de negocio), `repository.py` (acceso a datos) y `schema.py`
(contratos de entrada/salida de la API) — solo los archivos que ese módulo
necesita. Ver [backend/ARCHITECTURE.md](backend/ARCHITECTURE.md) para el
detalle de cómo se conectan las capas y qué queda centralizado
(`models/`, `security/`, `core/`, `common/`, `shared/`).

| # | Módulo | Carpeta backend | Carpeta frontend | Sprint previsto |
|---|---|---|---|---|
| 5.1.1 | Usuarios, roles y seguridad | `features/auth/`, `security/` | `features/auth` | 0 |
| 5.1.1 (RNF-18) | Bitácora del sistema | `features/bitacora/` | `features/admin/bitacora` | 0 |
| 5.1.2 | Validación institucional | `features/validacion/` | `features/admin/validacion-egresados` | 0 |
| 5.1.3 | Perfil profesional y currículum | `features/perfil/` | `features/perfil` | 0 |
| — | Datos de referencia (carreras, skills, sectores...) | `features/catalogo/` | — | 0 |
| — | Empresas (registro, autorización) | `features/empresa/` | `features/auth`, `features/admin` | 0 |
| 5.1.4 | Gestión de vacantes | `features/vacantes/` | `features/vacantes` | 1 |
| 5.1.5 | Postulación y seguimiento | `features/postulaciones/` | `features/postulaciones` | 1 |
| 5.1.6 | Proceso de selección | `features/seleccion/` | `features/seleccion` | 2 |
| 5.1.7 | Comunicación y entrevistas | `features/comunicacion/` | `features/comunicacion` | 2 |
| 5.1.8 | Notificaciones y alertas | `features/notificaciones/` | `features/notificaciones` | 2 |
| 5.1.9 | Moderación y antifraude | `features/moderacion/` | `features/moderacion` | 3 |
| 5.1.10 | Reportes institucionales | `features/reportes/` | `features/reportes` | 3 |
| 5.1.11–5.1.14 | Inteligencia artificial (recomendación, generativo, chatbot, predictivo) | `features/ia/` | `features/ia` | 3–4 |
| 5.1.15 | Aplicación móvil | — | `mobile/lib/features/*` | 4 |

## Calendario de sprints

| Sprint | Fechas | Foco |
|---|---|---|
| Sprint 0 | 25 y 27 de agosto de 2026 | Base estructural: usuarios/roles/seguridad, validación institucional, perfil profesional |
| Sprint 1 | 8 y 10 de septiembre de 2026 | Gestión de vacantes, postulación y seguimiento |
| Sprint 2 | 6 y 8 de octubre de 2026 | Proceso de selección, comunicación, notificaciones |
| Sprint 3 | 3 y 5 de noviembre de 2026 | Moderación, reportes institucionales, IA (recomendación/generativo/chatbot) |
| Sprint 4 | 24 y 26 de noviembre de 2026 | Análisis predictivo, aplicación móvil, cierre e integración |

## Flujo de ramas

- `preproduccion`: rama principal (base de esta estructura).
- `feature/<nombre>`: una rama por integrante o historia de usuario, integrada mediante pull request.
