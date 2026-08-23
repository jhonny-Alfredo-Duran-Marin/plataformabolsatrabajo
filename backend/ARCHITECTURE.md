# Arquitectura del backend

El backend está organizado **por módulo de negocio**, no por capa técnica.
Cada carpeta en `app/features/<modulo>/` agrupa todo lo que ese módulo
necesita para funcionar de punta a punta.

## Flujo de una petición

```
HTTP request
    -> router.py          valida entrada (schema.py), define el endpoint
        -> service.py      reglas de negocio, orquesta repositorios
            -> repository.py   consultas SQLAlchemy contra la BD
                -> model (en app/models/)   tabla real
```

`schema.py` no es la tabla de la base de datos: es el contrato de
entrada/salida de la API (Pydantic). El modelo ORM (SQLAlchemy) vive en
`app/models/`, separado, para no acoplar la forma de la API con la forma
de la tabla.

Un módulo solo trae los archivos que realmente usa — por ejemplo
`features/validacion/` solo tiene `router.py` porque no necesita su
propio service/repository/schema, reutiliza los de `features/perfil/` y
`features/empresa/`.

## Qué vive en `features/<modulo>/`

| Módulo | Contenido | Corresponde a |
|---|---|---|
| `auth/` | router, service, repository (usuarios/identidad), schema | HU-01, HU-02, HU-03 |
| `bitacora/` | router, service, repository, schema | HU-37 |
| `validacion/` | router (usa los service de `perfil/` y `empresa/`) | HU-04, HU-06 |
| `perfil/` | router, service, repository, schema (perfil de egresado) | HU-04, perfil profesional |
| `empresa/` | service, repository, schema (sin router propio todavía) | HU-05 |
| `catalogo/` | router, schema (carreras, skills, sectores...) | datos de referencia |
| `vacantes/`, `postulaciones/`, `seleccion/`, `comunicacion/`, `notificaciones/`, `moderacion/`, `reportes/`, `ia/` | por ahora solo `router.py` stub (o `services/` en `ia/`) | Sprints 1 a 4, ver [ROADMAP.md](../ROADMAP.md) |

Es normal que un módulo importe de otro (por ejemplo `validacion/router.py`
importa `EgresadoService` desde `features/perfil/service.py`, porque la
validación de egresados es parte del dominio "perfil"). Lo que no debería
pasar es que un módulo importe el `router.py` de otro — los routers solo
se registran una vez, en `app/main.py`.

## Qué queda centralizado (no es de un solo módulo)

- `app/models/` — todos los modelos SQLAlchemy. Se mantiene centralizado
  (y no dentro de cada `features/`) porque Alembic necesita importarlos
  todos juntos (`app/models/__init__.py`) para generar migraciones, y
  porque varios modelos tienen relaciones/FKs entre sí que cruzan módulos.
- `app/security/` — JWT, hashing de contraseñas, rate limiting de login,
  roles. Lo usa cualquier módulo que necesite autenticar/autorizar.
- `app/core/` — configuración (`config.py`), conexión a base de datos
  (`database.py`), logging.
- `app/common/` — utilidades transversales: manejo de excepciones,
  paginación, contexto de request (IP del cliente), y el router de
  `/health`.
- `app/shared/` — servicios de infraestructura usados por varios módulos
  pero que no son dueños de ningún dominio de negocio (por ahora,
  `email_service.py`).
- `app/scheduler/` — reservado para tareas programadas (cron), todavía
  sin contenido.

## Cómo se registra todo

`app/main.py` importa el `router` de cada `features/<modulo>/router.py`
y los registra con `app.include_router(...)`. Si agregas un módulo nuevo
con endpoints, hay que sumarlo ahí también.

## Al agregar una historia de usuario nueva

1. Busca si tu HU cae dentro de un módulo que ya existe en `features/`
   (revisa la tabla de [ROADMAP.md](../ROADMAP.md)).
2. Si el módulo ya tiene `router.py`, agrega tu endpoint ahí. Si no
   existe, créalo siguiendo el mismo patrón que un módulo similar
   (por ejemplo `features/bitacora/` es un buen ejemplo simple y
   completo: router + service + repository + schema).
3. No dupliques repository/service si el dato ya pertenece a otro
   módulo (ej. `Usuario` vive en `features/auth/repository.py`) —
   impórtalo desde ahí en vez de crear una copia.
