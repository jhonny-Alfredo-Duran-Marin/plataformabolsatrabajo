# Roadmap — EGRESA

Basado en el perfil de proyecto (alcance, sección 5) y la planificación de sprints (sección 3.11).

## Módulos del sistema

| # | Módulo | Carpeta backend | Carpeta frontend | Sprint previsto |
|---|---|---|---|---|
| 5.1.1 | Usuarios, roles y seguridad | `security/`, `routers/auth.py` | `features/auth` | 0 |
| 5.1.2 | Validación institucional | `routers/validacion.py` | `features/admin` | 0 |
| 5.1.3 | Perfil profesional y currículum | `routers/perfiles.py` | `features/perfil` | 0 |
| 5.1.4 | Gestión de vacantes | `routers/vacantes.py` | `features/vacantes` | 1 |
| 5.1.5 | Postulación y seguimiento | `routers/postulaciones.py` | `features/postulaciones` | 1 |
| 5.1.6 | Proceso de selección | `routers/seleccion.py` | `features/seleccion` | 2 |
| 5.1.7 | Comunicación y entrevistas | `routers/comunicacion.py` | `features/comunicacion` | 2 |
| 5.1.8 | Notificaciones y alertas | `routers/notificaciones.py` | `features/notificaciones` | 2 |
| 5.1.9 | Moderación y antifraude | `routers/moderacion.py` | `features/moderacion` | 3 |
| 5.1.10 | Reportes institucionales | `routers/reportes.py` | `features/reportes` | 3 |
| 5.1.11–5.1.14 | Inteligencia artificial (recomendación, generativo, chatbot, predictivo) | `services/ia/`, `routers/ia.py` | `features/ia` | 3–4 |
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
